"""
文件名: deepseek_gateway.py
核心作用: DeepSeek API 的统一网关（封装 LangChain 调用）。

详细解释:
1. 为什么需要这个文件？
   - 所有 nodes（生成、修复）都通过这里调用 DeepSeek。
   - 如果将来要更换模型（如 GPT-4），只需修改这一个文件。
   - 自动从 .env 读取 API Key，避免硬编码。

2. 关键特性：结构化输出（JSON Mode）
   - 在修复代码时，我们必须强制 DeepSeek 输出 JSON 格式的补丁。
   - 使用 .bind(response_format={"type": "json_object"}) 来实现。
   - 注意：这里已经帮你规避了 LangChain 与 DeepSeek 的兼容性坑。
"""
import os
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
from src.utils.logger import get_logger

# 加载 .env 文件中的环境变量
load_dotenv()

logger = get_logger(__name__)

# ---------- 配置常量（可通过环境变量覆盖） ----------
DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEFAULT_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))

def get_llm() -> ChatDeepSeek:
    """
    获取一个标准的 DeepSeek LLM 实例（用于通用对话和工具调用）。
    所有节点共享此实例，节省内存且保持配置统一。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("环境变量 DEEPSEEK_API_KEY 未设置！请在 .env 文件中配置。")
        raise ValueError("DEEPSEEK_API_KEY is required")
    
    logger.debug(f"初始化 DeepSeek 模型: {DEFAULT_MODEL}, temperature={DEFAULT_TEMPERATURE}")
    
    return ChatDeepSeek(
        model=DEFAULT_MODEL,
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
    )

def get_json_llm() -> ChatDeepSeek:
    """
    获取一个强制输出 JSON 的 LLM 实例。
    专门用于生成修复补丁（fix_code_node），确保输出可被 Pydantic 解析。
    
    关键点：使用 bind() 方法绑定 response_format，而不是在 invoke() 中传入。
    """
    llm = get_llm()
    # DeepSeek 支持 OpenAI 的 response_format 参数
    # LangChain 的 bind 方法可以将额外参数永久绑定到调用中
    structured_llm = llm.bind(response_format={"type": "json_object"})
    logger.debug("已启用 JSON 输出模式（用于修复补丁生成）")
    return structured_llm