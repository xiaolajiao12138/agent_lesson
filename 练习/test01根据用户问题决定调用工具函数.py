import json
import os
from pydantic import BaseModel, Field
from typing import Any
import sys
from pathlib import Path
super_path= Path(__file__).resolve().parent.parent
sys.path.append(str(super_path))
from phase04_rag_system.day09_vector_rag import SimpleVectorRAG

OPENAI_API_KEY = (
    os.getenv("api_key")
    or os.getenv("OPENAI_API_KEY")
    or "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345"
)
OPENAI_BASE_URL = (
    os.getenv("base_url")
    or os.getenv("OPENAI_BASE_URL")
    or "https://sub2api.starysp.top/v1"
)
DEFAULT_MODEL = os.getenv("mode") or "gpt-6.1-sol"
rag_system = SimpleVectorRAG()
class PolicyArgs(BaseModel):
    query:str = Field(description="企业制度相关的问题或关键词，如出差住宿标准")
    top_k:int = Field(description="召回切片数",default=2)
class WeatherArgs(BaseModel):
    query:str=Field(description="需要查询天气的城市，比如”北京“，”深圳“")
class CalculateArgs(BaseModel):
    expression:str = Field(
        description="合法的算术运算表达式"
    )
#从企业向量知识库中语义检索制度规范
def search_compony_tool(query:str,top_k:int=2)->str:
    try:
        print(query)
        chunks = rag_system.semantic_search(query,top_k=top_k)
        if not chunks:
            return "企业知识库中未检索到任何相关条款"
        return 
    except Exception as e:
        print(e)
def get_weather_tool(query:str,tpo_k:int = 2)->str:
    try:
        print(query)
    except Exception as e:
        print(e)

def calculate_tool(query:str,top_k:int=2)->str:
    try:
        print(query)
    except Exception as e:
        print(e)

#将三个工具的说明书打包成一个列表，给大模型看
ALL_TOOLS = [
    {
        "type":"function",
        "function":{
            "name":"search_company",
            "description":"专用于检索公司内部人事请假，加班调休，差旅报销以及技术开发安全合规等官方制度规定",
            "parameters":PolicyArgs.model_json_schema()
        }
    },
    {
        "type":"function",
        "function":{
            "name":"get_weather",
            "description":"获取指定城市的实时天气预报，当前气温和风向信息",
            "parameters":WeatherArgs.model_json_schema()
        }
    },
    {
        "type":"function",
        "function":{
            "name":"calculate",
            "description":"进行加减乘除，乘方等精确的数学运算",
            "parameters":CalculateArgs.model_json_schema()
        }
    },
]
#  将工具名称字符串映射到真实python函数的查找表
TOOL_REGISTRY:dict[str,Any] = {
    "search_company":search_compony_tool,
    "get_weather":get_weather_tool,
    "calculate":calculate_tool
}




def getanswer(q1:str,max_retries:int=2)->str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    message = [
        {
            "role":"system",
            "content":(
                "你是一个功能很强大的企业多功能助理"
            )
        },
        {
            "role":"user",
            "content":q1
        }
    ]
    msg = None
    for attempt in range(1,max_retries+1): #带三个工具说明书请求大模型（带网络重试保护）
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=message,
                tools=ALL_TOOLS,
                tool_choice="auto",       
            )
            msg = response.choices[0].message
            break
        except Exception as e:
            if attempt == max_retries:
                return f"网络请求遇到波动，重试失败：{e}"
                import time
                time.sleep(1)
            print(e)
    if msg.tool_calls:  #如果大模型返回了要调用工具
        print(msg)


if __name__ == "__main__":
    question = [
        "你好，请问你是谁？今天感觉怎么样？",  # 场景 1：闲聊（不调工具）
        "我下周去深圳出差，请问一线城市的住宿报销标准是多少？",  # 场景 2：触发制度库 (search_company_policy)
        "深圳今天天气怎么样？穿短袖会冷吗？",  # 场景 3：触发天气查询 (get_weather)
        "如果我出差 3 天，每天房费 480 元，总房费是多少钱？",  # 场景 4：触发计算器 (calculate)
    ]
    for i in question: #循环问题调用函数
        try:
            answer = getanswer(i)
            print(answer)
        except Exception as e:
            print(e)