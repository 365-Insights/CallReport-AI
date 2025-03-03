import requests
import json
import time
import os
import azure.cognitiveservices.speech as speechsdk


region = os.environ.get('speech_service_region')
subscription_key = os.environ.get('speech_service_key')
endpoint_fast = f"https://{region}.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe?api-version=2024-11-15"

def fast_speach_recog(audio_file_path: str, locale = "en-US"):
    definition = {
        "locales": [locale],
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