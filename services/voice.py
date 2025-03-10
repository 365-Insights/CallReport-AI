import requests
import json
import time
import os
import base64
import asyncio
from dotenv import load_dotenv

import azure.cognitiveservices.speech as speechsdk

load_dotenv()

region = os.environ.get('speech_service_region')
subscription_key = os.environ.get('speech_service_key')
endpoint_fast = f"https://{region}.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe?api-version=2024-11-15"

def fast_speech_recog(audio_file_path: str, lang = "en-US"):
    definition = {
        "locales": [lang],
        "profanityFilterMode": "Masked",
        "channels": [0, 1]
    }

    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Accept": "application/json"
    }

    with open(audio_file_path, "rb") as audio_file:
        files = {
            "audio": ("podcastwave.wav", audio_file, "audio/wav"),
            "definition": (None, json.dumps(definition), "application/json")
        }

        start_time = time.time()
        response = requests.post(endpoint_fast, headers=headers, files=files)

        if response.status_code == 200:
            result = response.json()
            print("Response: ")
            transcript_data = result.get('combinedPhrases', [{}])[0].get('text', '')
            print(transcript_data)
            elapsed_seconds = time.time() - start_time
            print(f"Transcription took {elapsed_seconds:.4f} seconds")
            return transcript_data
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return 
            # return response.text



def speech_recog(file_name: str, locale = "en-US"):
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
    speech_config.speech_recognition_language = "en-US"

    audio_config = speechsdk.AudioConfig(filename=file_name)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    def recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("Recognized: {}".format(evt.result.text))
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(evt.result.no_match_details))

    def canceled(evt):
        print("Speech Recognition canceled: {}".format(evt.result.reason))
        if evt.result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = evt.result.cancellation_details
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")

    speech_recognizer.recognized.connect(recognized)
    speech_recognizer.canceled.connect(canceled)

    speech_recognizer.start_continuous_recognition()
    print("Listening... Press Enter to stop.")
    input()
    speech_recognizer.stop_continuous_recognition()


def text2speech(text: str, lang_voice: str = 'en-US-AvaMultilingualNeural'):
    print(subscription_key, region)
    text = text.replace("\n", "")
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
    audio_config = speechsdk.audio.PullAudioOutputStream()

    # The neural multilingual voice can speak different languages based on the input text.
    speech_config.speech_synthesis_voice_name = lang_voice

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    # Synthesize the text to an audio stream
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))
        audio_data = speech_synthesis_result.audio_data
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        return audio_base64
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")
        return None
    
# Example usage
def main():
    text = "Hello, test. "
    audio_base64 = text2speech(text)
    with open("output.webm", 'wb') as file:
        file.write(base64.b64decode(audio_base64))
    # print(audio_base64)

# Run the example
if __name__ == "__main__":
    main()