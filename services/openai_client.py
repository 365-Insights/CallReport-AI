import traceback
from typing import Dict, List
import asyncio

import openai
from openai import AsyncAzureOpenAI
from utils import LOGGER


async def retry_with_backoff(
    func,
    delay: int = 5,
    max_retries: int = 1,
    errors: tuple = (openai.APIConnectionError),
):
    """Retry a function with exponential backoff."""
    def wrapper(*args, **kwargs):
        num_retries = 0
        while True:
            try:
                return func(*args, **kwargs)
            except errors as e:
                num_retries += 1
                if num_retries > max_retries:
                    raise Exception(f"Maximum number of retries reached ({max_retries}) when exceeded Open AI rate limits")
                # LOGGER.debug(f"Caught error while requesting gpt model: {str(e)}")
                # LOGGER.warning(f"Retrying request to gpt model on Azure OpenAI Studio after {delay} sec.", x_flow_id)
                # await asyncio.sleep(delay)
            # Unknown errors - raise exc
            except Exception as e:
                raise e
    return wrapper



class OpenAiClient:
    def __init__(self, config: Dict):
        self.config = config
        self.model = config["MODEL"]
        self._initialize_client()

    def _initialize_client(self):
        self.gen_client = AsyncAzureOpenAI(
            api_key=self.config["API_KEY"],
            api_version=self.config["API_VERSION"],
            azure_endpoint=self.config["ENDPOINT"],
        )
        print(self.config["ENDPOINT"], self.config["API_VERSION"], self.config["API_KEY"])


    async def generate_response(self, messages: List[Dict[str, str]], max_tokens = None) -> str:
        try:
            # print()
            response = await self.gen_client.chat.completions.create(
            model = self.model,
            messages=messages,
            temperature=0.7,
            max_tokens = max_tokens,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0
            )
            return response.choices[0].message.content
        except Exception as e:
            LOGGER.debug(f"Error during call for gpt: {e}\nTraceback:\n{traceback.format_exc()}")
            return None