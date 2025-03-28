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
        prompt = f"""Find information about {full_name} {from_country}that works at {company}. Try using linkedin as main source of data.
        If you don't have any relevant information about {full_name} just return - 'None'"""
        res = await self._generate_answer(prompt)
        return res

    async def get_company_info(self, company_name: str):
        prompt = f"""Find information about company with the name{company_name}. Try using likedin or company website as main sources of data.
        If you don't have any relevant information about {company_name} just return - 'None'"""
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