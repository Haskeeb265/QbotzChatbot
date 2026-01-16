from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np
from utility.observability.logger import get_logger
from config.settings import settings

logger = get_logger("embedding_model")


class EmbeddingModel:

    def __init__(self):
        logger.info("model_loading", model=settings.EMBEDDING_MODEL)
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self._verify_dimensions()

        logger.info(
            "model_loaded",
            model=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )

    def _verify_dimensions(self):
        """Ensure model output matches database schema"""
        test_embedding = self.model.encode("test")
        actual_dim = len(test_embedding)

        if actual_dim != settings.EMBEDDING_DIMENSION:
            logger.error(
                "dimension_mismatch",
                expected=settings.EMBEDDING_DIMENSION,
                actual=actual_dim,
            )
            raise ValueError(
                f"Model outputs {actual_dim} dims, "
                f"config expects {settings.EMBEDDING_DIMENSION}"
            )

    def encode_single(self, text: str) -> List[float]:

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error("encoding_failed", text=text[:100], error=str(e))
            raise

    def encode_batch(self, texts: List[str]) -> List[List[float]]:

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                show_progress_bar=True,
                convert_to_numpy=True,
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error("batch_encoding_failed", count=len(texts), error=str(e))
            raise
