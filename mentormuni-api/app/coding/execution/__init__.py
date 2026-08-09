"""Isolated code execution (Judge0 via CodeExecutionService)."""

from app.coding.execution.factory import get_code_execution_service
from app.coding.execution.service import CodeExecutionService

__all__ = ["CodeExecutionService", "get_code_execution_service"]
