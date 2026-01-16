from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from utility.observability.logger import get_logger


class BaseAgent(ABC):

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(name)
        self.logger.info("agent_initialized", agent=name)

    @abstractmethod
    def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

    def _create_response(
        self,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = {"agent": self.name, "timestamp": datetime.utcnow().isoformat()}

        if extra_metadata:
            metadata.update(extra_metadata)

        return {
            "success": success,
            "result": result,
            "error": error,
            "metadata": metadata,
        }

    def _handle_error(self, error: Exception, query: str) -> Dict[str, Any]:
        self.logger.error(
            "agent_execution_failed",
            agent=self.name,
            query=query[:100],
            error=str(error),
            error_type=type(error).__name__,
        )

        return self._create_response(
            success=False, error=f"{self.name} failed: {str(error)}"
        )
