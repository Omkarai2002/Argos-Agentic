from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from typing import Dict
from app.config import OPENAI_API_KEY, TEMPERATURE_FOR_JSON_EXTRACTION, JSON_EXTRACTION_PROMPT
from mission_classifier_layer.model_selection import Selection

data ={
        "user_id":1,
        "site_id":1,
        "org_id":1,
        "prompt" :"Fly to longitude 72.8777 latitude 19.076 at 30 meters, tilt camera down 45 degrees, start video recording, hover for 10 seconds and land."
    }
validated={
        "db_record_id":int,
        "user_id":data["user_id"],
        "site_id":data["site_id"],
        "org_id":data["org_id"],
        "prompt":data["prompt"],
        "class":"",
        "reason":"",
        "model_for_extraction":"",
        "model_for_extraction_json_output": Dict
    }
validate=Selection(validated,data)
validated=validate.select_model()

class PromptToJsonConvert:

    llm = ChatOpenAI(
        model=validated["model_for_extraction"],
        temperature=TEMPERATURE_FOR_JSON_EXTRACTION,
        api_key=OPENAI_API_KEY
    )

    parser = JsonOutputParser()

    # @staticmethod
    # def filter_json(chain):
    #     if chain["finish_action"]["type"]=="":

    @staticmethod
    def convert(prompt_text: str) -> Dict:

        messages = [
            SystemMessage(content=JSON_EXTRACTION_PROMPT),
            HumanMessage(content=prompt_text)
        ]

        result = PromptToJsonConvert.llm.invoke(messages)
        chain=PromptToJsonConvert.parser.invoke(result)
        validated["model_for_extraction_json_output"]=chain
        return validated

mission_json = PromptToJsonConvert.convert(
    validated["prompt"]
)

print(mission_json)
