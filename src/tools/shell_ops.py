"""
文件名: shell_ops.py
核心作用: Agent 的"测试执行器"（运行 pytest 并捕获反馈）。

详细解释:
1. 为什么用 subprocess？
   - 这是 Python 官方推荐的"调用外部命令"方式。
   - 我们用它来启动一个新的 Python 进程运行 pytest，与 Agent 主进程完全隔离。
   - 即使测试代码引发 SystemExit 或死循环，也不会拖垮整个 Agent。

2. 返回值设计 (bool, str)：
   - bool: True 表示所有测试通过，False 表示有测试失败或发生异常。
   - str: 包含完整的 stdout 和 stderr，供 LLM 分析报错原因。

3. 超时熔断（timeout）：
   - 设置为 30 秒，防止测试代码陷入死循环。
   - 超时后 subprocess 会抛出 TimeoutExpired，我们捕获并转为友好的错误字符串。
"""
import subprocess
import sys
import os
from src.utils.logger import get_logger

logger = get_logger(__name__)

def run_pytest(test_file_path: str, timeout: int = 30) -> tuple[bool, str]:
    """
    在独立的子进程中运行 pytest，捕获所有输出。

    参数:
        test_file_path: 测试文件路径（如 "test_target.py"）
        timeout: 超时秒数（默认 30 秒）

    返回:
        (bool, str): (测试是否通过, 完整的终端日志输出)
    """
    # 1. 检查测试文件是否存在（如果不存在，直接返回失败）
    if not os.path.exists(test_file_path):
        logger.error(f"测试文件不存在，无法执行: {test_file_path}")
        return False, f"错误：测试文件 {test_file_path} 不存在"
    
    # 2. 构建执行命令（使用 -v 显示详细信息，--tb=short 精简堆栈便于 LLM 阅读）
    cmd = [sys.executable, "-m", "pytest", test_file_path, "-v", "--tb=short"]
    logger.info(f"开始执行测试: {' '.join(cmd)}")
    
    try:
        # 3. 启动子进程并等待结果（自动捕获 stdout 和 stderr）
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,          # 将输出转为字符串（而非字节）
            timeout=timeout,
            cwd="."             # 在当前工作目录运行（可改为沙箱路径）
        )
        
        # 4. 合并 stdout 和 stderr（方便 LLM 一次性分析）
        full_log = result.stdout + "\n" + result.stderr
        
        # 5. 判断返回码：0 表示所有测试通过，非 0 表示有失败
        if result.returncode == 0:
            logger.info(f"✅ 测试全部通过: {test_file_path}")
            return True, full_log
        else:
            logger.warning(f"❌ 测试失败 (退出码 {result.returncode}): {test_file_path}")
            return False, full_log
            
    except subprocess.TimeoutExpired as e:
        # 6. 超时处理（这是测试代码陷入死循环时的救命稻草）
        error_msg = f"⏰ 测试执行超时 (>{timeout}秒)，已强制终止。"
        logger.error(error_msg)
        return False, error_msg + "\n" + str(e)
        
    except Exception as e:
        # 7. 其他意外异常（如 Python 环境问题）
        error_msg = f"💥 运行测试时发生未知异常: {str(e)}"
        logger.error(error_msg)
        return False, error_msg