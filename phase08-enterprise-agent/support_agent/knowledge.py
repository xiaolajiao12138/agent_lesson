"""企业实战第 5–6 课｜知识库生命周期、权限过滤和可重复评测的检索基线。

写入路径为 DocumentInput -> save_document() -> 数据库 UPSERT。
问答路径为 QuestionInput -> 按身份过滤文档 -> 关键词计分 -> 唯一答案或转人工建议。
当前算法使用原文摘录，便于离线测试；向量检索、重排和大模型生成可作为后续课程扩展。
阅读时重点关注 SQL 条件、JSON 转换、计分分支和 Citation 的来源绑定。
"""

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .db import conflict_insert
from .models import Document
from .schemas import Citation, DocumentInput, KnowledgeAnswer
from .security import Actor


def save_document(session: Session, tenant_id: str, source_id: str, payload: DocumentInput) -> None:
    """在调用方事务内按 (tenant_id, source_id) 新增或覆盖文档。

    payload.model_dump() 将 Pydantic 模型转成字典，**fields 将字典展开为关键字参数。
    keywords 列使用 Text 保存 JSON，因此先用 json.dumps() 把列表序列化成字符串。
    ensure_ascii=False 让中文以原字符保存，默认的 Unicode 转义也可由 json.loads() 正确还原。
    values() 填写待插入字段，excluded 表示本次尝试插入的新值。
    on_conflict_do_update() 依据联合主键判断冲突，set_ 指定冲突时覆盖哪些字段。
    on_conflict_do_nothing() 则会保留旧记录，适合工单幂等创建的场景。
    UPSERT 把插入及冲突更新放在一条语句中，并发时仍遵循数据库的锁与异常机制。
    语句由 session.execute() 执行，成功提交或异常回滚的边界由上层管理。
    """
    # model_dump 返回 Python 字典；model_dump_json 返回 JSON 文本，不能直接做 **fields 展开。
    fields = payload.model_dump()
    fields["keywords"] = json.dumps(payload.keywords, ensure_ascii=False)
    statement = conflict_insert(session, Document).values(
        tenant_id=tenant_id, source_id=source_id, **fields,
    )
    session.execute(statement.on_conflict_do_update(
        index_elements=["tenant_id", "source_id"],
        # excluded[field] 指向新提交的值，fields 的键限定需要更新的业务列。
        set_={field: statement.excluded[field] for field in fields},
    ))


def remove_document(session: Session, tenant_id: str, source_id: str) -> None:
    """按租户和来源编号物理删除文档，事务由调用方控制。

    delete(Document).where(...) 构造删除 SQL，execute() 执行它。
    再次删除已不存在的记录会影响零行，当前接口仍返回 204，表达资源已移除的结果。
    相关的软删除通常更新 is_deleted 标记，所有检索也要明确排除已下架文档。
    物理删除移除当前表中的记录，数据库文件收缩、历史版本和备份回收由存储系统另行管理。
    """
    session.execute(delete(Document).where(
        Document.tenant_id == tenant_id, Document.source_id == source_id,
    ))


def answer_question(session: Session, actor: Actor, question: str) -> KnowledgeAnswer:
    """根据获授权文档的关键词命中数，返回原文答案或建议转人工。

    先用 actor.tenant_id 限定租户，customer 再限定 visibility='tenant'。
    casefold() 用于不区分大小写的 Unicode 比较，lower() 执行常见的小写转换。
    json.loads() 还原关键词列表，集合推导式去掉重复关键词，避免重复项额外加分。
    sum(keyword in normalized for keyword in keywords) 累加布尔值，每个命中的不同关键词计一分。
    本算法统计关键词是否出现，重复出现同一个词不会重复加分。
    更高分出现时替换候选列表，同分且大于零时保留多个候选，最终只采用唯一最高分。
    未命中或最高分并列时返回 transfer，由前端决定是否调用建单接口。
    相关的 BM25 考虑词频等特征，向量检索利用嵌入相似度，Rerank 可对召回候选重新排序。
    这些检索方法都需要继续保留身份过滤及引用来源，本例采用便于回归测试的确定性基线。
    """
    query = select(Document).where(Document.tenant_id == actor.tenant_id)
    # 授权过滤先于计分进行，未获授权文档不进入候选集合。
    if actor.role == "customer":
        query = query.where(Document.visibility == "tenant")

    normalized = question.casefold()
    best_score = 0
    best_documents: list[Document] = []

    # scalars 返回 Document 对象，逐篇统计不同关键词的命中数。
    for document in session.scalars(query):
        keywords = {keyword.casefold() for keyword in json.loads(document.keywords)}
        score = sum(keyword in normalized for keyword in keywords)
        if score > best_score:
            best_score = score
            best_documents = [document]
        elif score == best_score and score > 0:
            best_documents.append(document)

    # 无命中或最高分并列时建议转人工；资料本身的准确性仍需在导入阶段维护。
    if len(best_documents) != 1:
        return KnowledgeAnswer(route="transfer", message="未找到唯一适用的资料，可以创建工单转人工。")

    source = best_documents[0]
    return KnowledgeAnswer(
        route="answer",
        message=source.body,
        citation=Citation(source_id=source.source_id, title=source.title, excerpt=source.body),
    )
