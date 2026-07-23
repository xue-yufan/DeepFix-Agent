"""
文件名: patch.py
核心作用: 定义 Agent 与 AI 模型之间的"数据契约"（Data Contract）。

详细解释:
1. 为什么需要这个文件？
   DeepSeek 模型输出的是自然语言或 JSON 字符串，而我们的 Python 程序需要具体的
   file_path（改哪个文件）、search（找哪段旧代码）、replace（改成什么新代码）。
   这个文件就是强制规定 AI 必须按照这个"标准格式"回复。

2. 它解决了什么问题？
   - 防止 AI 输出废话（如："我建议你修改第5行..."），确保输出可被程序直接执行。
   - 利用 Pydantic 库做类型校验。如果 AI 漏掉字段或填错类型，程序会立刻报错，
     绝不把脏数据传给文件系统，避免改坏代码。

3. 在项目中的位置（谁在用这个文件）？
   - src/graph/nodes.py（核心逻辑）: 会调用这个模型来解析 DeepSeek 的返回结果。
   - src/tools/file_ops.py（工具层）: 会根据这个模型里的 search 和 replace 字段
     去真实地修改磁盘上的代码文件。
"""
from pydantic import BaseModel, Field
from typing import Optional

class SearchReplacePatch(BaseModel):
    """强制LLM输出的修复补丁结构"""
    file_path: str = Field(..., description="需要修改的文件路径")
    search: str = Field(..., description="需要被替换的原始代码块（必须逐字匹配，否则替换失败）")
    replace: str = Field(..., description="替换后的新代码块")
    description: Optional[str] = Field(None, description="本次修复的简要说明（仅供日志记录）")