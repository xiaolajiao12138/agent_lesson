"""
【Python 零基础·课时 05】面向对象全透视：Class、__init__ 与 self 到底是什么？
文件说明：
    在 Agent 框架中，智能体通常都是以“类 (Class)”的形式封装的。
    前端同学最困惑的往往是：
    1. 为什么每个方法第一位都要写一个 self？
    2. __init__ 是个什么东西？
    3. __call__ 魔法方法怎么让类像函数一样执行？
    本文件拿 JS/ES6 Class 全程做镜像对照。
运行方式：
    python lesson05_oop_classes_and_self.py
"""

from typing import List

# ==============================================================================
# 1. 类的声明与 __init__ 构造函数（对标 JS class 与 constructor）
# ==============================================================================

# JS/TS 写法:
# class BaseAgent {
#   constructor(name, model = "gpt-4o") {
#     this.name = name;
#     this.model = model;
#     this.history = [];
#   }
#   sendMessage(content) {
#     this.history.push(content);
#   }
# }

class BaseAgent:
    """智能体基础父类"""

    # 1. __init__ 就是 Python 类的构造函数（相当于 JS 的 constructor）
    # 2. self 代表“当前被创建出来的那个对象实例”（严格等价于 JS 中的 this！）
    # 关键差异：JS 会在方法内隐式提供 this；而 Python 规范要求方法的第一个形参必须显式写出 self！
    def __init__(self, name: str, model: str = "gpt-4o"):
        self.name: str = name               # 实例属性绑定 (类似 this.name = name)
        self.model: str = model             # 类似 this.model = model
        self.message_history: List[str] = [] # 类似 this.message_history = []

    def log_action(self, action_name: str) -> None:
        """实例方法：第一个参数永远是 self，用于访问内部属性"""
        print(f"[{self.name}] 正在执行111动作: {action_name} (底层驱动模型: {self.model})")
        # 科研助手小智 正在执行动作 ：{action_name} 模型：deepseek_r1
    # 魔法方法 __str__：相当于 JS 对象的 .toString()
    # 当 print(agent) 时会自动调用该方法
    def __str__(self) -> str:
        return f"<BaseAgent 实例: 名称={self.name}, 历史对话条数={len(self.message_history)}>"


# ==============================================================================
# 2. 类的继承与 super()（对标 JS class Child extends Parent）
# ==============================================================================

class ResearchAgent(BaseAgent):
    """专门负责网络调研的子类智能体"""

    def __init__(self, name: str, search_engine: str = "Google", model: str = "gpt-4o"):
        # 调用父类构造函数（严格等价于 JS 的 super(name, model)）
        super().__init__(name=name, model=model)
        # 子类专属扩展属性
        self.search_engine: str = search_engine

    # 子类专属方法
    def execute_search(self, query: str) -> str:
        self.log_action(f"调用 {self.search_engine} 引擎检索关键词: '{query}'")
        result = f"检索到关于「{query}」的最新技术文档共 3 篇。"
        # 记录到从父类继承来的 message_history 中
        self.message_history.append(result)
        return result

    def getname(self,name) : 
        self.name = name
        return name
    # 核心黑魔法：__call__
    # 在 Python 中，只要一个类实现了 __call__ 方法，它的实例就可以像函数一样被直接调用！
    # 例如：agent("帮我查资料") 等价于 agent.__call__("帮我查资料")
    # 这在 LangChain / LangGraph 源码中无处不在！
    def __call__(self, query: str) -> str:
        return self.execute_search(query)


# ==============================================================================
# 运行演示
# ==============================================================================

def demo_oop():
    # print("=== 1. 实例化与方法调用 ===")
    
    # 类似 JS: const agent = new ResearchAgent("科研助手小智", "Bing");
    # Python 实例化不需要 new 关键字，直接当作函数调用 类名(...)
    researcher = ResearchAgent(name="科研助手小智", search_engine="Bing", model="deepseek-r1")
    # print(f"{researcher}")
    # 调用继承与扩展的方法
    res1 = researcher.execute_search("Vue 与 React 渲染机制差异")
    print(f"返回结果: {res1}")

    # print("\n=== 2. 查看继承自父类的历史记录与 __str__ ===")
    # print(f"打印实例对象: {researcher}")
    print(f"访问内部属性: {researcher.message_history}")

    # print("\n=== 3. 体验 __call__ 魔法方法（把对象当函数执行） ===")
    # # 注意看：这里直接像函数一样调用了 researcher 这个对象！
    res2 = researcher("Next.js 15 Server Actions 最佳实践")
    # 检索到next.js.....的最新技术文档共 3 篇
    print(f"通过 __call__ 调用的输出: {res2}")
    print(f"累计历史记录条数: {len(researcher.message_history)}")


if __name__ == "__main__":
    demo_oop()
