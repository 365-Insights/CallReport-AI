from enum import Enum
from dataclasses import dataclass

@dataclass
class UserData:
    session_id: str
    state: str
    history_data: dict
    last_message: str
    last_answer: str = None
    language: str = "en-US"

class Commands(Enum):
    playBotVoice = 0
    createContact = 1
    updateCurrentContact = 2
    fillInterests = 3
    addFollowUpds = 4
    giveListContactFields = 5
    giveListInterests = 6
    saveCurrentDocument = 7
    cancel = 8

    