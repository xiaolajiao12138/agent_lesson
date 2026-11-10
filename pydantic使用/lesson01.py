import os
from enum import StrEnum
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field, SecretStr,model_validator,ValidationError,field_validator

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
    CRITICAL = "CRITICAL"

class Agent_task(BaseModel):
    task_id: str = Field(
        ...,
        description="任务id",
    )
    titletype: PriorityLevel = Field(default=PriorityLevel.medium, description="任务类型")
    title: str = Field(..., max_length=8, min_length=1, description="任务标题")
    timeout_seconds:int = Field(
        default=30,
        ge=5,
        le=300,
        description="任务最大等待执行时间必须介于5-300之间"
    )
    @field_validator("title")##用户输入或大模型的逻辑可能带入空格，所以先用strip()去掉前后空格，如果不符合或要求就报错输出不合要求者
    @classmethod
    def validator_title_content(cls,v:str) ->str: 
        striptitle = v.strip()##防止大模型或者用户输入了一大堆空格
        if not striptitle:
            raise ValueError("任务标题不能为空")
        return striptitle
    # data = {"task_id": "123321", "type": "LOW", "title": "测试"}

    @model_validator(mode="after")
    def validate_cors_field_rules(self):
        if self.titletype.value == PriorityLevel.CRITICAL and self.timeout_seconds > 60:
            raise ValueError("多字段联动违规，防止系统卡死，超时时间绝对不能超过60秒")
        #规则要求，验证完成后必须把self要return 出去
        return self
# structmodel = llm_ChatOpenAI.with_structured_output(Agent_task)
# result = structmodel.invoke('这是一个标题')
# print(result)
# print(f"类型：{result.titletype}")

def demonstrate_pydantic_for_agents():
    data = {"task_id": "123123", "titletype": "CRITICAL", "title": "测","timeout_seconds":70}
    task = Agent_task(**data)
    print(task.title)


if __name__ == "__main__":
    demonstrate_pydantic_for_agents()
