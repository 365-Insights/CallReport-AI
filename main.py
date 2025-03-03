import os
import logging
import asyncio

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

openai_client = OpenAiClient(openai_config)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)



async def extract_info(audio_path):
    text = fast_speach_recog(audio_path, "de-DE")
    res_info = await extract_info_from_text(text, openai_client)
    print("RES: ", res_info)
    return res_info


@app.route(route="voice")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    text = extract_info("voice.wav")
    
    return func.HttpResponse("This http triggered function executed successfully.  You didn't pass the correct name though, try again.", status_code=200)


if __name__ == "__main__":
    asyncio.run(extract_info("voice.wav"))