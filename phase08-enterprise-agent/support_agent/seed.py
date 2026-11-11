"""企业实战第 5 课｜重复运行可恢复一组教学文档。请使用课程数据库。"""

from sqlalchemy.orm import Session, sessionmaker

from .db import build_engine
from .knowledge import save_document
from .schemas import DocumentInput


def seed_documents(session: Session) -> None:
    """写入可公开、角色限制和跨租户样本，方便验证不同授权范围。"""
    documents = [
        ("blue", "returns", "蓝店退换政策", "签收后 7 天内可提交退货申请。", ["退货", "退换"], "tenant"),
        ("blue", "delivery", "蓝店物流", "发货后可在订单详情页查看物流单号。", ["物流", "快递"], "tenant"),
        ("blue", "manual", "内部核查规则", "审批员需核对交接编号。", ["交接编号"], "reviewer"),
        ("green", "returns", "绿店退换政策", "签收后 15 天内可提交退货申请。", ["退货", "退换"], "tenant"),
    ]
    for tenant_id, source_id, title, body, keywords, visibility in documents:
        save_document(session, tenant_id, source_id, DocumentInput(
            title=title, body=body, keywords=keywords, visibility=visibility,
        ))


if __name__ == "__main__":
    engine = build_engine()
    try:
        sessions = sessionmaker(engine)
        with sessions.begin() as session:
            seed_documents(session)
        print("课程知识库已写入。")
    finally:
        engine.dispose()
