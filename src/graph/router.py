"""
文件名: router.py
核心作用: 条件路由（决定下一步去哪）。
"""
from src.graph.state import AgentState
from src.utils.logger import get_logger

logger = get_logger(__name__)

def should_continue(state: AgentState) -> str:
    """
    判断 Agent 下一步该去修复还是结束。
    这是整个 Agent 的"熔断开关"。
    """
    # 1. 如果测试通过了，任务结束
    if state.test_passed:
        logger.info("🏁 测试已通过，任务完成！")
        return "end"
    
    # 2. 如果达到最大迭代次数，强制停止（防止无限循环）
    if state.iteration >= state.max_iterations:
        logger.warning(f"⛔ 达到最大迭代次数 ({state.max_iterations})，强制终止。")
        return "end"
    
    # 3. 否则，进入修复流程
    logger.info(f"🔄 测试失败，进入修复流程 (当前迭代: {state.iteration + 1}/{state.max_iterations})")
    return "fix"