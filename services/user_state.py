from enum import Enum
from dataclasses import dataclass
from dataclasses import dataclass, field  

  
@dataclass  
class UserData:  
    session_id: str  
    state: str  
    history_data: dict  
    _last_message: str = None  
    _last_answer: str = None  
    language: str = "de-DE"  
    chat_history: list = field(default_factory=list)  
    max_history_length: int = 15  # Maximum length of the chat history  
  
    @property  
    def last_message(self):  
        """  
        Returns the last_message if set, or the most recent user_msg from chat_history if available.  
        """  
        if self._last_message is not None:  
            return self._last_message  
        elif self.chat_history:  
            return self.chat_history[-1]["user_msg"]  
        return None  # Return None if neither last_message nor chat_history is available  
  
    @last_message.setter  
    def last_message(self, value):  
        self._last_message = value  
        self._try_update_chat_history()  
  
    @property  
    def last_answer(self):  
        """  
        Returns the last_answer if set, or the most recent bot_answer from chat_history if available.  
        """  
        if self._last_answer is not None:  
            return self._last_answer  
        elif self.chat_history:  
            return self.chat_history[-1]["bot_answer"]  
        return None  # Return None if neither last_answer nor chat_history is available  
  
    @last_answer.setter  
    def last_answer(self, value):  
        self._last_answer = value  
        self._try_update_chat_history()  
  
    def _try_update_chat_history(self):  
        """  
        Updates the chat history only if both last_message and last_answer are set.  
        Enforces the maximum length of chat history.  
        """  
        # Only add to chat history if both last_message and last_answer are set  
        if self._last_message is not None and self._last_answer is not None:  
            self.chat_history.append({  
                "user_msg": self._last_message,  
                "bot_answer": self._last_answer  
            })  
  
            # Enforce the maximum length of the chat history  
            if len(self.chat_history) > self.max_history_length:  
                self.chat_history = self.chat_history[-self.max_history_length:]  # Keep only the last `max_history_length` items  
  
            # Clear the last_message and last_answer to prevent duplicate entries  
            self._last_message = None  
            self._last_answer = None  



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

    