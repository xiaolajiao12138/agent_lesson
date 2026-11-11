"""企业实战第 6 课｜对运行中的应用执行固定样例，失败时让 CI 得到非零退出码。"""

import argparse
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from support_agent.schemas import KnowledgeAnswer
from support_agent.security import IdentityInput

PROJECT = Path(__file__).resolve().parents[1]


class EvalCase(BaseModel):
    id: str
    user: str
    question: str
    route: Literal["answer", "transfer"]
    source_id: str | None = None
    expected_excerpt: str | None = None


def load_cases() -> list[EvalCase]:
    """反序列化评测集，格式错误时在请求前失败。"""
    return TypeAdapter(list[EvalCase]).validate_json(
        (PROJECT / "evals" / "cases.json").read_text(encoding="utf-8"),
    )


def run_cases(client: httpx.Client, tokens: dict[str, str], cases: list[EvalCase]) -> list[str]:
    """执行 HTTP 评测，返回失败用例的 ID 和原因。客户端由调用方关闭。"""
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
        citation = answer.citation
        source_id = citation.source_id if citation else None
        excerpt = citation.excerpt if citation else None
        if (answer.route, source_id, excerpt) != (case.route, case.source_id, case.expected_excerpt):
            failures.append(f"{case.id}: 路由、来源或引用正文与预期不同")
        elif case.route == "answer" and answer.message != case.expected_excerpt:
            failures.append(f"{case.id}: 回答正文与当前摘录基线不同")
    return failures


def main() -> int:
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
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
