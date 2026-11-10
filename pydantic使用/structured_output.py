from fastapi.responses import StreamingResponse
from langsmith import Stream
import time
from dotenv import load_dotenv
import os
import sys
from pydantic import BaseModel,Field
from openai import OpenAI
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="任务画像提取服务")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv(override=True)
api_key = os.getenv("api_key","")
base_url = os.getenv("base_url","")
DEFAULT_MODEL = os.getenv("mode","")

def get_gpt_client():
    return OpenAI(
        api_key=api_key,
        base_url= base_url,
    )

class UserProfileExtract(BaseModel):
    user_name:str = Field(description="用户名")
    current_role:str = Field(description="当前岗位角色，如前端开发")
    skills:List[str] = Field(description="用户掌握的专业技能")
    years:int = Field(description="工作年限")
    is_konw_Ai:bool = Field(description="是否对AI了解")

def extract_structured_data(bio)->UserProfileExtract:
    client = get_gpt_client()
    with client.chat.completions.stream(
        model = DEFAULT_MODEL,#大模型版本
        messages=[
            {
                "role":"system",
                "content":"你是一个极其严格的信息抽取助手。请仔细阅读用户提供的个人自述，提取出规范的人物画像。"
            },
            {
                "role":"user",
                "content":bio
            }
        ],
        response_format = UserProfileExtract,
    ) as stream:
        for event in stream:
            if event.type == "content.delta":
                yield event.delta
        print()
        completion = stream.get_final_completion()
        parsed_result = completion.choices[0].message.parsed
    # print(f"{completion.model_dump_json(indent=2,warnings=False)}")
    # parsed_result = completion.choices[0].message.parsed
    return parsed_result

@app.get("/api/title",response_model=UserProfileExtract)
def api_title():
    mock_bio=(
          "大家好！我叫小陈，目前在一家外企做前端开发，主要技术栈是 React、TypeScript 和 Next.js，"
        "不知不觉在这个领域已经搬砖整整 4 年了。最近大模型特别火，我目前正在全力自学 Agent 开发和 LangGraph，"
        "希望今年内能转型成为一名优秀的 AI 智能体全栈工程师！"
    )
    return StreamingResponse(extract_structured_data(mock_bio),media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app,host="127.0.0.1",port=8000)  
    # try:
    #     start_time = time.time()
    #     data = extract_structured_data(mock_bio)
    #     payload_time = time.time()-start_time
    #     print(f"0000000000000000")
    #     print(f"{payload_time}")
    #     print(f"-----------------")
    #     print(f"{data}")
    # except Exception as err:
    #     print(err)