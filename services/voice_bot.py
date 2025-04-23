
from .openai_client import OpenAiClient
from .voice import fast_speech_recog, speech_recog, text2speech
from .llm_prompts import *
from .user_state import UserData
from .ai_agent import SearchAgent
from .commands import *

from utils import convert_base64_audio_to_wav, lang2voice, load_preprocess_json, locale2lang, get_company_imprint, merge_dicts_recursive
from uuid import uuid4
import asyncio


name_path = ("GeneralInformation", "FirstName")
industry_path = "IndustryList"
default_fields = {"GeneralInformation": {"Gender": "", "FirstName": "", "LastName": ""},"BusinessInformation": {"Company": "", "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInformationAddress": "", "PositionLevel": "", "Department": "", "JobTitle": "", "Industry": "", "EducationLevel": "", "PhoneNumber": "", "MobilePhoneNumber": "", "BusinessEmail": ""}, "PersonalInformation": { "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInfoAddress": "", "PhoneNumber": "", "MobilePhoneNumber": "", "PersonalEMail": "" }}
required_fields = ["FirstName", "LastName", "Company", "BusinessEmail"]
industry_formated = ""

class VoiceBot:
    def __init__(self, openai_config: dict):
        self.openai_client = OpenAiClient(openai_config)
        self.users_states = {} # report_id to state
        self.ai_agent = SearchAgent()


    async def process_user_message(self, lang: str = "de-DE", form_data: str = "", session_id: str = None, callreportID: str = None, payload: str = "", form_type: str = ""):
        user_data = self.users_states.get(session_id)
        
        if not user_data:
            print("Creating new user data")
            user_data = UserData(session_id, "default", "", "", lang)
        user_data.language = lang
        last_message = user_data.last_message
        last_answer = user_data.last_answer
        user_text = payload
        form_data = load_preprocess_json(form_data)
        print("USER TEXT: ", user_text)
        msg_type = await self.classify_user_message(user_text, user_data.chat_history) 
        print("Put state as: ", msg_type)
        user_data.state = msg_type
        commands = []
        print(f"Classification: {msg_type} | with user text - {user_text}") 
        async with asyncio.TaskGroup() as tg:
            suggestion_task = tg.create_task( 
                self.generate_accompany_message(user_text, msg_type, user_data)
            )

            main_task  = tg.create_task(
                self.generate_answer(user_text, msg_type, form_data, user_data, callreportID, form_type)
            )
        commands, user_state = main_task.result()
        accompany_text = suggestion_task.result()
        if not self.check_for_voice_command(commands):
            print("Don't have voice command so add accompany text")
            if commands:
               order = commands[-1]["order"]+1 
            else:
                order = 1
            accompany_audio = gen_voice_play_command(accompany_text, order, user_data.language)
            commands.append(accompany_audio)
        user_state.last_message = user_text 
        self.users_states[session_id] = user_state
        response = self.form_response(commands, session_id)
        return response
    

    async def generate_accompany_message(self, user_msg: str, category: str, user_data: UserData):
        category = category.replace("report", "contact")
        messages = [
                {"role": "user", "content": get_suggestion_prompt(user_msg, category, user_data.chat_history, user_data.language)}
            ]
        text = await self.openai_client.generate_response(messages)
        return text
    

    def check_for_voice_command(self, commands: list):
        for command in commands:
            if command["name"] == 'playBotVoice' or command["name"] == "giveListContactFilds" or command["name"] == "giveListInterests":
                return True
        return False


    async def form_error_resonse(self, session_id, locale: str = "de-DE"):
        messages = [
                {"role": "user", "content": get_error_prompt(locale)}
            ]
        text = await self.openai_client.generate_response(messages)
        commands = [gen_voice_play_command(text, 1, locale)]
        return self.form_response(commands, session_id)


    def form_response(self, commands: list, session_id: str = None) -> dict:
        return {
            "commands": commands,
            "sessionID": session_id
        }
    

    async def generate_answer(self, text: str, msg_type: str, form_data: dict,
                             user_state = None, call_report_id:str = False, form_type = ""):
        global industry_formated, required_fields
        commands = []
        order = 0
        print(msg_type)  
        contact_forms = form_data["ContactList"]
        main_contact = contact_forms[0]
        industry_values = form_data["IndustryList"]
        industry_formated = get_variant_of_fields(industry_values)
        for contact in contact_forms:
            if contact["GeneralInformation"]["Main"] == 1:
                print("Found main contact")
                main_contact = contact
        interest_form = form_data["InterestsList"]
        if "Create contact" in msg_type or "Create report" in msg_type:
            res, user_state = await self._create_contact(text, main_contact, user_state, order)
            commands.extend(res["commands"])
            order = res["order"]
        if "None" in msg_type:
            answer = await self.generate_general_answer(text, user_state.language)
            user_state.last_answer = answer
            order += 1
            commands.append(gen_voice_play_command(answer, order, user_state.language))
        elif self._is_call_report_nan(call_report_id) and not commands:
            print("Can't do this not inside call report with classification: ", msg_type)
            answer = await self.generate_not_in_callreport_answer(text, lang = user_state.language)
            user_state.last_answer = answer
            order += 1
            commands.append(gen_voice_play_command(answer, order, user_state.language))
        if "Fill interests" in msg_type:
            res = await self.fill_in_interests(text, interest_form, user_state, order)
            order = res.get("order", 0)
            commands.extend(res["commands"])
        if "Update info" in msg_type:
            required_fields = main_contact["RequiredFields"]
            user_state, extend_commands = await self.update_contact_info(text, main_contact, user_state, call_report_id, order)
            commands.extend(extend_commands)
        if "Add follow-ups" in msg_type:
            follow_apps = await self.extract_follow_ups(text)
            order += 1
            commands.append(gen_general_command("addFollowUps", follow_apps, "list", order))
        if "Cancel" in msg_type:
            order += 1
            commands.append(gen_general_command("Cancel", order = order))
        if "Save" in msg_type:
            order += 1
            extend_commands = []
            if form_type == "contact": 
                required_fields = main_contact["RequiredFields"]
                user_state, extend_commands = await self.check_info_ask_for_extra_info(text, user_state, "", main_contact, required_fields, order)
                print("Extended commands: ", extend_commands)
                if extend_commands and not self.check_for_voice_command(commands): 
                    commands.extend(extend_commands)
                elif not extend_commands: 
                    commands.append(gen_general_command("saveCurrentDocument", order = order))
        
        return commands, user_state
    

    async def update_contact_info(self, text, contact_forms, user_data: UserData, call_report_id: str, order = 0):
        contact_fields = await self.extract_info_from_text(text, contact_forms)  
        old = user_data.contacts.get(call_report_id, {}).get(call_report_id, contact_forms)
        contact_fields = await self.enrich_contact_from_internet(text, contact_fields, user_data, order, old_contact_info = old)
        user_data.contacts[call_report_id] = contact_fields
        user_data, extend_commands = await self.check_info_ask_for_extra_info(text, user_data, "updateCurrentContact", contact_fields, required_fields, order)
        return user_data, extend_commands
    

    async def fill_internet_personal_info(self, user_msg: str, user_form: dict, user_data: UserData, order = 0) -> list:
        print("FIll internet information")
        first_name, second_name = user_form["GeneralInformation"]["FirstName"], user_form["GeneralInformation"]["LastName"]
        person = first_name + " " + second_name

        company = user_form["BusinessInformation"]["Company"] 
        country = user_form["PersonalInformation"]["Country"] 
        neccessary_info = (first_name, second_name, company)
        if not all(neccessary_info):
            return  None
        personal_info = await self.ai_agent.get_person_info(person, company, country)
        print("Personal info: ", personal_info)
        if personal_info == "None":
            # answer = await self.gen_no_info_found(user_msg)
            # user_data.last_answer = answer
            # order += 1
            # commands.append(gen_voice_play_command(answer, order, user_data.language))
            # return  commands, user_data
            return None
        fields = await self._fill_forms_with_extra_info(personal_info, user_form)
        # user_data.history_data["contact_fields"] = fields
        print("new: ", fields)
        # order += 1
        # commands.append(gen_general_command("updateCurrentContact", value = fields, val_type = "json", order = order))
        return fields
    
    
    async def fill_internet_company_info(self, user_msg: str, user_form: dict, user_data: UserData, order: int = 0):
        commands = []
        print("FIll internet info about company") 
        company = user_form["BusinessInformation"]["Company"]  
        if not company:
            return 
            # answer = await self.generate_missing_field_message(user_msg, [company], False, True, user_data = user_data)
            # order += 1
            # user_data.last_answer = answer
            # commands.append(gen_voice_play_command(answer, order, user_data.language))
            # return  commands, user_data
        personal_info = await self.ai_agent.get_company_info(company)
        print("Personal info: ", personal_info)
        if personal_info == "None":
            answer = await self.gen_no_info_found(user_msg)
            user_data.last_answer = answer
            order += 1
            commands.append(gen_voice_play_command(answer, order, user_data.language))
            return  commands, user_data
        website = await self._get_website(personal_info)
        imprint_info = get_company_imprint(website)
        print("Imprint info: ", imprint_info)
        full_info = personal_info + f"\nWebsite: {website}"+ "\nImprint info: " + imprint_info
        fields = await self._fill_forms_with_extra_info(full_info, user_form)
        # user_data.history_data["contact_fields"] = fields
        print("new: ", fields)
        order += 1
        # commands.append(gen_general_command("updateCurrentContact", value = fields, val_type = "json", order = order))
        return fields
    
    
    async def enrich_contact_from_internet(self, text, contact_fields: dict, user_data: UserData, order: int = 0, old_contact_info: dict = None) -> dict:
        async with asyncio.TaskGroup() as tg:
            if old_contact_info: # check if we had changes in info and we need to redo the search
                comp_change, person_change = self._check_company_change(contact_fields, old_contact_info), self._check_name_changes(contact_fields, old_contact_info)
            else:
                comp_change, person_change = True, True
            if comp_change:
                company_search_task = tg.create_task( 
                    self.fill_internet_company_info(text, contact_fields, user_data, order)
                )
            if person_change:
                pers_search_task  = tg.create_task(
                    self.fill_internet_personal_info(text, contact_fields, user_data, order)
                )
        company_info, personal_info = None, None
        if comp_change:
            company_info = company_search_task.result()
        if person_change:
            personal_info = pers_search_task.result()
        if company_info and personal_info:
            print("Merging both search: company and personal")
            complete_info = merge_dicts_recursive(company_info, personal_info)
        elif company_info:
            print("Only company info")
            complete_info = company_info
        elif personal_info:
            print("Only personal info")
            complete_info = personal_info
        else:
            print("Neither company info nor personal info")
            complete_info = contact_fields
        return complete_info
    

    async def _create_contact(self, text: str, form_data: dict, user_data: UserData, order = 0):
        global required_fields, default_fields
        extend_commands = []
        is_give_list = 0
        msg = ""
        print(form_data)
        print("PAYLOAD: ", form_data)
        if isinstance(form_data, dict):
            default_fields = form_data
        required_fields = form_data["RequiredFields"]
        cmd_name = "createContact"
        contact_fields = await self.extract_info_from_text(text, form_data)
        complete_info = await self.enrich_contact_from_internet(text, contact_fields, user_data, order)
        print(user_data.contacts, type(user_data.contacts))
        user_data.contacts[uuid4()] = complete_info
        user_data, extend_commands = await self.check_info_ask_for_extra_info(text, user_data, cmd_name, contact_fields, required_fields, order)
        return {"commands": extend_commands, "contact_fields": contact_fields, "order": order, "is_give_list": is_give_list, "answer": msg}, user_data


    async def fill_in_interests(self, text: str, payload, user_data: UserData, order = 0):
        extend_commands = []
        interests = None
        command_name = "fillInterests"
        interests = await self.extract_list_interests(text, payload)
        order += 1
        extend_commands.append(gen_general_command(command_name, interests, "list", order))
        try:
            # fix this
            contact_fields = user_data.contacts
            print(name_path)
            name = contact_fields[name_path[0]][name_path[1]]
            print(name)
        except Exception:
            print("Couldn't get name from contacts")
            name = ""
        summery = await self.generate_summery(text, interests, name)
        order+=1
        extend_commands.append(gen_general_command("fillInSummary", summery, "summary", order))
            
        return {"commands": extend_commands, "interests": interests, "order": order}
    

    async def classify_user_message(self, message: str, chat_history)->str:
        messages = [
                {"role": "system", "content": classification_system_prompt},
                {"role": "user", "content": get_classification_prompt(message, chat_history) + message + "'"}
            ]
        res = await self.openai_client.generate_response(messages)
        return res


    async def extract_info_from_text(self, text: str, fields: dict)->str:
        messages = [
                {"role": "system", "content": extract_form_system_prompt},
                {"role": "user", "content": prompt_fill_form_fields(fields) + text}
            ]
        print(messages)
        res = await self.openai_client.generate_response(messages)
        print("FIlled fields", res)
        res = str(res).strip("'<>() ").replace('\'', '\"').replace("Unknown", "")
        res = load_preprocess_json(res)

        return res
    

    async def _fill_forms_with_extra_info(self, information: str, fields: dict)->str:
        messages = [
            {"role": "user", "content": prompt_fill_form_fields_internet(fields, information)}
        ]
        res = await self.openai_client.generate_response(messages)
        res = str(res).strip("'<>() ").replace("Unknown", "")
        # .replace('\'', '\"') 
        # if isinstance(contact_fields, str):
        contact_fields = load_preprocess_json(res)
        return contact_fields
    

    async def extract_follow_ups(self, text: str):
        messages = [
                {"role": "system", "content": system_flollow_ups},
                {"role": "user", "content": get_folow_ups_prompt(text)}
            ]
        res = await self.openai_client.generate_response(messages)
        print("Add follow ups", res)
        res = load_preprocess_json(res)
        return res
    

    async def extract_list_interests(self, text: str, data: list):
        print("Extracting interests")
        # processed_interests = [{"id": interest["_Id"], "name": interest["_Name"]} for interest in data]
        prompt = get_extract_interests_prompt(text, data)
        
        messages = [
                {"role": "user", "content": prompt}
            ]
        res = await self.openai_client.generate_response(messages)
        print("List interests from gpt: ", res)
        res = load_preprocess_json(res)
        result = []
        for i in res:
            for interest in data:
                if i == interest["_Id"]:
                    result.append(interest)
        return result
    

    async def generate_summery(self, user_text: str, interests: list, user_name: str):
        names = [i["_Name"] for i in interests]
        prompt = get_summery_prompt(user_text, names, user_name)
         
        messages = [
                {"role": "user", "content": prompt}
            ]
        summery = await self.openai_client.generate_response(messages)
        return summery

    async def check_info_ask_for_extra_info(self, text, user_data, cmd_name, contact_fields, required_fields, order = 0):
        extend_commands = []
        print("Required fields: ", required_fields)
        print(type)
        if isinstance(required_fields[0], dict):
            required_fields = [i["Value"] for i in required_fields]
        if isinstance(contact_fields, str):
            contact_fields = load_preprocess_json(contact_fields)
        print(contact_fields)
        missing_fields = self.check_required_filled(contact_fields, required_fields)
        print("Missed", missing_fields)
        # add check for same json structure !!!
        if cmd_name:
            order += 1
            extend_commands.append(gen_general_command(cmd_name, value = contact_fields, val_type = "json", order = order))
        if missing_fields:
            order += 1
            msg = await self.generate_missing_field_message(text, missing_fields, not cmd_name, user_data = user_data)
            print('gen:', msg)
            extend_commands.append(gen_voice_play_command(msg, order, user_data.language))
            user_data.last_answer = msg
        return user_data, extend_commands

    def check_required_filled(self, full_form: dict, req_fields: list) -> list :
        print("Required fields: ", req_fields)
        missing_fields = []
        for full_name in req_fields:
            theme, field_name = full_name.split("_")
            if not full_form[theme][field_name]:
                print("Missing value: ", theme, field_name)
                missing_fields.append(f"{field_name} in section {theme}")
            else:
                print("Filled required field: ", theme, field_name)
        return missing_fields
    

    def _check_name_changes(self, new_info: dict, old_info: dict) -> bool: 
        first_name, second_name = new_info["GeneralInformation"]["FirstName"], new_info["GeneralInformation"]["LastName"]
        old_first_name, old_second_name = old_info["GeneralInformation"]["FirstName"], old_info["GeneralInformation"]["LastName"]
        if first_name == old_first_name and old_second_name == second_name:
            return False
        return True
    

    def _check_company_change(self, new_info: dict, old_info: dict) -> bool: 
        company= new_info["BusinessInformation"]["Company"] 
        old_company = old_info["BusinessInformation"]["Company"] 
        if company == old_company: 
            return False
        return True
    

    async def generate_missing_field_message(self, text: str, missing_fields: list, is_saving: bool, is_search: bool = False, user_data: UserData = None):
        prompt = get_missing_fields_prompt(text, missing_fields, is_saving, is_search, user_data.language)
        messages = [
                {"role": "user", "content": prompt}
            ]
        message = await self.openai_client.generate_response(messages)
        return message


    async def generate_general_answer(self, user_msg, lang: str = "de-DE"):
        prompt = get_general_answer_prompt(user_msg, lang)
        messages = [
                {"role": "user", "content": prompt}
            ]
        message = await self.openai_client.generate_response(messages)
        return message
    

    async def generate_not_in_callreport_answer(self, user_msg: str, lang: str = "de-DE"):
        prompt = get_prompt_not_in_call_report(user_msg, lang)
        messages = [
                {"role": "user", "content": prompt}
            ]
        message = await self.openai_client.generate_response(messages)
        return message

    
    
    async def gen_no_info_found(self, user_msg: str, lang: str = "de-DE"):
        prompt = get_prompt_no_info_found(user_msg, lang)
        messages = [
                {"role": "user", "content": prompt}
            ]
        message = await self.openai_client.generate_response(messages)
        return message
    

    async def _get_website(self, information):
        prompt = get_website_extraction_prompt(information)
        messages = [
                {"role": "user", "content": prompt}
            ]
        message = await self.openai_client.generate_response(messages)
        return message 
    
    @staticmethod
    def _is_call_report_nan(callreportID):
        return not callreportID or callreportID.lower() == "null" or callreportID.lower() == "none"