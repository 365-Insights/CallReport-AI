import os  
import logging  
import json  
from fastapi import FastAPI, HTTPException, Request  
from dotenv import load_dotenv  
from pydantic import BaseModel  
from utils import *
from services import VoiceBot  # Assuming `VoiceBot` is defined in `services.py`  
  
# Load environment variables  
load_dotenv()  
  
# Configuration for OpenAI  
openai_config = {  
    "ENDPOINT": os.environ.get("openai_endpoint"),  
    "API_KEY": os.environ.get("openai_key"),  
    "MODEL": os.environ.get("llm_model"),  
    "API_VERSION": os.environ.get("openai_api_version"),  
}  
  
# Initialize the VoiceBot instance  
voice_bot = VoiceBot(openai_config)  
  
# Create a FastAPI app instance  
app = FastAPI()  
  
# Log initialization  
logging.info("INITIALISED SUCCESSFULLY")  
  
  
# Define a Pydantic model for request validation  
class RequestPayload(BaseModel):  
    type: str  
    language: str  
    sessionID: str  
    callreportID: str
    value: str  
  
  
@app.post("/api/req")  
async def process_request(payload: RequestPayload):  
    """  
    Handle POST requests to process user messages.  
    """  
    print(payload)
    try:  
        # Extract data from the request payload  
        req_type = payload.type  
        sessionID = payload.sessionID  
        callreportID = payload.callreportID
        value = payload.value  
        language = payload.language  
        # print("VALUE", value)
        # new_path = convert_base64_webm_to_wav(value, "test.wav")
        # print(new_path)
        # Process the user message using VoiceBot  
        response = await voice_bot.process_user_message(language, req_type, sessionID, callreportID, value)  
  
        # Example test response (can be replaced with the actual response)  
  
        # Return the processed response as JSON  
        return {"response": response}  
    except ValueError as e:  
        # Handle invalid input or errors  
        logging.error(f"Error processing request: {e}")  
        raise HTTPException(status_code=400, detail="Invalid input")  
  
  
# For debugging or testing purposes  
if __name__ == "__main__":  
    import uvicorn  
    uvicorn.run(app, host="localhost", port=8000)  
    # uvicorn.run(app, host="0.0.0.0", port=8000)  