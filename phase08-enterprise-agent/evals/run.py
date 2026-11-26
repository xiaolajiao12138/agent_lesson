"""企业实战第 6 课｜固定样例回归评测，可在 CI 或命令行中运行。

阅读顺序为 EvalCase -> load_cases() -> run_cases() -> main()。
在项目目录执行 python -m evals.run，默认访问 http://127.0.0.1:8000。
cases.json 每条数据描述问题、教学用户、预期路由、文档编号和摘录正文。
run_cases() 可复用 TestClient 或真实 HTTP 客户端，main() 负责解析命令行与形成退出码。
"""

import argparse
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from support_agent.schemas import KnowledgeAnswer
from support_agent.security import IdentityInput

# 当前文件在 evals/ 下，向上两级得到项目目录，用于定位 cases.json 和教学身份文件。
PROJECT = Path(__file__).resolve().parents[1]


class EvalCase(BaseModel):
    """一条评测数据的契约，由 TypeAdapter 一次性校验整个列表。

    id 用于定位失败用例，user 对应凭证表中的 user_id。
    route 是 answer/transfer 的期望结果，source_id 和 expected_excerpt 默认 None。
    列表结构或字段格式有误时，加载阶段就会失败，便于先修正评测数据。
    """
    id: str
    user: str
    question: str
    route: Literal["answer", "transfer"]
    source_id: str | None = None
    expected_excerpt: str | None = None


def load_cases() -> list[EvalCase]:
    """读取固定 JSON 评测集，返回 list[EvalCase]。

    Path.read_text() 得到文件文本，validate_json() 完成 JSON 解析及列表元素校验。
    json.loads() 主要负责反序列化，TypeAdapter 进一步应用 Pydantic 类型约束。
    路径基于本文件定位，因此评测数据读取不依赖调用命令时的当前目录。
    """
    return TypeAdapter(list[EvalCase]).validate_json(
        (PROJECT / "evals" / "cases.json").read_text(encoding="utf-8"),
    )


def run_cases(client: httpx.Client, tokens: dict[str, str], cases: list[EvalCase]) -> list[str]:
    """逐条发送问答请求，对照当前摘录基线，返回失败用例及原因列表。

    client.post(json=..., headers=...) 创建请求体和 Bearer 请求头。
    raise_for_status() 会将 HTTP 失败状态转为 HTTPStatusError，网络故障属于 RequestError。
    KnowledgeAnswer.model_validate_json(response.content) 对响应 JSON 字节执行模型校验。
    response.json() 会得到普通 Python 数据，model_validate(response.json()) 是相关的两步写法。
    失败时 append() 记录原因，continue 继续后续样例，便于一次运行汇总多个问题。
    比较路由、引用来源和原文内容，回答路由还要求正文与基线摘录一致。
    这些断言适用于当前确定性实现，后续生成式回答的质量指标需要相应定义。
    """
    failures = []
    for case in cases:
        try:
            response = client.post("/agent/answer", json={"question": case.question},
                                   headers={"Authorization": f"Bearer {tokens[case.user]}"})
            response.raise_for_status()
            answer = KnowledgeAnswer.model_validate_json(response.content)
        except httpx.HTTPStatusError as error:
            failures.append(f"{case.id}: HTTP {error.response.status_code}")
            continue
        except (httpx.RequestError, ValidationError, KeyError) as error:
            failures.append(f"{case.id}: {type(error).__name__}")
            continue
        # citation 可以为 None，因此在读取 source_id/excerpt 前先做存在性分支。
        citation = answer.citation
        source_id = citation.source_id if citation else None
        excerpt = citation.excerpt if citation else None
        # 三元组逐项比较，一次检查路由、来源标识和引用正文。
        if (answer.route, source_id, excerpt) != (case.route, case.source_id, case.expected_excerpt):
            failures.append(f"{case.id}: 路由、来源或引用正文与预期不同")
        elif case.route == "answer" and answer.message != case.expected_excerpt:
            failures.append(f"{case.id}: 回答正文与当前摘录基线不同")
    return failures


def main() -> int:
    """命令行入口，装配 HTTP 客户端与凭证，打印评测结果并返回退出码。

    ArgumentParser 定义参数，add_argument() 配置名称、默认值和类型，parse_args() 读取实际传参。
    --identities 通过 type=Path 把参数转成 Path，再校验公开教学凭证文件。
    with httpx.Client(...) 复用连接池并在结束时关闭，timeout 限制网络等待。
    trust_env=False 让此本地评测客户端使用显式配置，不读取环境代理等网络设置。
    bool(failures) 在列表非空时为 True，int(True)=1，int(False)=0。
    CI 根据进程退出码判断成功或失败，SystemExit(main()) 会使用该返回值退出。
    """
    parser = argparse.ArgumentParser(description="运行售后知识库评测")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--identities", type=Path, default=PROJECT / "demo-identities.json")
    args = parser.parse_args()
    records = TypeAdapter(list[IdentityInput]).validate_json(args.identities.read_text(encoding="utf-8"))
    cases = load_cases()
    with httpx.Client(base_url=args.base_url, timeout=5.0, trust_env=False) as client:
        failures = run_cases(client, {record.user_id: record.token for record in records}, cases)
    for failure in failures:
        print(f"FAIL {failure}")
    print(f"通过 {len(cases) - len(failures)}/{len(cases)}")
    # [] -> False -> 0；存在失败项 -> True -> 1。这里处理的是列表的真值。
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
