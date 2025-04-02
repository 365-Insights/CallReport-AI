import json
from datetime import datetime

from utils import locale2lang

variant_fields = ["IndustryValues"]
skip_sections = variant_fields + ["RequiredFields"]

def get_formatted_history(chat_history) -> str:
    formatted_history = "\n".join(  
        [f"User: {entry['user_msg']}\nBot: {entry['bot_answer']}" for entry in chat_history]  
    )  
    return formatted_history
extract_form_system_prompt = "You are a highly accurate and efficient assistant designed to extract specific information from transcribed text. Your task is to extract the following data obtained using the Speech-to-Text service, check the spelling, and consider that it may be a dialogue. Correct first names if they appear unusual or incorrect."

def get_variant_of_fields(full_form):
    text = ""
    for field in variant_fields:
        if not full_form.get(field): 
            continue
        variations = [i["Value"] for i in full_form.get(field, [])]
        field = field.replace("Values", "")
        text += f"{field} - {variations}"
    print("Variations: ", text)
    if text:
        text = "\nCertain fields can have only specific values:\n" + text 
    return text

# default_fields = '''"GeneralInformation": {"Gender": "", "FirstName": "", "LastName": ""},"BusinessInformation": {"Company": "", "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInformationAddress": "", "PositionLevel": "", "Department": "", "JobTitle": "", "Industry": "", "EducationLevel": "", "PhoneNumber": "", "MobilePhoneNumber": "", "BusinessEmail": ""}, "PersonalInformation": { "City": "", "Country": "", "Street": "", "HouseNumber": "", "PostalCode": "", "AdditionalInfoAddress": "", "PhoneNumber": "", "MobilePhoneNumber": "", "PersonalEMail": "" }'''
def prompt_fill_form_fields(fields):
    field_variations = get_variant_of_fields(fields)
    fields_no_required = json.dumps({k: val for k, val in fields.items() if k not in skip_sections}, ensure_ascii=False)
    extract_form_user_prompt = f"""Return only a JSON object with all attributes in the exact format specified below, without any additional text or modifications: {fields_no_required}.
Do not include any explanations, return only the JSON object, and do not exclude attributes from the JSON even if they are empty, this is important.
{field_variations}
[USER TEXT]: \n"""
    return extract_form_user_prompt


classification_system_prompt = """Your task is to analyze the current user message in the context of the conversation, which includes the **last bot response** and the **previous user message**. Based on this context, determine the most appropriate category from the list above. Always return **exactly one category** from the list, even if the message appears ambiguous. If the current user message does not clearly fit any of the categories, return "None."   
  
Provide no explanations or additional text, only the name of the selected category.  """
def get_classification_prompt(user_msg, chat_history):  
    formatted_history = get_formatted_history(chat_history)  
    ### Chat History:  
    classification_prompt = f"""  
Classify the current user message into one of the predefined categories below. Use the descriptions provided for each category to make an informed decision:  
- **Create contact**: The user explicitly requests to create a new contact.  
- **Create report**: The user explicitly requests to generate or create a report.  
- **Fill interests**: The user mentions interests or preferences that should be recorded or updated, such as hobbies, likes, or areas of focus.  
- **Update contact info**: The user provides some information. If the intent is not to create a new contact but rather to modify or update existing details or fill in some contact information, classify it here. This includes follow-up messages providing additional details such as 'The name is Cloud Value.' or could be general message "My name is Sasha"
- **Add follow-ups**: The user indicates a need to create tasks, reminders, or action items to be followed up on in the future. These could involve scheduling a call, setting a meeting, or assigning a task.  
- **Find person information**: The user asks to fill information about himself with data from the Internet. This could be a request like 'automatically fill in my personal info' or 'find information about me on the internet.'  
- **Find company information**: The user asks to fill some company information using data from the Internet. This could be a request like 'automatically fill in my company info' or 'find information about my company on the internet.' This does not include follow-up messages providing specific details like company names.  
- **Cancel**: The user wants to cancel an action, task, or operation. This includes explicit requests to stop, abort, or discontinue a process.  
- **Save**: The user explicitly asks to save something, such as progress, settings, or changes they’ve made.  
- **None**: The user’s message does not match any of the above categories or is unclear in intent. Use this category if the message is ambiguous or unrelated to any predefined action.  
  
Use the following context to make your decision:  
### Chat History: {formatted_history}  
**Rules:**  
1. Always return **exactly one category** from the list above.  
2. If the current user message is unclear or does not match any category, return "None."  
3. Provide no additional text or explanation—only the name of the selected category.  
  
Current user message: '{user_msg}'  
"""  
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

    Given a user's message, identify and return the most likely interests from the list of available interests. The output should be only a Python list of IDs use double quotes for ids. If there is not relevant interests return empty list: []

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

def get_missing_fields_prompt(user_message: str, missing_fields: list, is_saving: bool = False, is_search: bool = False, locale: str = "de-DE"):  
    # Base prompt  
    prompt = f"""  
    You are a friendly and intelligent assistant. Your task is to generate a polite, friendly, and clear message to ask the user for missing required information. The missing fields are provided in the list below, and the user's message (if any) should be acknowledged politely.  
  
    Instructions:  
    1. If the user message is provided, briefly acknowledge it in a warm tone.  
    2. Instead of listing the missing fields directly, ask for them individually in the form of polite questions. For example, instead of saying "The missing fields are: First name, Last name," ask "Could you please tell me your first name?" or "May I have your last name, please?"  
    3. Politely ask the user to provide the requested information one by one, phrased as natural and conversational questions.  
    4. Maintain a conversational, approachable, and polite tone throughout.  
    5. Your output will be used in a text-to-speech (TTS) system, so it is critical that the text is plain and free of any special formatting or symbols.  
    6. When responding to a user's message, always reply in '{locale2lang[locale]}'
    """  
  
    # Add specific instructions if the `is_saving` flag is True  
    if is_saving: 
        print("can't save without all info") 
        prompt += """  
    Additional context:  
    The user is trying to save a contact but hasn't provided all the necessary fields. Please inform the user that saving the contact is not possible without these fields, and kindly prompt them to provide the missing information.  
    """  
    if is_search: 
        prompt += """  
    Additional context:  
    The user is asking bot to find additional information about him or his company, but we don't have all info for the search. Please inform the user that automatically filling form(searching for info) is not possible without these fields, and kindly prompt them to provide the missing information.  
    """  
    # Append the user's message and missing fields to the prompt  
    prompt += f"""  
    Here's the user's message and the missing fields:  
  
    User message: "{user_message}"  
    Missing fields: {missing_fields}  
  
    Output:  
    """  
  
    return prompt  


def get_general_answer_prompt(user_message, locale: str = "de-DE"):
    prompt = f"""The user hasn’t indicated a specific action or request. Respond in a friendly and engaging way, letting them know what you can assist with. Use the following categories to explain your capabilities:    

- Create contact    
- Create a report    
- Fill interests    
- Update contact info    
- Add follow-ups    
- Cancel    
- Save document    
- Autofill some company information using internet
- Autofill some personal information using internet
RULES:
1. When responding to a user's message, always reply in '{locale2lang[locale]}'
2. Your output will be used in a text-to-speech (TTS) system, so it is critical that the text is plain and free of any special formatting or symbols.
3. Your tone should be polite, encouraging, and professional. Make the user feel welcome to ask for help if they need it. Keep your response brief and friendly.    
  
User Message: '{user_message}'  """
    return prompt


def get_prompt_not_in_call_report(user_msg: str, locale: str = "de-DE"):
    prompt = f"""The user has requested an action, but before proceeding with their request, they need to create a call report or open an existing one. Generate a polite and friendly response to inform the user of this requirement. Make sure the tone is supportive and encouraging, and clearly explain that creating or opening a call report is necessary before continuing.  
    RULES:
    1. Your output will be used in a text-to-speech (TTS) system, so it is critical that the text is plain and free of any special formatting or symbols.
    2. When responding to a user's message, always reply in '{locale2lang[locale]}'
    3. If appropriate, offer guidance on how they can create or open a call report, or let them know you’re available to assist with this step.    
    
    User Message: "{user_msg}"  """
    return prompt


def get_error_prompt(locale: str = "de-DE"):
    prompt_error_occured = f"""  
    Generate a polite, user-friendly error message to notify the user that an issue has occurred while processing their request. The message should acknowledge the failure, reassure the user, and encourage them to try again. Avoid technical jargon and maintain a tone that is friendly, empathetic, and professional.  
    
    ### Steps:  
    1. Politely acknowledge that an issue has occurred.  
    2. Briefly inform the user that their request could not be completed due to the error.  
    3. Reassure the user that the issue is likely temporary or fixable.  
    4. Encourage the user to try their request again.  
    5. Optionally offer help or suggest contacting support if the issue persists.  
    6. Your output will be used in a text-to-speech (TTS) system, so it is critical that the text is plain and free of any special formatting or symbols.
    7. Response should be in '{locale2lang[locale]}'
    
    ### Output Format:  
    - Tone: Friendly, polite, and supportive.  
    - Length: 1–2 sentences.  
    
    ### Examples:  
    1. "Oops! Something went wrong while processing your request. Please try again in a moment."  
    2. "We're sorry, but we encountered an issue while handling your request. Please try again shortly."  
    3. "Uh-oh, it looks like something went wrong. Don’t worry—please give it another shot!"  
    4. "Apologies! We hit a small snag while processing your request. Please try again, and thank you for your patience."  
    5. "Something went wrong on our end. Please try again, and let us know if the issue persists."  
    """  
    return prompt_error_occured

def get_suggestion_prompt(user_message: str, category: str, chat_history: list, locale: str = "de-DE") -> str:  
    # Format the chat history into a readable string for the prompt  
    formatted_history = get_formatted_history(chat_history)
    prompt = f"""  
You are a helpful and proactive assistant. Your task is to provide a useful suggestion to the user based on their message, the specified task category, and the full chat history. Each category has a unique purpose, and your suggestion should guide the user toward completing the task effectively or improving the outcome and they should be pretty short.  
### Instructions:  
1. Understand the user's message, the task category, and the context provided by the chat history.  
2. Use the chat history to avoid repeating previous bot responses unnecessarily. If a suggestion or confirmation has already been provided, generate a new response that adds value or addresses a different aspect of the task.  
3. If the category is **Cancel**, simply confirm the action has been canceled without recommending further steps. Use varied phrasing to keep the response engaging.  
4. Ensure your tone is friendly, encouraging, and action-oriented.  
5. Your output will be used in a text-to-speech (TTS) system, so it is critical that the text is plain and free of any special formatting or symbols.  
6. When responding to a user's message, always reply in '{locale2lang[locale]}'
### Chat History:  
{formatted_history}  
  
### Current User Message:  
{user_message}  
  
### Category:  
{category}  
  
### Categories and Suggestions:  
- **Create contact**: If the user has mentioned their name or second name previously in the chat history, suggest they recheck the spelling to ensure it is correct. Otherwise, suggest they fill in more fields generally or move to another section like filling interests.  
- **Fill interests**: Suggest the user review the recorded interests to ensure they are complete or ask them to mention any missing ones that should be added.  
- **Update contact info**: Recommend the user double-check the updated details if provided info could have been mistranscribed in spelling or suggest adding any missing fields that could be relevant.  
- **Add follow-ups**: Propose that the user add more follow-ups if needed, or suggest related actions like filling in interests or checking if all details are correct for the follow-up tasks.  
- **Cancel**: Confirm the cancellation with a friendly and varied response, like: "Sure, the action has been canceled." Use alternate phrasing to keep the response fresh.  
- **Save document**: Reassure the user that their document has been saved and suggest reviewing the saved content to ensure everything is accurate.  
- **Find person information**: Suggest the user verify the accuracy of the information found about themselves by our bot and ask if there are any specific details they would like to update or add.  
- **Find company information**: Recommend the user review the gathered company information by our bot for accuracy and completeness, and ask if there are additional details needed about the company. 
  
Now, generate a suggestion for the user:  
"""  
    return prompt 


def prompt_fill_form_fields_internet(fields, internet_info_text):  
    # Create the prompt with instructions for GPT to fill in the fields  
    field_variations = get_variant_of_fields(fields)
    fields_no_required = json.dumps({k: val for k, val in fields.items() if k not in skip_sections}, ensure_ascii=False)
    # fields_no_required = json.dumps(fields, ensure_ascii=False)  

    extract_form_internet_prompt = f"""  
Given the following information text:  
  
"{internet_info_text}"  
  
Return only a JSON object with all attributes in the exact format specified below, without any additional text or modifications. 
Prioritize existing values in the form if they are already filled. And don't forget to fill summery fields for appropriate section if they are empty. Don't confuse summery in different sections, only fill in one that you have info about. 
Do not include any explanations, return only the JSON object, and do not exclude attributes from the JSON even if they are empty. This is important.  
{field_variations}
Form fields:  
{fields_no_required}  
""" 
    return extract_form_internet_prompt 

def get_prompt_no_info_found(user_msg: str, locale: str = "de-DE"):  
    prompt = f"""  
    The user has requested to fill extra information in the form automatically. Generate a polite and friendly response to inform the user that, unfortunately, no information was found about them on the internet to fill in the extra info automatically. Encourage them to fill in the information manually.  
  
    RULES:  
    1. Your output will be used in a text-to-speech (TTS) system, so it is critical that the text is plain and free of any special formatting or symbols.  
    2. When responding to a user's message, always reply in '{locale2lang[locale]}'
    3. If appropriate, offer guidance on how they can fill in the information manually, and let them know you’re available to assist with this step.  
  
    User Message: '{user_msg}'
    """  
    return prompt  

def get_website_extraction_prompt(info: str) -> str:  
    prompt = f"""  
    The user has provided the following company information. Extract the URL of the official company website from the provided information.  
      
    Provided Information:  
    {info}  
  
    Your response should only contain the URL of the official website and nothing else.  
    Example of output: 'https://www.microsoft.com/'
    """  
    return prompt