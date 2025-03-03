
from .openai_client import OpenAiClient

extract_form_system_prompt = "You are a highly accurate and efficient assistant designed to extract specific information from transcribed text. Your task is to extract the following data obtained using the Speech-to-Text service, check the spelling, and consider that it may be a dialogue. Correct first names if they appear unusual or incorrect."
extract_form_user_prompt = """Return only a JSON object with all attributes in the exact format specified below, without any additional text or modifications: 'GeneralInformation: Gender, FirstName, LastName; BusinessInformation: Company, City, Country, Street, HouseNumber, PostalCode, AditionalInformationAddress, PositionLevel, Department, JobTitle, Industry, EducationLevel, PhoneNumber, MobilePhoneNumber, BusinessEmail; PersonalInformation: City, Country, Street, HouseNumber, PostalCode, AditionalInfoAddress, PhoneNumber, MobilePhoneNumber, PersonalEMail' .
Do not include any explanations, return only the JSON object, and do not exclude attributes from the JSON even if they are empty, this is important.
[USER TEXT]: \n"""

async def extract_info_from_text(text: str, openai_client: OpenAiClient):
    messages = [
            {"role": "system", "content": extract_form_system_prompt},
            {"role": "user", "content": extract_form_user_prompt + text}
        ]
    res = await openai_client.generate_response(messages)
    return res