
from .openai_client import OpenAiClient
from .voice import fast_speech_recog, speech_recog, text2speech
from .llm_prompts import *
from .user_state import UserData
from .ai_agent import SearchAgent
from .commands import *
from utils import *

from uuid import uuid4
import asyncio
import os

name_path = ("GeneralInformation", "FirstName")
industry_path = "IndustryList"
default_fields = {"GeneralInformation": {"Gender": "", "FirstName": "", "LastName": ""},"BusinessInformation": {"Company": "", "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInformationAddress": "", "PositionLevel": "", "Department": "", "JobTitle": "", "Industry": "", "EducationLevel": "", "PhoneNumber": "", "MobilePhoneNumber": "", "BusinessEmail": ""}, "PersonalInformation": { "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInfoAddress": "", "PhoneNumber": "", "MobilePhoneNumber": "", "PersonalEMail": "" }}
required_fields = ["FirstName", "LastName", "Company", "BusinessEmail"]
industry_formated = ""

class VoiceBot:
    def __init__(self, openai_config: dict):
        self.BEST_MODEL = os.environ.get("best_model")
        self.openai_client = OpenAiClient(openai_config)
        self.users_states = {} # report_id to state
        self.ai_agent = SearchAgent()

    @timing()
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
        msg_type = await self.classify_user_message(user_text, user_data.chat_history, callreportID) 
        print("Put state as: ", msg_type)
        user_data.state = msg_type
        commands = []
        print(f"Classification: {msg_type} | with user text - {user_text}") 
        async with asyncio.TaskGroup() as tg:
            suggestion_task = tg.create_task( 
                self.generate_accompany_message(user_text, msg_type, user_data)
            )

            main_task  = tg.create_task(
                self.generate_answer(user_text, msg_type, form_data, user_data, callreportID)
            )
        commands, user_state, callreportID = main_task.result()
        accompany_text = suggestion_task.result()

        commands = validate_commands(commands)

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
    
    @timing()
    async def generate_answer(self, text: str, msg_type: str, form_data: dict,
                             user_state = None, call_report_id:str = False):
        global industry_formated, required_fields
        commands = []
        order = 0
        # print(msg_type)  
        contact_forms = form_data["ContactList"]
        main_contact = contact_forms[0]
        industry_formated = get_variant_of_fields(form_data)
        if "InterestsList" in form_data:
            interest_form = form_data["InterestsList"]

        if "Cancel" in msg_type:
            commands.append(gen_general_command(CommandType.CANCEL))
        if "Create report" in msg_type:
            command, call_report_id = self._create_call_report()
            order += 1
            msg_type += "Create contact"
            commands.append(command)
        
        if "None" in msg_type:
            answer = await self.generate_general_answer(text, user_state.language)
            user_state.last_answer = answer
            order += 1
            commands.append(gen_voice_play_command(answer, order, user_state.language))
            return commands, user_state, call_report_id
        elif self._is_call_report_nan(call_report_id) and not commands:
            print("Can't do this not inside call report with classification: ", msg_type)
            answer = await self.generate_not_in_callreport_answer(text, lang = user_state.language)
            user_state.last_answer = answer
            order += 1
            commands.append(gen_voice_play_command(answer, order, user_state.language))
            return commands, user_state, call_report_id
        
        tasks = []
        if "Create contact" in msg_type:  
            tasks.append(self._create_contact(text, contact_forms, user_state, call_report_id))  
        if "Update info" in msg_type:  
            required_fields = main_contact["RequiredFields"]  
            tasks.append(self.update_contact_info(text, contact_forms, user_state, call_report_id))  
        if "Fill interests" in msg_type:  
            tasks.append(self.fill_in_interests(text, interest_form, user_state, order))  
        if "Add follow-ups" in msg_type:  
            tasks.append(self._add_follow_ups(text, user_state))  
    
        # Execute all tasks concurrently  
        results = await asyncio.gather(*tasks)  

        # Process results from the gathered tasks  
        for result in results:  
            if result:
                extend_commands, user_state = result  
                if extend_commands:  
                    commands.extend(extend_commands)

        if "Save" in msg_type:
            extend_commands = []
            # required_fields = main_contact["RequiredFields"]
            # user_state, extend_commands = await self.check_info_ask_for_extra_info(text, user_state, "", contact_forms, required_fields, order)
            # if extend_commands and not self.check_for_voice_command(commands): 
            #     commands.extend(extend_commands)
            # elif not extend_commands: 
            commands.append(gen_general_command(CommandType.SAVE))
        

        return commands, user_state, call_report_id
    
    @timing()
    async def update_contact_info(self, text, contact_forms, user_data: UserData, call_report_id: str, order = 0):
        contact_fields = await self.extract_info_from_text(text, contact_forms, user_data.language)  
        old_contacts = user_data.contacts.get(call_report_id, {})
        if not old_contacts:
            old_contacts = contact_forms
        tasks = await self.update_internet_information(contact_fields, old_contacts, user_data.language)
        if tasks:
            tasks = [t for t in tasks if t is not None]
            internet_information = await asyncio.gather(*tasks)
            internet_info = []
            for t in internet_information:
                internet_info.append(t["info"])
                url = t.get("linkedin_url")
                if url:
                    print("Put linkedIn url update: ", url)
                    contact_fields = self.put_linkedin_url_by_id(contact_fields, url, t.get("contact_id"))

            internet_info = [t for t in internet_info if t is not None]
            internet_info = "\n\n".join(internet_info)
            contact_fields = await self._fill_forms_with_extra_info(internet_info, contact_fields, user_data.language)
        
        user_data.contacts[call_report_id] = contact_fields
        contact_fields = self.take_only_changed_contacts(contact_fields, old_contacts)
        # for contact in contact_fields:
        user_data, extend_commands = await self.check_info_ask_for_extra_info(text, user_data, CommandType.UPDATE_CONTACT, contact_fields, required_fields, order)
        return extend_commands, user_data
    
    @timing()
    async def update_internet_information(self, contact_fields: dict, old_contacts: dict, lang: str = "de-DE") -> list:
        all_companies = []
        tasks = []
        if not old_contacts:
            print("a new contact so get all internet info")
            for i, contact in enumerate(contact_fields):
                tasks.append(self.fill_internet_company_info(contact, lang))
                tasks.append(self.fill_internet_company_info(contact, lang))
            return tasks

        for i, contact in enumerate(contact_fields):
            contact_id = contact["GeneralInformation"]["ContactID"]
            company = contact["BusinessInformation"]["Company"]
            fname, surname = contact["GeneralInformation"]["FirstName"], contact["GeneralInformation"]["LastName"]
            for i, old_contact in enumerate(old_contacts):
                old_company = old_contact["BusinessInformation"]["Company"]
                old_fname, old_surname = old_contact["GeneralInformation"]["FirstName"], old_contact["GeneralInformation"]["LastName"]
                old_id = old_contact["GeneralInformation"]["ContactID"]
                if old_id == contact_id:
                    break
            if old_id != contact_id:
                continue
            if company not in all_companies and old_company != company:
                print("DIFFERENT COMPANIES")
                all_companies.append(company)
                tasks.append(self.fill_internet_company_info(contact, lang))
            if old_fname != fname or surname != old_surname:
                print("DIFFERENT NAMES")
                tasks.append(self.fill_internet_personal_info(contact, lang))
            print("CHECKED company and person.", fname, "Old", old_fname, "new", surname, "Old", old_surname)
        return tasks

    @timing()
    async def fill_internet_personal_info(self, user_form: dict, lang: str = "de-DE") -> list:
        print("FIll internet information")
        first_name, second_name = user_form["GeneralInformation"]["FirstName"], user_form["GeneralInformation"]["LastName"]
        if not all([first_name, second_name]):
            return 
        person = first_name + " " + second_name

        company = user_form["BusinessInformation"]["Company"] 
        country = user_form["PersonalInformation"]["Country"] 
        neccessary_info = (first_name, second_name, company)
        if not all(neccessary_info):
            return  None
        personal_info, linked_url = await self.ai_agent.get_person_info(person, company, country)
        if personal_info == "None":
            # answer = await self.gen_no_info_found(user_msg)
            # user_data.last_answer = answer
            # order += 1
            # commands.append(gen_voice_play_command(answer, order, user_data.language))
            # return  commands, user_data
            return None
        personal_info += f"\nLinkedin url: {linked_url}"
        contact_id = user_form["GeneralInformation"]["ContactID"]
        return {"info": personal_info, "linkedin_url": linked_url, "contact_id": contact_id}
    
    @timing()
    async def fill_internet_company_info(self, user_form: dict, lang = "de-DE"):
        print("FIll internet info about company") 
        company = user_form["BusinessInformation"]["Company"]  
        if not company:
            return 
        personal_info = await self.ai_agent.get_company_info(company)
        # print("Personal info: ", personal_info)
        if personal_info == "None":
            # answer = await self.gen_no_info_found(user_msg)
            # user_data.last_answer = answer
            # order += 1
            # commands.append(gen_voice_play_command(answer, order, user_data.language))
            return 
        website = await self._get_website(personal_info)
        print("Website: ", website)
        imprint_info = get_company_imprint(website)
         # print("Imprint info: ", imprint_info)
        if not imprint_info:
            imprint_info = ""
        if not website:
            website = ""
        full_info = personal_info + f"\nWebsite: {website}"+ "\nImprint info: " + str(imprint_info)
        return {"info": full_info}
    
    
    @timing()
    async def _add_follow_ups(self, text, user_data: UserData):
        follow_apps = await self.extract_follow_ups(text, user_data.language)
        return [gen_general_command(CommandType.ADD_FOLLOW_UPS, follow_apps, "list", 0)], user_data


    def _create_call_report(self, order = 0):
        call_report_id = str(uuid4())
        commands = gen_general_command(CommandType.CREATE_REPORT, value = {"CallReportID": call_report_id}, val_type="json", order = order)
        return commands, call_report_id
    
    @timing()
    async def _create_contact(self, text: str, form_data: dict, user_data: UserData, call_report_id: str = "", order = 0):
        global required_fields 
        extend_commands = []
        msg = ""
        required_fields = form_data[0]["RequiredFields"]
        cmd_name = CommandType.CREATE_CONTACT
        contact_fields = await self.extract_info_from_text(text, form_data, user_data.language)
        print("Extracted contact fields: ", contact_fields)
        # print("Fields BEFORE: ", contact_fields)
        all_companies = []
        tasks = []
        contact_fields = self.generate_contacts_ids(contact_fields)

        for i, contact in enumerate(contact_fields):
            company = contact["BusinessInformation"]["Company"]
            if company not in all_companies:
                all_companies.append(company)
                tasks.append(self.fill_internet_company_info(contact, user_data.language))
            tasks.append(self.fill_internet_personal_info(contact, user_data.language))
        internet_information = await asyncio.gather(*tasks)

        
        internet_info = []
        for t in internet_information:
            internet_info.append(t["info"])
            url = t.get("linkedin_url")
            if url:
                print("Put linkedIn url: ", url)
                contact_fields = self.put_linkedin_url_by_id(contact_fields, url, t.get("contact_id"))
        if internet_info:
            internet_info = "\n\n".join(internet_info)
            contact_fields = await self._fill_forms_with_extra_info(internet_info, contact_fields, user_data.language)
        
        # print("ENRICHED CONTACTS: ", type(contact_fields), contact_fields)
        user_data.contacts[call_report_id] = contact_fields
        extend_commands.append(gen_general_command(cmd_name, value = contact_fields, val_type = "json", order = order))
        main = False
        for contact in form_data:
            main = main or contact["GeneralInformation"]["MainContact"]
        if not main:
            for contact in contact_fields:
                main = main or contact["GeneralInformation"]["MainContact"]
        if not main and contact_fields:
            contact_fields[0]["GeneralInformation"]["MainContact"] = True
        # for contact in contact_fields:
        #     user_data, extend_commands = await self.check_info_ask_for_extra_info(text, user_data, cmd_name, contact, required_fields, order)
        return extend_commands, user_data

    @timing()
    async def fill_in_interests(self, text: str, payload, user_data: UserData, order = 0):
        extend_commands = []
        interests = None
        interests = await self.extract_list_interests(text, payload, user_data.language)
        print("Interests: ", interests)
        if interests:
            order += 1
            extend_commands.append(gen_general_command(CommandType.FILL_INTERESTS, interests, "list", order))
            try:
                # fix this
                contact_fields = user_data.contacts
                print(name_path)
                name = contact_fields[name_path[0]][name_path[1]]
                print(name)
            except Exception:
                print("Couldn't get name from contacts")
                name = ""
            summery = await self.generate_summery(text, interests, name, user_data.language)
            order+=1
            extend_commands.append(gen_general_command(CommandType.FILL_IN_SUMMARY, summery, "summary", order))
            return extend_commands, user_data
        else:
            print("No relevant interests found. ")
            return 
        
    
    @timing()
    async def classify_user_message(self, message: str, chat_history, call_report_id: str = None)->str:
        messages = [
                {"role": "system", "content": classification_system_prompt},
                {"role": "user", "content": get_classification_prompt(message, chat_history, call_report_id) + message + "'"}
            ]
        res = await self.openai_client.generate_response(messages, max_tokens = 100, model_name = self.BEST_MODEL, top_p = 0.7)
        return res

    @timing()
    async def extract_info_from_text(self, text: str, fields: dict, lang: str = "de-DE")->str:
        messages = [
                {"role": "system", "content": extract_form_system_prompt},
                {"role": "user", "content": prompt_fill_form_fields(fields, lang) + text}
            ]
        res = await self.openai_client.generate_response(messages)
        # print("FIlled fields", res)
        res = str(res).strip("'<>() ").replace('\'', '\"').replace("Unknown", "")
        res = load_preprocess_json(res)

        return res
    
    @timing()
    async def _fill_forms_with_extra_info(self, information: str, fields, language: str = "de-DE")->str:
        messages = [
            {"role": "user", "content": prompt_fill_form_fields_internet(fields, information, language)}
        ]
        res = await self.openai_client.generate_response(messages)
        res = str(res).strip("'<>() ").replace("Unknown", "")
        # .replace('\'', '\"') 
        # if isinstance(contact_fields, str):
        contact_fields = load_preprocess_json(res)
        return contact_fields
    

    async def extract_follow_ups(self, text: str, lang: str = "de-DE"):
        messages = [
                {"role": "system", "content": system_flollow_ups},
                {"role": "user", "content": get_folow_ups_prompt(text, lang)}
            ]
        res = await self.openai_client.generate_response(messages)
        print("Add follow ups", res)
        res = load_preprocess_json(res)
        return res
    
    @timing()
    async def extract_list_interests(self, text: str, data: list, lang: str = "de-DE"):
        print("Extracting interests")
        # processed_interests = [{"id": interest["_Id"], "name": interest["_Name"]} for interest in data]
        prompt = get_extract_interests_prompt(text, data, lang)
        
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
    
    @timing()
    async def generate_summery(self, user_text: str, interests: list, user_name: str, lang: str = "de-DE"):
        names = [i["_Name"] for i in interests]
        prompt = get_summery_prompt(user_text, names, user_name, lang)
        messages = [
                {"role": "user", "content": prompt}
            ]
        summery = await self.openai_client.generate_response(messages)
        return summery
    
    @timing()
    async def check_info_ask_for_extra_info(self, text: str, user_data, cmd_name: str, contact_fields: list, required_fields, order = 0):
        extend_commands = []
        print("Required fields: ", required_fields)
        if isinstance(required_fields[0], dict):
            required_fields = [i["Value"] for i in required_fields]
        if isinstance(contact_fields, str):
            contact_fields = load_preprocess_json(contact_fields)
        missing_fields = []
        for contact in contact_fields:
            missing_fields.extend(self.check_required_filled(contact, required_fields))
        missing_fields = list(set(missing_fields))
        print("Missed", missing_fields)
        # add check for same json structure !!!
        if cmd_name:
            order += 1
            extend_commands.append(gen_general_command(cmd_name, value = contact_fields, val_type = "json", order = order))
        if missing_fields:
            order += 1
            msg = await self.generate_missing_field_message(text, missing_fields, not cmd_name, user_data = user_data)
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


    @staticmethod
    def generate_contacts_ids(contacts: list):
        for contact in contacts:
            contact["GeneralInformation"]["ContactID"] = str(uuid4())
        
        return contacts

    @staticmethod
    def take_only_changed_contacts(new_contacts: list, old_contacts: list):
        final_contacts = []
        for new in new_contacts:
            n_id = new["GeneralInformation"]["ContactID"]
            o_id, old_c = None, None
            for old in old_contacts:
                o_id = old["GeneralInformation"]["ContactID"]
                if o_id == n_id:
                    old_c = old
                    break
            if o_id == n_id and new == old_c:
                print("The same contacts:", old == new)
            else:
                print(o_id, n_id)
                final_contacts.append(new)
        return final_contacts
    
    @staticmethod
    def put_linkedin_url_by_id(contacts: list, linkedin_url: str, contact_id: str):
        print("CONTACT ID:", contact_id)
        for contact in contacts:
            n_id = contact["GeneralInformation"]["ContactID"]
            if contact_id == n_id:
                print("Contact: ", contact)
                for k, val in contact.items():
                    if isinstance(val, dict) and "LinkedinUrl" in val:
                        print("Section: ", k)
                        contact[k]["LinkedinUrl"] = linkedin_url
                    elif "LinkedinUrl" in contact:
                        contact["LinkedinUrl"] = linkedin_url
                    else:
                        print("Didn't find any linked in url")
                # contact["PersonalInformation"]["LinkedinUrl"]
        return contacts
