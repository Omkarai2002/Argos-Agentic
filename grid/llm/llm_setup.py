from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
# in llm_setup.py
from grid.services.schema import MissionResponse

load_dotenv()


class LLMSetup:

    def __init__(self, system_prompt: str = ""):
        self.llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0
        )
        self.structured_llm = self.llm.with_structured_output(MissionResponse)
        self.system_prompt = system_prompt

    def generate(self, user_prompt: str) -> MissionResponse:

        messages = []

        if self.system_prompt:
            messages.append(("system", self.system_prompt))

        messages.append(("human", user_prompt))

        response = self.structured_llm.invoke(messages)

        return response