import threading
from typing import Optional, List
from core.storage.embedding.embedding_model import EmbeddingModel
from utility.observability.logger import get_logger

logger = get_logger("embedding_manager")


class EmbeddingModelManager:
    """
    Thread-safe singleton manager for the embedding model.

    Ensures the model is loaded only once across the entire application,
    eliminating the 7-second delay on every vector search operation.

    Usage:
        model = EmbeddingModelManager.get_instance()
        embeddings = model.encode_single("query text")
    """

    _instance: Optional[EmbeddingModel] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> EmbeddingModel:
        """
        Get the singleton embedding model instance.

        Thread-safe lazy initialization - loads model on first call,
        returns cached instance on subsequent calls.

        Returns:
            EmbeddingModel: The singleton embedding model instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check pattern for thread safety
                if cls._instance is None:
                    logger.info("embedding_model_singleton_initializing")
                    cls._instance = EmbeddingModel()
                    logger.info("embedding_model_singleton_ready")

        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance (useful for testing).

        WARNING: Only use this for testing purposes.
        """
        with cls._lock:
            cls._instance = None
            logger.warning("embedding_model_singleton_reset")
