"""
================================================================================
企业实战：动态知识库管理与确定性检索评测基线
================================================================================
本模块实现了企业级支持 Agent 的动态知识库管理与分权问答检索。
涵盖核心技巧与类似方法对比：
    1. 【原子 UPSERT 更新】：on_conflict_do_update 实现安全覆盖旧版本文档
    2. 【幂等物理删除】：多次删除同一文档得到相同结果且不抛异常
    3. 【检索算法演进对比】：关键词词频基线 vs 全文检索 BM25 vs 向量语义检索 (pgvector)
    4. 【租户与角色分级可见性】：根据 actor.role 动态裁剪检索候选池（内部机密文档隔离）
"""

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .db import conflict_insert
from .models import Document
from .schemas import Citation, DocumentInput, KnowledgeAnswer
from .security import Actor


def save_document(session: Session, tenant_id: str, source_id: str, payload: DocumentInput) -> None:
    """
    【方法作用】：
        以租户内的业务编号（source_id）为唯一索引，原子执行“新增或覆盖更新 (UPSERT)”。
        当多次导入相同 source_id 的文档时，自动用最新的标题、内容与关键词覆盖旧内容。

    【参数说明】：
        session (Session): 数据库会话
        tenant_id (str): 所属企业租户 ID
        source_id (str): 外部知识库来源唯一编码（如 "KB-DOC-001"）
        payload (DocumentInput): Pydantic 文档入参模型

    【类似方法与底层原理对比】：
        1. on_conflict_do_update (UPSERT) 🌟（当前使用）
           - 原理：依赖底层数据库 (PostgreSQL / SQLite 3.24+) 原生支持的 `INSERT ... ON CONFLICT (...) DO UPDATE SET ...`；
           - 优势：一条 SQL 搞定，完全由数据库内核在单次索引加锁期间完成，高并发下绝无死锁或唯一索引违规崩溃。
        2. ❌ 传统两步走方案（先查后改）：
           - 代码：
               existing = session.query(Document).filter_by(tenant_id=..., source_id=...).first()
               if existing: existing.body = ...
               else: session.add(Document(...))
           - 弊端：在并发导入或多进程场景下，可能两个线程同时查到“不存在”，随后双双执行 INSERT，
             导致其中一个直接报 `IntegrityError: 唯一键冲突` 崩溃！
        3. 细节坑点提示：
           - `json.dumps(..., ensure_ascii=False)`：在保存中文列表时至关重要！
             如果不加 `ensure_ascii=False`，中文会被编码为 `\\u4f60\\u597d`，导致后续包含式字符串匹配彻底失效。
    """
    fields = payload.model_dump()
    fields["keywords"] = json.dumps(payload.keywords, ensure_ascii=False)
    statement = conflict_insert(session, Document).values(
        tenant_id=tenant_id, source_id=source_id, **fields,
    )
    session.execute(statement.on_conflict_do_update(
        index_elements=["tenant_id", "source_id"],
        set_={field: statement.excluded[field] for field in fields},
    ))


def remove_document(session: Session, tenant_id: str, source_id: str) -> None:
    """
    【方法作用】：
        幂等下架/删除指定租户下的某份文档。

    【参数说明】：
        session (Session): 数据库会话
        tenant_id (str): 租户 ID（强制限定租户，防止误删他人文档）
        source_id (str): 要删除的文档来源 ID

    【物理删除 vs 逻辑软删除 对比】：
        1. 物理删除 (当前使用)：直接执行 `DELETE FROM documents WHERE ...`。
           - 优势：真正释放磁盘空间，保证已删除的机密内容绝对无法再被检索出来；
           - 幂等性：即使该文档已经被删除了，再次调用该函数依然成功执行（匹配删除 0 行，不报错）。
        2. 逻辑软删除 (Soft Delete)：
           - 做法：表结构增加 `is_deleted: bool = False`，删除时仅执行 `UPDATE documents SET is_deleted=True`；
           - 适用场景：需要长久法律审计、或者提供“回收站撤销删除”功能的企业系统。
    """
    session.execute(delete(Document).where(
        Document.tenant_id == tenant_id, Document.source_id == source_id,
    ))


def answer_question(session: Session, actor: Actor, question: str) -> KnowledgeAnswer:
    """
    【方法作用】：
        智能知识库检索问答引擎：
        1. 权限过滤：普通客户只能看到 `visibility == 'tenant'` 的公开文档，客服/管理员可看内部机密文档；
        2. 算法匹配：计算匹配得分，若有且仅有【唯一的最高分文档】，直接引用该文档生成准确回答；
        3. 防幻觉兜底：若未命中任何资料、或存在多篇得分相同的冲突文档，建议走【工单转人工】流程！

    【参数说明】：
        session (Session): 数据库会话
        actor (Actor): 请求发起者身份
        question (str): 提问内容

    【返回值】：
        KnowledgeAnswer: 包含 route ("answer" 或 "transfer")、回答正文及引用出处 (Citation)

    【现代 Agent 检索体系全景对比】：
        1. 关键词词频基线 (当前做法)：
           - 优势：完全确定性、零 Token 开销、毫秒级响应，是构建自动化 Regression 评测集的绝佳基线；
           - 局限：无法理解同义词（如“笔记本”和“电脑”如果不配置同义关键词就无法匹配）。
        2. 数据库全文检索 (PostgreSQL tsvector / ElasticSearch BM25)：
           - 优势：支持中文分词（结巴分词 / IK 分词器）、词频-逆文档频率 (TF-IDF) 打分，支持百万级文档快速全文查找。
        3. 向量语义检索 (pgvector / Chroma / Embedding)：
           - 优势：基于高维向量余弦距离计算，擅长理解模糊意图与近义表达；
           - 最佳实践：企业级生产环境通常采用【双路混合检索 (Hybrid Search)】——
             关键词全文检索（保底型号/专有名词精确匹配）+ 向量语义检索（理解口语化表达），再通过 Rerank 模型重新打分！
    """
    query = select(Document).where(Document.tenant_id == actor.tenant_id)
    # 动态权限裁剪：隔离租户内部敏感资料
    if actor.role == "customer":
        query = query.where(Document.visibility == "tenant")

    normalized = question.casefold()
    best_score = 0
    best_documents: list[Document] = []
    
    # 遍历候选文档并根据关键词重合度进行计分
    for document in session.scalars(query):
        keywords = {keyword.casefold() for keyword in json.loads(document.keywords)}
        score = sum(keyword in normalized for keyword in keywords)
        if score > best_score:
            best_score = score
            best_documents = [document]
        elif score == best_score and score > 0:
            best_documents.append(document)

    # 无法锁定唯一确切答案时，优雅降级转人工，彻底杜绝大模型在缺乏依据时强行胡编胡扯（幻觉）
    if len(best_documents) != 1:
        return KnowledgeAnswer(route="transfer", message="未找到唯一适用的资料，可以创建工单转人工。")

    source = best_documents[0]
    return KnowledgeAnswer(
        route="answer",
        message=source.body,
        citation=Citation(source_id=source.source_id, title=source.title, excerpt=source.body),
    )
