"""
文件名: file_ops.py
核心作用: Agent 的"文件系统手脚"（底层原子操作）。

详细解释:
1. 为什么需要这个文件？
   - 这是整个项目中唯一直接操作磁盘的地方。
   - 将文件读写、搜索替换封装成纯函数，与 AI 逻辑（nodes.py）完全解耦。
   - 这样做的好处是：即使将来把 AI 从 DeepSeek 换成 GPT，底层的文件操作完全不用动。

2. 核心设计：搜索替换的"安全机制"
   - 本文件不依赖任何 AI 库，只使用 Python 内置的 os 和文件操作。
   - apply_search_replace 使用最保守的"字符串逐字匹配"策略。
   - 返回布尔值 (True/False) 而不是直接抛异常，便于上层节点做"重试"或"回退"决策。
"""
import os
from src.utils.logger import get_logger

# 获取当前模块的日志记录器
logger = get_logger(__name__)


def read_file_content(file_path: str) -> str:
    """
    读取目标文件的完整内容。
    如果文件不存在，抛出明确的 FileNotFoundError。
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        raise FileNotFoundError(f"❌ 文件 {file_path} 不存在，请检查路径")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    logger.debug(f"成功读取文件: {file_path} (共 {len(content)} 字符)")
    return content

def write_test_file(original_file_path: str, code: str) -> str:
    """
    将生成的测试代码写入磁盘。
    自动在相同目录下创建 test_ 开头的文件。
    返回新创建的测试文件路径，供后续 pytest 调用。
    """
    # 获取文件所在目录名
    dir_name = os.path.dirname(original_file_path)
    # 获取文件名
    base_name = os.path.basename(original_file_path)
    # 如果原文件是 target.py，测试文件就是 test_target.py
    test_path = os.path.join(dir_name, f"test_{base_name}")

    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(code)

    logger.info(f"测试文件已写入: {test_path}")
    return test_path

def apply_search_replace(file_path: str, search: str, replace: str) -> bool:
    """
    执行保守的"搜索并替换"操作。
    
    参数:
        file_path: 目标文件路径
        search: 需要被替换的原始代码块（必须逐字匹配，包括缩进和空格）
        replace: 替换后的新代码块
    
    返回:
        bool: True 表示替换成功；False 表示未找到 search 片段（操作被安全拦截）
    """
    if not os.path.exists(file_path):
        logger.warning(f"替换跳过：文件不存在 -> {file_path}")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if search not in content:
        logger.warning(f"替换失败：在 {file_path} 中未找到匹配的代码段")
        return False
    
    new_content = content.replace(search, replace, 1)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    logger.info(f"✅ 补丁应用成功: {file_path}")
    return True