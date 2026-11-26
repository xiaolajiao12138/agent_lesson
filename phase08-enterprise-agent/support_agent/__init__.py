"""售后工单 Agent 课程的 Python 包入口。

__init__.py 标记并初始化包，本文件用文档字符串说明包用途。
通过 uvicorn support_agent.main:create_app --factory 启动应用工厂。
通过 python -m support_agent.seed 运行样例导入，Python 会按包路径解析相对导入。
__name__ == '__main__' 的分支在直接执行对应模块时运行，导入时保留定义供调用方使用。
"""
