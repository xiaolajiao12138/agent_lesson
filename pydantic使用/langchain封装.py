from enum import StrEnum
from turtle import title
from unittest import result
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field, SecretStr,model_validator,ValidationError,field_validator
import os
load_dotenv(override=True)

api_key = os.getenv("api_key", "")
base_url = os.getenv("base_url")
mode = os.getenv("mode", "gpt-6.1-sol")

llm_ChatOpenAI = init_chat_model(
    model=mode, api_key=SecretStr(api_key), base_url=base_url
)

class Person(BaseModel):
    name:str = Field(description="姓名")
    age:str = Field(description="年龄")
    Occupation:str = Field(description="职业")
structured_model = llm_ChatOpenAI.with_structured_output(Person)
result = structured_model.invoke("张三是一名30岁的软件工程师")
print(result)
print(type(result))

class MoiveModel(BaseModel):
    title:str = Field(description="电影标题")
    year:int = Field(description="发行年份")
    director:str = Field(description="导演")
    rating:float = Field(description="电影评分，满分十分")
structured_model = llm_ChatOpenAI.with_structured_output(MoiveModel)
print(structured_model)
result = structured_model.invoke("给出电影盗梦空间的信息") 
print(result)