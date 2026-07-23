"""
文件名: builder.py
核心作用: 组装 LangGraph 工作流（支持两种模式：逐函数修复 / 全面重写）。
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from src.graph.state import AgentState
from src.graph.nodes import generate_test_node, execute_test_node, fix_code_node, rewrite_file_node
from src.graph.router import should_continue
from src.utils.logger import get_logger
import os
import sqlite3

logger = get_logger(__name__)

def build_agent(mode: str = "iterative"):
    """
    构建并编译完整的 Agent 图。
    
    参数:
        mode: "iterative"（逐函数修复，默认）或 "rewrite"（全面重写）
    """
    logger.info(f"🏗️  开始组装 Agent 工作流 (模式: {mode})...")
    
    builder = StateGraph(AgentState)
    
    # 注册所有节点
    builder.add_node("rewrite_file", rewrite_file_node)
    builder.add_node("generate_test", generate_test_node)
    builder.add_node("execute", execute_test_node)
    builder.add_node("fix", fix_code_node)
    
    # ---------- 根据模式选择入口 ----------
    if mode == "rewrite":
        builder.set_entry_point("rewrite_file")
        builder.add_edge("rewrite_file", "execute")
    else:
        builder.set_entry_point("generate_test")
        builder.add_edge("generate_test", "execute")
    
    # ---------- 公共路由 ----------
    builder.add_conditional_edges(
        "execute",
        should_continue,
        {
            "end": END,
            "fix": "fix"
        }
    )
    builder.add_edge("fix", "execute")  # 修复完再执行（闭环）
    
    # 配置持久化
    os.makedirs("checkpoints", exist_ok=True)
    conn = sqlite3.connect("checkpoints/agent_memory.db", check_same_thread=False)
    memory = SqliteSaver(conn)
    logger.info(f"✅ 检查点已挂载 (模式: {mode})")
    
    graph = builder.compile(checkpointer=memory)
    logger.info("🎯 Agent 组装完成！")
    return graph