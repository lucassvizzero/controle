import logging
import os

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "seu_segredo_super_seguro")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "360"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secret@postgres:5432/finance")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if SECRET_KEY == "seu_segredo_super_seguro":
    logger.warning(
        "SECRET_KEY está com o valor padrão inseguro. "
        "Defina a variável de ambiente SECRET_KEY antes de usar em produção."
    )
