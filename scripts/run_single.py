"""
文件名: run_single.py
核心作用: 命令行入口，启动 Agent 修复指定的 Python 文件。
支持两种模式:
  - iterative: 逐函数修复（默认）
  - rewrite: 全面重写整个文件（类似 Claude Code）
"""
import sys
import os
import argparse
import shutil
import ast
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph.builder import build_agent
from src.graph.state import AgentState
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 固定输出根目录
OUTPUT_ROOT = "test"

def extract_functions(file_path: str) -> list[str]:
    """从 Python 文件中提取所有顶层函数名"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        return functions
    except Exception as e:
        logger.error(f"提取函数列表失败: {e}")
        return []

def run_agent_for_function(target_file: str, func_name: str, max_iter: int, agent) -> dict:
    """为指定函数运行一次 Agent（用于 iterative 模式）"""
    initial_state = AgentState(
        target_file=target_file,
        target_function=func_name,
        max_iterations=max_iter,
        test_code="",
        error_trace="",
        iteration=0,
        patch_history=[],
        thoughts=[],
        test_passed=False,
        final_patch=None,
        next_step="start"
    )
    
    thread_id = f"{target_file.replace('\\', '_').replace('/', '_').replace(':', '')}_{func_name}"
    config = {"configurable": {"thread_id": thread_id}}
    
    logger.info(f"🔧 正在修复函数: {func_name}")
    final_state = agent.invoke(initial_state.model_dump(), config=config)
    return final_state

def main():
    parser = argparse.ArgumentParser(description="启动测试自愈 Agent")
    parser.add_argument("--file", required=True, help="目标 Python 文件路径（如 target.py）")
    parser.add_argument("--func", default=None, help="指定要修复的函数名（不指定则自动修复所有顶层函数，仅 iterative 模式有效）")
    parser.add_argument("--max-iter", type=int, default=5, help="每个函数的最大修复迭代次数（默认 5）")
    parser.add_argument("--mode", default="iterative", choices=["iterative", "rewrite"],
                        help="运行模式: iterative(逐函数修复) 或 rewrite(全面重写，类似Claude Code)")
    args = parser.parse_args()
    
    original_file = args.file
    if not os.path.exists(original_file):
        logger.error(f"❌ 目标文件不存在: {original_file}")
        return
    
    # 准备输出目录
    file_name = os.path.basename(original_file)
    name_without_ext = os.path.splitext(file_name)[0]
    output_subdir = os.path.join(OUTPUT_ROOT, name_without_ext)
    os.makedirs(output_subdir, exist_ok=True)
    
    dest_file = os.path.join(output_subdir, file_name)
    shutil.copy2(original_file, dest_file)
    logger.info(f"📁 工作文件: {dest_file}")
    
    # 构建 Agent（传入模式）
    agent = build_agent(mode=args.mode)
    
    # ---------- 根据模式执行 ----------
    if args.mode == "rewrite":
        # 全面重写模式：一次性处理整个文件
        logger.info("📌 全面重写模式：将一次性分析并重写整个文件")
        initial_state = AgentState(
            target_file=dest_file,
            target_function="all",
            max_iterations=args.max_iter,
            test_code="",
            error_trace="",
            iteration=0,
            patch_history=[],
            thoughts=[],
            test_passed=False,
            final_patch=None,
            next_step="start"
        )
        thread_id = dest_file.replace("\\", "_").replace("/", "_").replace(":", "")
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.info("⏳ Agent 开始运行...\n" + "="*50)
        final_state = agent.invoke(initial_state.model_dump(), config=config)
        
        # 输出结果
        print("\n" + "="*50)
        print("📊 最终执行报告 (重写模式)")
        print("="*50)
        print(f"✅ 测试是否通过: {'是' if final_state.get('test_passed') else '否'}")
        print(f"🔄 总迭代次数: {final_state.get('iteration', 0)}")
        if final_state.get('patch_history'):
            print(f"📝 应用补丁数量: {len(final_state['patch_history'])}")
        if final_state.get('final_patch'):
            print(f"💡 最终补丁说明: {final_state['final_patch'].description}")
        if not final_state.get('test_passed'):
            print("\n⚠️  测试未通过，请检查日志 logs/agent.log")
        else:
            print(f"\n📁 修复后的文件: {dest_file}")
        print("="*50)
    
    else:
        # iterative 模式：逐个函数修复
        if args.func:
            func_list = [args.func]
        else:
            func_list = extract_functions(original_file)
            if not func_list:
                logger.error(f"❌ 未能从文件中提取到任何函数: {original_file}")
                return
            logger.info(f"📋 自动提取到 {len(func_list)} 个函数: {', '.join(func_list)}")
        
        results = {}
        all_passed = True
        
        for func_name in func_list:
            logger.info(f"\n{'='*40}\n🔨 开始修复函数: {func_name}\n{'='*40}")
            final_state = run_agent_for_function(dest_file, func_name, args.max_iter, agent)
            results[func_name] = final_state
            if not final_state.get('test_passed'):
                all_passed = False
                logger.warning(f"⚠️ 函数 {func_name} 修复失败")
            else:
                logger.info(f"✅ 函数 {func_name} 修复成功")
        
        # 汇总报告
        print("\n" + "="*50)
        print("📊 最终汇总报告 (逐函数修复)")
        print("="*50)
        print(f"📁 工作目录: {output_subdir}")
        print(f"📋 共处理函数: {len(func_list)} 个")
        print(f"✅ 全部通过: {'是' if all_passed else '否'}")
        for func_name, state in results.items():
            status = "✅ 通过" if state.get('test_passed') else "❌ 失败"
            iteration = state.get('iteration', 0)
            patch_count = len(state.get('patch_history', []))
            print(f"   {func_name}: {status} (迭代 {iteration} 次, 补丁 {patch_count} 个)")
        
        test_file = os.path.join(output_subdir, f"test_{file_name}")
        if os.path.exists(test_file):
            print(f"\n📁 测试文件已生成: {test_file}")
        print("="*50)

if __name__ == "__main__":
    main()