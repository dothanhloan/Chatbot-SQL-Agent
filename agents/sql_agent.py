from langchain_core.prompts import ChatPromptTemplate
from core.prompt import SYSTEM_PROMPT
from core.schema_hrm import HRM_SCHEMA

def build_sql_agent(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT.format(schema=HRM_SCHEMA)),
        ("human", "{question}")
    ])
    return prompt | llm
