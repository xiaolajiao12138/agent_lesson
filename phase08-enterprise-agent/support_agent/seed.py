"""企业实战第 5 课｜导入可复现的课程知识库，供接口练习和测试共用。

在项目目录通过 python -m support_agent.seed 运行，以便 Python 正确解析相对导入。
先执行 Alembic 迁移，脚本再根据 DATABASE_URL 向对应数据库写入样例。
下方数据是教学业务规则，重复运行会用这些基线内容更新同一批文档。
"""

from sqlalchemy.orm import Session, sessionmaker

from .db import build_engine
from .knowledge import save_document
from .schemas import DocumentInput


def seed_documents(session: Session) -> None:
    """在传入 Session 中导入四份样本文档，由调用方决定事务提交。

    每个元组依次包含租户、来源编号、标题、正文、关键词列表及可见范围。
    blue 和 green 的相同 source_id 用于验证租户隔离，reviewer 文档用于验证角色可见性。
    元组解包把每个位置交给对应变量，再组装 DocumentInput 进行校验。
    save_document() 使用 UPSERT，因此重复导入会更新基线内容。
    测试的 migrated fixture 也调用本函数，使测试数据与手动练习使用相同规则。
    """
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
    # __main__ 只在直接作为脚本/模块运行时进入，import seed 时保留函数供其他模块调用。
    engine = build_engine()
    try:
        sessions = sessionmaker(engine)
        # 工厂的 begin() 创建 Session 和事务，正常退出提交，异常回滚，最后关闭 Session。
        with sessions.begin() as session:
            seed_documents(session)
        print("课程知识库已写入。")
    finally:
        # 无论导入成功或失败，都释放本脚本拥有的引擎资源。
        engine.dispose()
