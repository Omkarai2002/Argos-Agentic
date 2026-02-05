from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.config import (OPENAI_API_KEY,
WORK_PATTERN_PROMPT,MODEL_FOR_CLASSIFICATION,
TEMPERATURE_FOR_CLASSIFICATION)
from typing import Dict,Any

# data ={
#         "user_id":1,
#         "site_id":1,
#         "org_id":1,
#         "prompt" :"Plan a grid-based area coverage mission over a 500 m × 400 m agricultural field near the dock with 70% front overlap and 60% side overlap at 60 m altitude for multispectral mapping."
#     }
# validated={
#         "db_record_id":int,
#         "user_id":data["user_id"],
#         "site_id":data["site_id"],
#         "org_id":data["org_id"],
#         "prompt":data["prompt"],
#         "class":"",
#         "reason":""
#     }
@dataclass
class Classifier:
    validated:dict
    
    def test(self):
        return validated

    def build_work_pattern_chain(self):
        llm=ChatOpenAI(
            model=MODEL_FOR_CLASSIFICATION,
            temperature=TEMPERATURE_FOR_CLASSIFICATION,
            api_key=OPENAI_API_KEY
        )
        prompt=ChatPromptTemplate.from_template(WORK_PATTERN_PROMPT)
        parser=JsonOutputParser()
        chain =prompt| llm | parser
        return chain
    
    def doctrine_classifier(self,work_pattern:str,mission_text:str)->str:
        text=mission_text.lower()
        if work_pattern =="cover_area":
            return "grid"
        if work_pattern =="move_and_work":
            return "path"
        if work_pattern =="inspect_structure":
            return "3d"
        if work_pattern =="stop_and_work":
            structural_terms =[
                "tower","turbine","facade","building",
                "wind turbine","cell tower","telecom tower"
            ]
            if any (term in text for term in structural_terms):
                return "3d"
            return "point"
        return "point"
    
    def classify_mission(self) -> dict:
        mission_text=self.validated["prompt"]
        chain = self.build_work_pattern_chain()

        # Step 1: LLM → work pattern
        llm_result = chain.invoke({
            "mission_text": mission_text
        })

        work_pattern = llm_result["work_pattern"]
        reason = llm_result["reason"]
        complexity=llm_result["complexity"]

        # Step 2: Rules → doctrine
        mission_type = self.doctrine_classifier(work_pattern, mission_text)

        return {
            "mission_type": mission_type,          # point / path / grid / 3d
            "work_pattern": work_pattern,          # LLM output
            "reason": reason, 
            "complexity":complexity                    # LLM explanation
        }

class FillJson(Classifier):
    def append_data_to_json(self):
        mission_data=self.classify_mission()
        self.validated["class"]=mission_data["mission_type"]
        self.validated["reason"]=mission_data["reason"]
        self.validated["complexity"]=mission_data["complexity"]
        return self.validated

# c=FillJson(validated)
# print(c.append_data_to_json())
