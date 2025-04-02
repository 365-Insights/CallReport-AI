import os
import asyncio


from dotenv import load_dotenv
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
    ResourceNotFoundError,
    AzureError
)
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import MessageRole, BingGroundingTool
from azure.identity import DefaultAzureCredential




class SearchAgent:
    def __init__(self):
        self.project_client = AIProjectClient.from_connection_string(
            credential=DefaultAzureCredential(),
            conn_str=os.environ["PROJECT_CONNECTION_STRING"],
        )
        self._initialize_agent()
    
    def _initialize_agent(self):
        self.agent_id = os.environ.get("ai_agent_id")
        print(self.agent_id)
        # if self.agent_id:
        #     try:
        #         self.agent = self.project_client.agents.get_agent(self.agent_id)
        #     except ResourceNotFoundError:
        #         print(f"Failed to get the agent by id: {self.agent_id}")
        #         self.agent_id = self._create_agent()
        # else:
        #     self.agent_id = self._create_agent()
        

    def _create_agent(self):
        print("Creating search agent")
        bing_connection = self.project_client.connections.get(connection_name=os.environ["BING_CONNECTION_NAME"])
        conn_id = bing_connection.id
        print(conn_id)  
        bing = BingGroundingTool(connection_id=conn_id)
        self.agent = self.project_client.agents.create_agent(
            model=os.environ.get("search_agent_llm"),
            name="search-agent-python",
            instructions="You are a helpful assistant",
            tools=bing.definitions,
            headers={"x-ms-enable-preview": "true"},
        )
        return self.agent.id
    

    async def _generate_answer(self, prompt: str):

        # Create thread for communication
        thread = await self.project_client.agents.create_thread()
        print(f"Created thread, ID: {thread.id}")

        # Create message to thread
        message = await self.project_client.agents.create_message(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=prompt,
        )
        print(f"Created message, ID: {message.id}")

        # Create and process agent run in thread with tools
        run = await self.project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=self.agent_id)
        print(f"Run finished with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            raise Exception
        messages = await self.project_client.agents.list_messages(thread_id=thread.id)
        # print(messages)
        response_message = messages.get_last_message_by_role(
            MessageRole.AGENT
        )
        if response_message:
            return " ".join([i.text.value for i in response_message.text_messages])


    async def get_person_info(self, full_name: str, company: str, country: str = None):  
        from_country = f"from {country} " if country else ""  
        prompt = (  
            f"""Find detailed professional information about {full_name} {from_country}who works at {company}. Use LinkedIn as the primary source. Include job title, department, and professional background. If possible, obtain contact details and a profile link.  
            If LinkedIn does not provide information, check industry publications or company websites. If no relevant information can be found, return just 'None' nothing else.
            If you find then provide summery about the person, his email, phone, location, position, job title, industry where he works, education level. The more info the better."""  
        )  
        res = await self._generate_answer(prompt)  
    
        # Retry logic if res is 'None'  
        if res == 'None':  
            print("Retry finding persons information")
            # Alter the prompt slightly: perhaps broaden the search or change phrases.  
            prompt_retry = (  
                f"""Attempt to find any publicly available information about {full_name} who works at {company}associated with {company} using alternative professional networks or news articles. Focus on identifying their role and contributions to the company.  
                Information that you should include:
                - Position, department, some work info
                - Location, city, country
                - Standart information about the person that could be useful like summery about and etc.
                If no information is still found, confirm 'None'."""  
            )  
            res = await self._generate_answer(prompt_retry)  
        return res  

    async def get_company_info(self, company_name: str):
        prompt = f"""  
Gather detailed information about the company named {company_name}. Use the official company website (including the imprint) and LinkedIn as the primary sources. The required details include:  
  
1. Full Company Address:  
   - Street name and number  
   - Postal code  
   - City and country  
  
2. Contact Information:  
   - Phone number  
   - Email address (found on the imprint on the official website)  
  
3. Industry:  
   - Industry type or sector  
  
4. Official Website URL:  
   - Link to the official website  
  
5. General Information:  
   - A brief summary or overview of the company, including its mission, vision, and key services/products  
  
Find as much info as possible that could be useful."""  
  
# res = await self._generate_answer(prompt)  
# return res      
        res = await self._generate_answer(prompt)
        return res
    
if __name__ == "__main__":
    load_dotenv()
    aiagent = SearchAgent()
    name = "Oleksandr Diakon"
    company = "Infopulse"
    # res = asyncio.run(aiagent.get_person_info(name, company))
    res = asyncio.run(aiagent.get_company_info(company))
    print("result: ", res)