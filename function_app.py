import os
import logging
import asyncio
import json
import traceback
import azure.cognitiveservices.speech as speechsdk
import azure.functions as func
from dotenv import load_dotenv


from services import *

load_dotenv()


openai_config = {
    "ENDPOINT": os.environ.get("openai_endpoint"),
    "API_KEY": os.environ.get("openai_key"),
    "MODEL": os.environ.get("llm_model"),
    "API_VERSION": os.environ.get("openai_api_version")
}

voice_bot = VoiceBot(openai_config)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.function_name(name="VoiceBot")
@app.route(route="req")
async def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        req_type = req_body.get('type')
        sessionID = req_body.get('sessionID')
        callreportID = req_body.get("callreportID")
        value = req_body.get('value')
        language = req_body.get("language")
        response = await voice_bot.process_user_message(language, req_type, sessionID, callreportID, value)
        # test = {"tets": 123, "test": 23}
        return func.HttpResponse(json.dumps(response), mimetype="application/json")

    except Exception:
        print("Encountered an exception")
        print(traceback.format_exc())
        return func.HttpResponse(
            "Processing Error",
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