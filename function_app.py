import os
import logging
import asyncio
import json
import traceback
import azure.cognitiveservices.speech as speechsdk
import azure.functions as func
from dotenv import load_dotenv


from services import *
from utils.config import get_config

load_dotenv()

# Load configuration from Azure Key Vault
config = get_config()
openai_config = config.get_openai_config()

voice_bot = VoiceBot(openai_config)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.function_name(name="VoiceBot")
@app.route(route="req")
async def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        form_data = req_body.get('formData')
        sessionID = req_body.get('sessionID')
        callreportID = req_body.get("callreportID")
        value = req_body.get('value')
        language = req_body.get("language")
        print("Language: ", language)
        # form_type = req_body.get("typeForm")
        try:
            response = await voice_bot.process_user_message(language, form_data, sessionID, callreportID, value)
            # test = {"tets": 123, "test": 23}
        except Exception:
            print("Encountered an exception")
            print(traceback.format_exc())
            response = await voice_bot.form_error_resonse(sessionID, language)
        return func.HttpResponse(json.dumps(response), mimetype="application/json")

    except Exception:
        print("Invalid input")
        print(traceback.format_exc())
        return func.HttpResponse(
            "Invalid Input",
            status_code=400
        )
    
    
# if __name__ == "__main__":
#     req = {
#         "type": "record",
#         "language": "en-US",
#         "callreportID": "guid",
#         "value": "/135135...." 
#     }
#     res = main(req)