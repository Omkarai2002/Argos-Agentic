from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from typing import Dict
from app.config import OPENAI_API_KEY, TEMPERATURE_FOR_JSON_EXTRACTION, JSON_EXTRACTION_PROMPT
from mission_classifier_layer.model_selection import Selection
from jsons import (TEMPLATE)
from validation_layer.json_cleanup import EnterDataToJSON
from dataclasses import dataclass
# data ={
#         "user_id":1,
#         "site_id":1,
#         "org_id":1,
#         "prompt" :"Fly to Pathardi Phata at 30 meters, tilt camera down 45 degrees, start video recording, hover for 10 seconds and land."
#     }
# validated={
#         "db_record_id":int,
#         "user_id":data["user_id"],
#         "site_id":data["site_id"],
#         "org_id":data["org_id"],
#         "prompt":data["prompt"],
#         "class":"",
#         "reason":"",
#         "model_for_extraction":"",
#         "model_for_extraction_json_output": Dict
#     }
# validate=Selection(validated,data)
# validated=validate.select_model()
output_from_json=EnterDataToJSON()
@dataclass
class PromptToJsonConvert:

    validated: dict

    def __post_init__(self):

        self.llm = ChatOpenAI(
            model=self.validated["model_for_extraction"],
            temperature=TEMPERATURE_FOR_JSON_EXTRACTION,
            api_key=OPENAI_API_KEY,
            model_kwargs={
                "reasoning":{
                    "effort":"low"
                }
            }
        )

        self.parser = JsonOutputParser()

    def convert(self) -> Dict:

        messages = [
            SystemMessage(content=JSON_EXTRACTION_PROMPT),
            HumanMessage(content=self.validated["prompt"])
        ]

        result = self.llm.invoke(messages)
        chain = self.parser.invoke(result)

        extracted_json = TEMPLATE

        self.validated["model_for_extraction_json_output"] = \
            output_from_json.parse_json(chain, extracted_json)

        return self.validated


# mission_json = PromptToJsonConvert.convert(
#     validated["prompt"]
# )

# print(mission_json)
# mission_json=PromptToJsonConvert(validated)
# print(mission_json.convert())