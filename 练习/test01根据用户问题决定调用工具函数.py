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
    city:str=Field(description="需要查询天气的城市，比如”北京“，”深圳“")
class CalculateArgs(BaseModel):
    expression:str = Field(
        description="合法的算术运算表达式"
    )
#从企业向量知识库中语义检索制度规范
def search_compony_tool(query:str,top_k:int=2)->str:
    print(query)
    chunks = rag_system.semantic_search(query,top_k=top_k)
    if not chunks:
        return "企业知识库中未检索到任何相关条款"
    return "\n\n".join(
        [
            f"【切片ID:{c['id']} | 分类：{c["category"]}】\n{c['content']} "
            for c in chunks
        ]
    )
  
def get_weather_tool(city:str)->str:
    mock_data = {
        "北京":{"temp":"12℃","condition":"晴朗少云","wind":"西北风3级"},
        "上海":{"temp":"5℃","condition":"阴天下雨","wind":"东南风5级"},
        "深圳":{"temp":"20℃","condition":"晴朗","wind":"北风6级"}
    }
    info = mock_data.get(
        city,{"temp":"18℃","condition":"下雨","wind":"北风6级"}
    )
    return json.dumps({"city":city,**info},ensure_ascii=False)
def calculate_tool(expression:str)->str:
    try:
        res = eval(expression,{"__builtins__":None},{}) #在安全受命名空间下执行算数计算
        return json.dumps({"expression":expression,"resutlt":res},ensure_ascii=False)
    except Exception as e:
        return json.dumps({"errore":f"计算失败：{e!s}"},ensure_ascii=False)

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
        for tool_call in msg.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            if function_name in TOOL_REGISTRY:
                target_function = TOOL_REGISTRY[function_name]
                observation = target_function(**function_args)
                message.append(msg.model_dump(exclude_none=True))
                message.append(
                    {
                        "role":"tool",
                        "tool_call_id":tool_call.id,
                        "content":str(observation)
                    }
                )
    try:
        final_res = client.chat.completions.create(
            model=DEFAULT_MODEL,temperature=0.0,messages=message
        )
        return final_res.choices[0].message.content
    except Exception as e:
            return f"获取最终总结答案异常{e}"
    #如果模型没有调用工具，判定未普通回答
    return msg.content

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