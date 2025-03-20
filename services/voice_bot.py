
from .openai_client import OpenAiClient
from .voice import fast_speech_recog, speech_recog, text2speech
from .llm_prompts import *
from utils import convert_base64_audio_to_wav, lang2voice, load_preprocess_json
from uuid import uuid4
from .user_state import UserData
import asyncio

default_fields = {"GeneralInformation": {"Gender": "", "FirstName": "", "LastName": ""},"BusinessInformation": {"Company": "", "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInformationAddress": "", "PositionLevel": "", "Department": "", "JobTitle": "", "Industry": "", "EducationLevel": "", "PhoneNumber": "", "MobilePhoneNumber": "", "BusinessEmail": ""}, "PersonalInformation": { "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInfoAddress": "", "PhoneNumber": "", "MobilePhoneNumber": "", "PersonalEMail": "" }}
required_fields = ["FirstName", "LastName", "Company", "BusinessEmail"]

class VoiceBot:
    def __init__(self, openai_config: dict, speech_config: dict = None):
        self.openai_client = OpenAiClient(openai_config)
        self.users_states = {} # report_id to state


    async def process_user_message(self, lang: str = "de-DE", request_type: str = "", session_id: str = None, callreportID: str = None, payload = {}, form_type: str = ""):
        file_id = uuid4()        
        # if session_id:
        user_data = self.users_states.get(session_id)
        if not user_data:
            print("Creating new user data")
            user_data = UserData(session_id, "default", {}, "", "", lang)
        last_message = user_data.last_message
        last_answer = user_data.last_answer
            
        user_text = "" 
        if request_type == "record":  
            audio_path = f"temp/{file_id}.wav"  
            try:  
                output_path = convert_base64_audio_to_wav(payload, audio_path)  
                user_text, lang = fast_speech_recog(output_path)  
                user_data.language = lang
                print("USER TEXT: ", user_text)
            except Exception as e:  
                raise RuntimeError(f"Audio processing failed: {str(e)}")  
            # Classify user message into one of the categories/commands
            msg_type = await self.classify_user_message(user_text, user_data.chat_history) 
            print("Put state as: ", msg_type)
            user_data.state = msg_type
            commands = []
            order = 1
            if msg_type == "Fill insterests": 
                commands.append(self.gen_general_command("giveListInterests", order = order))
            elif msg_type in ["Update contact info", "Create contact", "Create report"] or (msg_type == "Save" and form_type == "contact"):    
                commands.append(self.gen_general_command("giveListContactFilds", order = order))
            print("Givelist command")
            if commands:
                user_data.last_message = user_text 
                self.users_states[session_id] = user_data
                user_data.last_message = user_text 
                return self.form_response(commands, user_data.session_id)
        elif request_type in ["listInterests", "listContactFields"]:  
            payload = load_preprocess_json(payload)
            user_text = last_message 
            msg_type = user_data.state 
        else:  
            raise ValueError(f"Unsupported request_type: {request_type}")  
        print(f"Classification: {msg_type} | with user text - {user_text}") 
        not_in_call_report =  not callreportID or callreportID.lower() == "null" or callreportID.lower() == "none"
        async with asyncio.TaskGroup() as tg:
            suggestion_task = tg.create_task( 
                self.generate_accompany_message(user_text, msg_type, user_data.chat_history))

            main_task  = tg.create_task(
                self.generate_answer(user_text, msg_type, request_type, payload, user_data, not_in_call_report, form_type)
            )
        commands, user_state = main_task.result()
        accompany_text = suggestion_task.result()

        if not self.check_for_voice_command(commands):
            print("Don't have voice command so add accompany text")
            accompany_audio = self.gen_voice_play_command(accompany_text, commands[-1]["order"]+1, user_data.language)
            commands.append(accompany_audio)
        user_state.last_message = user_text 
        self.users_states[session_id] = user_state
        response = self.form_response(commands, session_id)
        return response
    
    async def generate_accompany_message(self, user_msg: str, category: str, chat_history):
        category = category.replace("report", "contact")
        messages = [
                {"role": "user", "content": get_suggestion_prompt(user_msg, category, chat_history)}
            ]
        text = await self.openai_client.generate_response(messages)
        return text
    

    def check_for_voice_command(self, commands: list):
        for command in commands:
            if command["name"] == 'playBotVoice' or command["name"] == "giveListContactFilds" or command["name"] == "giveListInterests":
                return True
        return False


    async def form_error_resonse(self, session_id):
        messages = [
                {"role": "user", "content": prompt_error_occured}
            ]
        text = await self.openai_client.generate_response(messages)
        commands = [self.gen_voice_play_command(text, 1, "de-DE")]
        return self.form_response(commands, session_id)


    def form_response(self, commands: list, session_id: str = None) -> dict:
        return {
            "commands": commands,
            "sessionID": session_id
        }
    

    async def generate_answer(self, text, msg_type, request_type: str, payload = None, user_state = None, not_in_call_report = False, form_type = ""):
        commands = []
        order = 0
        print(msg_type)
        print(not_in_call_report)
        if msg_type == "Create contact" or msg_type == "Create report":
            res, user_state = await self._create_contact(text, payload, user_state, request_type, order)
            commands.extend(res["commands"])
            order = res["order"]
        elif msg_type == "None":
            answer = await self.generate_general_answer(text)
            user_state.last_answer = answer
            order += 1
            commands.append(self.gen_voice_play_command(answer, order, user_state.language))
        elif not_in_call_report:
            print("Can't do this not inside call report with classification: ", msg_type)
            answer = await self.generate_not_in_callreport_answer(text, lang = user_state.language)
            user_state.last_answer = answer
            order += 1
            commands.append(self.gen_voice_play_command(answer, order, user_state.language))
        elif msg_type == "Fill interests":
            res = await self.fill_in_interests(text, payload, user_state, request_type, order)
            order = res.get("order", 0)
            commands.extend(res["commands"])

        elif msg_type == "Update contact info":
            if isinstance(payload, dict):
                default_fields = payload
            required_fields = payload["RequiredFields"]
            cmd_name = "updateCurrentContact"
            contact_fields = await self.extract_info_from_text(text, payload)
            user_state, extend_commands = await self.check_info_ask_for_extra_info(text, user_state, cmd_name, contact_fields, required_fields, order)
            # contact = await self.extract_info_from_text(text, contact_fields)
            # user_state, new_commands = await self.check_info_ask_for_extra_info(text, user_state, "updateCurrentContact", contact, required_fields, order)
            commands.extend(extend_commands)
        elif msg_type == "Cancel":
            order += 1
            commands.append(self.gen_general_command("Cancel", order = order))
        elif msg_type == "Save":
            order += 1
            extend_commands = []
            if form_type == "contact":
                required_fields = payload["RequiredFields"]
                user_state, extend_commands = await self.check_info_ask_for_extra_info(text, user_state, "", payload, required_fields, order)
            if extend_commands:
                commands.extend(extend_commands)
            else:
                commands.append(self.gen_general_command("saveCurrentDocument", order = order))
        elif msg_type == "Add follow-ups":
            follow_apps = await self.extract_follow_ups(text)
            order += 1
            commands.append(self.gen_general_command("addFollowUps", follow_apps, "list", order))
        
        return commands, user_state
    

    async def _create_contact(self, text: str, payload, user_data: UserData, request_type: str, order = 0):
        global required_fields, default_fields
        extend_commands = []
        is_give_list = 0
        msg = ""
        
        # required_fields = ["FirstName", "LastName", "Company", "BusinessEmail"]
        if user_data.state == "fill_required":
            contact_fields = await self.extract_info_from_text(text, user_data.history_data.get("contact_fields"))
            print(user_data.history_data.get("contact_fields"))
            cmd_name = "updateCurrentContact"
        else: # if we
            # print(load_preprocess_json(payload))
            if isinstance(payload, dict):
                default_fields = payload
            required_fields = payload["RequiredFields"]
            cmd_name = "createContact"
            contact_fields = await self.extract_info_from_text(text, payload)
        user_data, extend_commands = await self.check_info_ask_for_extra_info(text, user_data, cmd_name, contact_fields, required_fields, order)
            
        return {"commands": extend_commands, "contact_fields": contact_fields, "order": order, "is_give_list": is_give_list, "answer": msg}, user_data


    async def fill_in_interests(self, text: str, payload, user_data: UserData, request_type: str, order = 0):
        extend_commands = []
        interests = None
        if request_type == "record":
            command_name = "giveListInterests"
            order += 1
            extend_commands.append(self.gen_general_command(command_name, order = order))
        else:
            command_name = "fillInterests"
            interests = await self.extract_list_interests(text, payload)
            order += 1
            extend_commands.append(self.gen_general_command(command_name, interests, "list", order))
            summery = await self.generate_summery(text, interests)
            order+=1
            extend_commands.append(self.gen_general_command("fillInSummary", summery, "summary", order))
            
        return {"commands": extend_commands, "interests": interests, "order": order}
    

    async def classify_user_message(self, message: str, chat_history):
        messages = [
                {"role": "system", "content": classification_system_prompt},
                {"role": "user", "content": get_classification_prompt(message, chat_history) + message + "'"}
            ]
        res = await self.openai_client.generate_response(messages)
        return res


    async def extract_info_from_text(self, text: str, fields: dict):
        messages = [
                {"role": "system", "content": extract_form_system_prompt},
                {"role": "user", "content": prompt_fill_form_fields(fields) + text}
            ]
        res = await self.openai_client.generate_response(messages)
        print("FIlled fields", res)
        return str(res).strip("'<>() ").replace('\'', '\"')
    

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
    

    async def generate_summery(self, user_text: str, interests: list):
        names = [i["_Name"] for i in interests]
        prompt = get_summery_prompt(user_text, names)
         
        messages = [
                {"role": "user", "content": prompt}
            ]
        summery = await self.openai_client.generate_response(messages)
        return summery

    async def check_info_ask_for_extra_info(self, text, user_data, cmd_name, contact_fields, required_fields, order = 0):
        extend_commands = []
        if isinstance(required_fields[0], dict):
            required_fields = [i["Value"] for i in required_fields]
        if isinstance(contact_fields, str):
            contact_fields = load_preprocess_json(contact_fields)
        user_data.history_data["contact_fields"] = contact_fields
        print(contact_fields)
        missing_fields = self.check_required_filled(contact_fields, required_fields)
        print("Missed", missing_fields)
        # add check for same json structure !!!
        if cmd_name:
            order += 1
            extend_commands.append(self.gen_general_command(cmd_name, value = contact_fields, val_type = "json", order = order))
        if missing_fields:
            user_data.state = "fill_required"
            order += 1
            msg = await self.generate_missing_field_message(text, missing_fields, not cmd_name)
            extend_commands.append(self.gen_voice_play_command(msg, order, user_data.language))
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
    

    def _generate_audio(self, text, lang = "en-US"):
        voice = lang2voice.get(lang, "en-US-AvaMultilingualNeural")
        audio_data, duration = text2speech(text, voice)
        return audio_data, duration


    # @staticmethod
    def gen_voice_play_command(self, text: str, order = 1, lang = "en-US"):
        audio_data, duration = self._generate_audio(text, lang)
        val = {
                "record": audio_data,
                "textMessage": text,
                "duration": duration
                }
        voice_play = self.gen_general_command("playBotVoice", val, "record", order)
        return voice_play
    
    async def generate_missing_field_message(self, text: str, missing_fields: list, is_saving: bool):
        prompt = get_missing_fields_prompt(text, missing_fields, is_saving)
        messages = [
                {"role": "user", "content": prompt}
            ]
        message = await self.openai_client.generate_response(messages)
        return message


    async def generate_general_answer(self, user_msg):
        prompt = get_general_answer_prompt(user_msg)
        messages = [
                {"role": "user", "content": prompt}
            ]
        message = await self.openai_client.generate_response(messages)
        return message
    

    async def generate_not_in_callreport_answer(self, user_msg: str, lang: str = "de-DE"):
        prompt = get_prompt_not_in_call_report(user_msg)
        messages = [
                {"role": "user", "content": prompt}
            ]
        message = await self.openai_client.generate_response(messages)
        return message

    @staticmethod
    def gen_general_command(command_name: str, value = {}, val_type: str = dict, order: int = 1):
        command = {
            "name": command_name,
            "order": order,
            "parameters": {}
        }
        if value and val_type:
            command["parameters"]["value"] = value
            command["parameters"]["type"] = val_type
        return command
    
