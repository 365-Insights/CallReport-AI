import json

with open("config/user_req_types.json") as f:
    dc = json.loads(f.read())
dc = list(dc.keys())

extract_form_system_prompt = "You are a highly accurate and efficient assistant designed to extract specific information from transcribed text. Your task is to extract the following data obtained using the Speech-to-Text service, check the spelling, and consider that it may be a dialogue. Correct first names if they appear unusual or incorrect."

# default_fields = '''"GeneralInformation": {"Gender": "", "FirstName": "", "LastName": ""},"BusinessInformation": {"Company": "", "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInformationAddress": "", "PositionLevel": "", "Department": "", "JobTitle": "", "Industry": "", "EducationLevel": "", "PhoneNumber": "", "MobilePhoneNumber": "", "BusinessEmail": ""}, "PersonalInformation": { "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInfoAddress": "", "PhoneNumber": "", "MobilePhoneNumber": "", "PersonalEMail": "" }'''
def prompt_fill_form_fields(fields):
    fields_no_required = json.dumps({k: val for k, val in fields.items() if k != 'RequiredFields'}, ensure_ascii=False)
    extract_form_user_prompt = f"""Return only a JSON object with all attributes in the exact format specified below, without any additional text or modifications: {fields_no_required}.
Do not include any explanations, return only the JSON object, and do not exclude attributes from the JSON even if they are empty, this is important.
[USER TEXT]: \n"""
    return extract_form_user_prompt


classification_list = "\n- ".join(dc)
print(classification_list)
classification_system_prompt = """You are an intelligent assistant designed to classify user messages into one of the following categories:
- Create contact
- Create a report
- Fill interests
- Update current contact
- Cancel
- Save document

When given a user message, you will analyze the content and return the name of the most appropriate category from the list above."""

classification_prompt = """Classify the following message into one of the categories: 'Create contact', 'Create a report', 'Fill interests', 'Update current contact', 'Add follow ups', 'Cancel', 'Save Document'.

Message: '"""

system_flollow_ups = """You are a highly accurate and efficient assistant designed to extract specific information from transcribed text. Your task is to extract the following data obtained using the Speech-to-Text service, check the spelling, and consider that it may be a dialogue."""
extract_follow_ups = """ Return only a JSON object with all attributes in the exact format specified below, without any additional text or modifications: 
{
"type": "",
"notes": "",
 "responsibleUser": ""
}.
Do not include any explanations, return only the JSON object, and do not exclude attributes from the JSON even if they are empty, this is important.
[USER TEXT]:
"""


def get_extract_interests_prompt(user_message, available_interests):
    prompt = f"""
    You are an intelligent assistant. Your task is to extract and fill in likely interests from a user's message based on a provided list of available interests. The available interests are in the following format:

    {available_interests}

    Given a user's message, identify and return the most likely interests from the list of available interests. The output should be a Python list of IDs.

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