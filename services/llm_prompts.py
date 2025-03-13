import json
from datetime import datetime

extract_form_system_prompt = "You are a highly accurate and efficient assistant designed to extract specific information from transcribed text. Your task is to extract the following data obtained using the Speech-to-Text service, check the spelling, and consider that it may be a dialogue. Correct first names if they appear unusual or incorrect."

# default_fields = '''"GeneralInformation": {"Gender": "", "FirstName": "", "LastName": ""},"BusinessInformation": {"Company": "", "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInformationAddress": "", "PositionLevel": "", "Department": "", "JobTitle": "", "Industry": "", "EducationLevel": "", "PhoneNumber": "", "MobilePhoneNumber": "", "BusinessEmail": ""}, "PersonalInformation": { "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInfoAddress": "", "PhoneNumber": "", "MobilePhoneNumber": "", "PersonalEMail": "" }'''
def prompt_fill_form_fields(fields):
    fields_no_required = json.dumps({k: val for k, val in fields.items() if k != 'RequiredFields'}, ensure_ascii=False)
    extract_form_user_prompt = f"""Return only a JSON object with all attributes in the exact format specified below, without any additional text or modifications: {fields_no_required}.
Do not include any explanations, return only the JSON object, and do not exclude attributes from the JSON even if they are empty, this is important.
[USER TEXT]: \n"""
    return extract_form_user_prompt


classification_system_prompt = """Your task is to analyze the current user message in the context of the conversation, which includes the **last bot response** and the **previous user message**. Based on this context, determine the most appropriate category from the list above. Always return **exactly one category** from the list, even if the message appears ambiguous. If the current user message does not clearly fit any of the categories, return "None."   
  
Provide no explanations or additional text, only the name of the selected category.  """
def get_classification_prompt(user_msg, bot_answer, last_msg):
    classification_prompt = f"""Classify the current user message into one of the predefined categories below. Use the descriptions provided for each category to make an informed decision:    
  
- **Create contact**: The user explicitly requests to create a new contact.   
  
- **Create report**: The user explicitly requests to generate or create a report.  
  
- **Fill interests**: The user mentions interests or preferences that should be recorded or updated, such as hobbies, likes, or areas of focus.    
  
- **Update contact info**: The user provides some information. If the intent is not to create a new contact but rather to modify or update existing details, classify it here.    
  
- **Add follow-ups**: The user indicates a need to create tasks, reminders, or action items to be followed up on in the future. These could involve scheduling a call, setting a meeting, or assigning a task.    
  
- **Cancel**: The user wants to cancel an action, task, or operation. This includes explicit requests to stop, abort, or discontinue a process.    
  
- **Save**: The user explicitly asks to save something, such as progress, settings, or changes they’ve made.    

- **None**: The user’s message does not match any of the above categories or is unclear in intent. Use this category if the message is ambiguous or unrelated to any predefined action.    
  
Use the following context to make your decision:    
- Last bot response: '{bot_answer}'    
- Last user message: '{last_msg}'    
  
**Rules:**    
1. Always return **exactly one category** from the list above.    
2. If the current user message is unclear or does not match any category, return "None."    
3. Provide no additional text or explanation—only the name of the selected category.    
  
Current user message: '{user_msg}'"""
    return classification_prompt


system_flollow_ups = """You are a highly accurate and efficient assistant designed to extract specific information from transcribed text. Your task is to extract the following data obtained using the Speech-to-Text service, check the spelling, and consider that it may be a dialogue."""
def get_folow_ups_prompt(user_text: str):
    print(user_text)
    td = datetime.now()
    extract_follow_ups = f'''Extract follow-ups details from the provided user text and return them in the exact JSON format specified below. Follow these rules strictly:    
1. The content of each attribute should be inferred and filled appropriately by the model based on the user text:    
   - `notes`: This represents the content or description of the follow-up, such as a task to complete, a call to make, or a meeting to schedule.    
   - `responsibleUser`: The person who is responsible for completing the follow-up.    
   - `datetime`: The specific date or time when the follow-up should be completed. (For you reference right now is {td})   
2. The `type` attribute must be one of the following options: ["task", "call", "meeting"].    
3. If specific details for an attribute are not explicitly mentioned in the user text, leave that attribute empty.    
4. Always include all attributes in the JSON object, even if they are empty.    
5. Do not include any additional text, explanations, or comments outside of the JSON object.    
  
JSON format for multiple follow-ups:    
[
{{    
  "type": "",    
  "notes": "",    
  "responsibleUser": "",    
  "datetime": ""    
}}, 
{{    
  "type": "",    
  "notes": "",    
  "responsibleUser": "",    
  "datetime": ""    
}}
] 
  
Input: [USER TEXT] - {user_text}    
Output: Return only the JSON object, strictly adhering to the format above.    '''
    print(333)
    return extract_follow_ups


def get_extract_interests_prompt(user_message, available_interests):
    prompt = f"""
    You are an intelligent assistant. Your task is to extract and fill in likely interests from a user's message based on a provided list of available interests. The available interests are in the following format:

    {available_interests}

    Given a user's message, identify and return the most likely interests from the list of available interests. The output should be only a Python list of IDs. If there is not relevant interests return empty list: []

    User message: "{user_message}"

    Output:
    """
    return prompt


def get_summery_prompt(user_text: str, interests: list):
    prompt = f"""You are an intelligent assistant. Your task is to generate a summary of a user's interests based on their message and a list of relevant interests. The relevant interests are provided in the following format:
{interests}
Given the user's message and the list of relevant interests, generate a summary that includes the names of the relevant interests and incorporates the user's message.

User message: {user_text}

Output:
"""
    return prompt


def get_missing_fields_prompt(user_message: str, missing_fields: list):  
    prompt = f"""  
    You are a friendly and intelligent assistant. Your task is to generate a polite, friendly, and clear message  
    to ask the user to provide missing required fields. The missing fields are provided in the list below, and the  
    user's message (if any) should be acknowledged politely.  

    Instructions:  
    1. If the user message is provided, briefly acknowledge it in a warm tone.  
    2. Clearly list the missing fields in a user-friendly format (e.g., as a bulleted list or a comma-separated list).  
    3. Politely ask the user to provide the missing information.  
    4. Maintain a conversational, approachable, and polite tone throughout. 
    5. Don't use formatting for text for example **word** 
    Your output should be concise, polite, and friendly. Here's the user's message and the missing fields:  
    User message: "{user_message}"  
    Missing fields: {missing_fields}  
  
    Output:  
    """  
    return prompt  


def get_general_answer_prompt(user_message):
    prompt = f"""The user hasn’t indicated a specific action or request. Respond in a friendly and engaging way, letting them know what you can assist with. Use the following categories to explain your capabilities:    
  
- Create contact    
- Create a report    
- Fill interests    
- Update contact info    
- Add follow-ups    
- Cancel    
- Save document    

Your tone should be polite, encouraging, and professional. Make the user feel welcome to ask for help if they need it. Keep your response brief and friendly.    
  
User Message: '{user_message}'  """
    return prompt


def get_prompt_not_in_call_report(user_msg: str):
    prompt = f"""The user has requested an action, but before proceeding with their request, they need to create a call report or open an existing one. Generate a polite and friendly response to inform the user of this requirement. Make sure the tone is supportive and encouraging, and clearly explain that creating or opening a call report is necessary before continuing.  
    
    If appropriate, offer guidance on how they can create or open a call report, or let them know you’re available to assist with this step.    
    
    User Message: "{user_msg}"  """
    return prompt