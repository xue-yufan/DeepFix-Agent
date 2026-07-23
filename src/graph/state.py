"""
该文件采用优化过的版本。
"""

"""
文件名: state.py（原始版）
核心作用: 定义 Agent 的"全局状态结构"（State Schema）。

详细解释:
1. 为什么需要这个文件？
   LangGraph 的核心是"状态机"。这个文件定义了 Agent 在运行过程中，
   需要在节点之间传递哪些数据。它相当于整个 Agent 的"上下文管理器"。

2. 设计原则（为什么分三组）？
   - 输入组: 任务启动时的固定参数（只读）。
   - 过程组: 运行时产生的动态数据（可读可写），如报错、迭代次数。
   - 路由组: 控制流程走向，决定下一步执行哪个节点。

3. 特殊说明（Annotated 和 operator.add）：
   - patch_history 使用了 Annotated[List[str], operator.add]。
   - 这意味着每次更新这个字段时，不是覆盖，而是"追加"。
   - 好处：即使节点重试或并行，历史记录也不会丢失，方便追溯。
"""

"""
文件名: state.py (优化版)
核心作用: 定义 Agent 的"全局状态结构"，并集成高级控制逻辑。

优化亮点：
1. 将 patch_history 从 List[str] 升级为 List[SearchReplacePatch]，保留完整的补丁对象。
2. 自定义 Reducer 函数，自动限制历史记录长度（最多10条），防止内存泄漏。
3. 内置 max_iterations 配置和 is_maxed_out 状态，实现"熔断下沉"。
4. 增加 thoughts 字段，专门存储 DeepSeek 的推理过程（reasoning_content），便于调试。

技术栈：使用 Pydantic BaseModel（替代 TypedDict），实现运行时类型校验和默认值。
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Annotated
from src.schemas.patch import SearchReplacePatch

# ---------- 自定义 Reducer 函数（控制列表长度，减小开销） ----------
def add_patches(left: List[SearchReplacePatch], right: List[SearchReplacePatch]) -> List[SearchReplacePatch]:
    """
    追加补丁列表，并强制只保留最近 10 条。
    用法：在节点中返回 {"patch_history": [new_patch]}，此函数自动追加并截断。
    """
    combined = left + right
    return combined[-10:]  # 只保留最后10条

def add_thoughts(left: List[str], right: List[str]) -> List[str]:
    """
    追加思考链，并强制只保留最近 10 条。
    防止 DeepSeek 的超长推理内容撑爆内存。
    """
    combined = left + right
    return combined[-10:]

# ---------- Agent 全局状态（继承 BaseModel，自带校验和默认值） ----------
class AgentState(BaseModel):
    """
    Agent 的全局状态。
    所有节点（生成、执行、修复）通过这个模型进行数据交换。
    """
    
    # ----- 1. 输入信息（任务启动时设定） -----
    target_file: str = Field(..., description="待修复的目标文件路径")
    target_function: str = Field(..., description="目标函数名称")
    
    # ----- 2. 熔断与控制参数（内置上限） -----
    max_iterations: int = Field(5, description="最大允许的修复迭代次数（防止死循环）")
    is_maxed_out: bool = Field(False, description="是否已达到迭代上限（由节点自动计算）")
    
    # ----- 3. 工作过程（运行时动态更新） -----
    test_code: str = Field("", description="当前生成的测试用例代码")
    error_trace: str = Field("", description="最新的 pytest 报错堆栈信息")
    iteration: int = Field(0, description="当前已执行的修复迭代次数")
    
    # 修复历史：存储补丁对象（自动追加，只留最近10条）
    patch_history: Annotated[List[SearchReplacePatch], add_patches] = Field(
        default_factory=list,
        description="已应用的补丁对象列表（自动保留最近10条）"
    )
    
    # 思考链：存储 DeepSeek 的推理过程（自动追加，只留最近10条）
    thoughts: Annotated[List[str], add_thoughts] = Field(
        default_factory=list,
        description="DeepSeek 的推理思考过程（便于调试 Prompt）"
    )
    
    # ----- 4. 最终结果与路由 -----
    test_passed: bool = Field(False, description="测试是否通过")
    final_patch: Optional[SearchReplacePatch] = Field(None, description="最终成功应用的补丁")
    next_step: str = Field("start", description="路由标识，告诉图引擎下一步去哪")