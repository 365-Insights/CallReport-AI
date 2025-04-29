from enum import Enum
from .voice import text2speech
from utils import lang2voice


class CommandType(Enum):  
    PLAY_BOT_VOICE = "playBotVoice"  
    CREATE_CONTACT = "createContacts"  
    CREATE_REPORT = "createCallReport"
    UPDATE_CONTACT = "updateCurrentContact"  
    FILL_INTERESTS = "fillInterests"  
    FILL_IN_SUMMARY = "fillInSummary"  
    ADD_FOLLOW_UPS = "addFollowUps"  
    SAVE = "saveCurrentDocument"
    CANCEL = "Cancel"




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
    voice_play = gen_general_command(CommandType.PLAY_BOT_VOICE, val, "record", order)
    return voice_play

def validate_commands(commands: list):
    to_remove = []
    for i, comand in enumerate(commands):
        empty = False
        if comand["name"] not in (CommandType.SAVE, CommandType.CANCEL):
            if not comand["parameters"] or not comand["parameters"]['value']:
                to_remove.append(comand)   
                continue
        else:
            continue
        val = comand["parameters"]["value"]
        if comand["name"] == CommandType.ADD_FOLLOW_UPS:
            for follow_up in val:
                if not all((follow_up["type"], follow_up["notes"])):
                    print("Remove empty follow up")
                    val.remove(follow_up)
            if not val:
                to_remove.append(comand)   
            else:
                commands[i]["parameters"]["value"] = val
            
    for i in to_remove:
        print("Remove command because it is empty: ", i)
        commands.remove(i)
    return commands