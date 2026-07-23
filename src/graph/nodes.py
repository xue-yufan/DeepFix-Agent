"""
文件名: nodes.py
核心作用: 定义 LangGraph 的所有工作节点（生成 -> 执行 -> 修复 -> 重写）。
"""
import os
import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage

from src.models.deepseek_gateway import get_llm, get_json_llm
from src.tools.file_ops import read_file_content, write_test_file, apply_search_replace
from src.tools.shell_ops import run_pytest
from src.schemas.patch import SearchReplacePatch
from src.utils.logger import get_logger
from src.graph.state import AgentState

logger = get_logger(__name__)


def generate_test_node(state: AgentState) -> Dict[str, Any]:
    """节点 1：生成测试代码"""
    logger.info(f"📝 [生成节点] 开始为目标文件生成测试: {state.target_file}")
    
    try:
        source_code = read_file_content(state.target_file)
    except FileNotFoundError as e:
        logger.error(f"生成节点中止：{e}")
        return {"next_step": "end", "test_passed": False, "error_trace": str(e)}
    
    prompt = f"""你是一个资深的测试工程师。请为以下 Python 函数生成完整的 pytest 单元测试代码。
要求覆盖正常路径、边界条件和异常情况。
请**只输出 Python 代码**，不要包含任何解释、注释或 Markdown 标记（不要用 ```python 包裹）。

目标函数名: {state.target_function}
目标函数源码：
{source_code}
"""
    
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    raw_test_code = response.content
    
    # 清理 Markdown
    test_code = raw_test_code
    if "```python" in test_code:
        test_code = test_code.split("```python")[1].split("```")[0]
    elif "```" in test_code:
        test_code = test_code.split("```")[1].split("```")[0]
    test_code = test_code.strip()
    
    test_path = write_test_file(state.target_file, test_code)
    logger.info(f"✅ 测试文件已生成: {test_path}")
    
    return {
        "test_code": test_code,
        "next_step": "execute",
    }


def execute_test_node(state: AgentState) -> Dict[str, Any]:
    """节点 2：执行测试"""
    logger.info(f"▶️  [执行节点] 开始运行测试 (迭代次数: {state.iteration})")
    
    dir_name = os.path.dirname(state.target_file)
    base_name = os.path.basename(state.target_file)
    test_path = os.path.join(dir_name, f"test_{base_name}")
    
    passed, log = run_pytest(test_path, timeout=30)
    
    if passed:
        logger.info(f"🎉 测试全部通过！任务完成。")
        return {
            "test_passed": True,
            "error_trace": "",
            "next_step": "end",
        }
    else:
        logger.warning(f"❌ 测试失败，将进入修复流程。")
        return {
            "test_passed": False,
            "error_trace": log,
            "next_step": "fix",
        }


def fix_code_node(state: AgentState) -> Dict[str, Any]:
    """节点 3：修复代码（补丁模式）"""
    logger.info(f"🔧 [修复节点] 开始分析报错并生成补丁 (第 {state.iteration + 1} 次修复)")
    
    if state.test_passed:
        return {"next_step": "end"}
    
    try:
        source_code = read_file_content(state.target_file)
    except FileNotFoundError as e:
        logger.error(f"修复节点中止：{e}")
        return {"next_step": "end", "test_passed": False, "error_trace": str(e)}
    
    prompt = f"""你是一个代码修复专家。请根据以下报错信息，修改代码。
**重要**：你必须输出纯 JSON 格式，不要包含 Markdown 或任何解释。
JSON 必须包含以下字段：
{{
    "file_path": "目标文件的相对路径",
    "search": "需要被替换的旧代码段（必须与原文逐字匹配，包括缩进）",
    "replace": "替换后的新代码段",
    "description": "本次修复的简要说明"
}}

目标文件路径: {state.target_file}
报错堆栈信息:
{state.error_trace}

原始代码:
{source_code}
"""
    
    json_llm = get_json_llm()
    try:
        response = json_llm.invoke([HumanMessage(content=prompt)])
        patch_data = json.loads(response.content)
        patch = SearchReplacePatch(**patch_data)
        logger.info(f"📋 AI 生成的补丁描述: {patch.description}")
        
        success = apply_search_replace(patch.file_path, patch.search, patch.replace)
        
        if success:
            logger.info(f"✅ 补丁应用成功！")
            return {
                "iteration": state.iteration + 1,
                "patch_history": [patch],
                "final_patch": patch,
                "error_trace": "",
                "next_step": "execute",
                "test_passed": False,
            }
        else:
            logger.error("❌ 补丁应用失败：未在文件中找到匹配的 search 代码段。")
            return {
                "error_trace": f"补丁应用失败：未找到匹配的代码段。\nAI 试图查找:\n{patch.search}",
                "next_step": "execute",
                "iteration": state.iteration + 1,
            }
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ AI 返回的不是合法 JSON: {e}\n内容: {response.content[:200]}...")
        return {
            "error_trace": f"AI 输出格式错误，无法解析补丁。错误: {str(e)}",
            "next_step": "execute",
            "iteration": state.iteration + 1,
        }
    except Exception as e:
        logger.error(f"💥 修复节点发生未知异常: {str(e)}")
        return {
            "error_trace": f"修复节点异常: {str(e)}",
            "next_step": "end",
        }


def rewrite_file_node(state: AgentState) -> Dict[str, Any]:
    """
    节点 0（可选）：全面重写文件。
    一次性分析整个文件的所有错误，直接重写为正确版本。
    模仿 Claude Code 的 "fix this file" 行为。
    """
    logger.info(f"📝 [重写节点] 开始全面分析并重写文件: {state.target_file}")
    
    try:
        source_code = read_file_content(state.target_file)
    except FileNotFoundError as e:
        logger.error(f"重写节点中止：{e}")
        return {"next_step": "end", "test_passed": False, "error_trace": str(e)}
    
    prompt = f"""你是一位资深的软件架构师。请**仔细分析**以下 Python 文件中的所有函数，找出所有潜在的 Bug、逻辑错误、类型隐患和边界条件问题。

然后，**直接输出修复后完整的 Python 文件代码**，要求：
- 保持原有函数名和整体结构不变。
- 修复所有错误（如除零、空列表访问、类型错误、浮点数精度等）。
- 添加必要的类型注解（Type Hints）。
- 添加清晰的注释说明改动点。
- **只输出完整的 Python 代码**，不要包含 Markdown 包裹（如 ```python），不要添加额外解释。

--- 原始文件 ---
{source_code}
--- 结束 ---
"""
    
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    new_code = response.content
    
    # 防御性清理
    if "```python" in new_code:
        new_code = new_code.split("```python")[1].split("```")[0]
    elif "```" in new_code:
        new_code = new_code.split("```")[1].split("```")[0]
    new_code = new_code.strip()
    
    # 直接覆盖原文件（此时 state.target_file 指向 test/xxx/ 下的副本）
    with open(state.target_file, "w", encoding="utf-8") as f:
        f.write(new_code)
    
    logger.info(f"✅ 文件已全面重写: {state.target_file}")
    
    return {
        "test_code": "",
        "error_trace": "",
        "iteration": 0,
        "patch_history": [],
        "next_step": "execute",
        "test_passed": False,
    }