# TestHealer: AI-Powered Python Code Auto-Fixer

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://langchain-ai.github.io/langgraph/)

**TestHealer** is an intelligent agent that automatically generates unit tests, detects bugs in Python code, and fixes them using **DeepSeek** large language model. It supports both **iterative function-by-function repair** and **full-file rewrite** (like Claude Code).

## 🚀 Features

- 🔍 Automatically extract functions from Python files
- 🧪 Generate comprehensive `pytest` test suites
- 🔧 Fix bugs iteratively or rewrite the entire file at once
- 💾 Persistent checkpoint for resume after interruption
- 📁 Isolated output directory (`test/`) – original file unchanged
- 🧠 Supports DeepSeek API with JSON mode for structured fixes

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/testhealer.git
cd testhealer

# Install with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
