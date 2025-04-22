from enum import Enum
from .voice import text2speech
from utils import lang2voice


class CommandType(Enum):  
    PLAY_BOT_VOICE = "playBotVoice"  
    GIVE_LIST_CONTACT_FIELDS = "giveListContactFields"  
    GIVE_LIST_INTERESTS = "giveListInterests"  
    UPDATE_CURRENT_CONTACT = "updateCurrentContact"  
    FILL_INTERESTS = "fillInterests"  
    FILL_IN_SUMMARY = "fillInSummary"  
    ADD_FOLLOW_UPS = "addFollowUps"  


@staticmethod
def gen_general_command(command_name: str, value = {}, val_type: str = dict, order: int = 1):
    command = {
        "name": command_name,
        "order": order,
        "parameters": {}
    }
    if value and val_type:
        command["parameters"]["value"] = value
        command["parameters"]["type"] = val_type
    return command


def generate_audio(text, lang = "en-US"):
    voice = lang2voice.get(lang, "en-US-AvaMultilingualNeural")
    audio_data, duration = text2speech(text, voice)
    return audio_data, duration


    # @staticmethod
def gen_voice_play_command(text: str, order = 1, lang = "en-US"):
    audio_data, duration = generate_audio(text, lang)
    val = {
            "record": audio_data,
            "textMessage": text,
            "duration": duration
            }
    voice_play = gen_general_command("playBotVoice", val, "record", order)
    return voice_play