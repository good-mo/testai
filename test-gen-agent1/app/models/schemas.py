# app/models/schemas.py
"""共享 Pydantic 数据模型（从 main.py 迁移）。

各业务域请求体已逐步迁入独立域模型文件：
  case → app/models/case.py、defect → app/models/defect.py、
  apitest → app/models/apitest.py、project → app/models/project.py。
本文件仅保留仍在使用的 ChatRequest（generation 域），
其余历史遗留模型均为死代码，已清理（#608）。
"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    source_code: str = ""
    file_path: str = "demo.py"
    test_type: str = "functional"
    generate_script: bool = True


__all__ = [
    "ChatRequest",
]
