import os
from enum import StrEnum
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field, SecretStr

load_dotenv(override=True)

api_key = os.getenv("api_key", "")
base_url = os.getenv("base_url")
mode = os.getenv("mode", "gpt-6.1-sol")

llm_ChatOpenAI = init_chat_model(
    model=mode, api_key=SecretStr(api_key), base_url=base_url
)


class PriorityLevel(StrEnum):
    low = "LOW"
    medium = "MEDIUM"


class Agent_task(BaseModel):
    task_id: str = Field(
        ...,
        description="任务id",
    )
    titletype: PriorityLevel = Field(default=PriorityLevel.medium, description="任务类型")
    title: str = Field(..., max_length=8, min_length=1, description="任务标题")

    # data = {"task_id": "123321", "type": "LOW", "title": "测试"}

structmodel = llm_ChatOpenAI.with_structured_output(Agent_task)
result = structmodel.invoke('这是一个标题')
print(result)
print(f"类型：{result.titletype}")

# def demonstrate_pydantic_for_agents():
#     data = {"task_id": "123321", "type": "LOW", "title": "测试"}
#     task = Agent_task(**data)
#     print(task.title)


# if __name__ == "__main__":
# demonstrate_pydantic_for_agents()
