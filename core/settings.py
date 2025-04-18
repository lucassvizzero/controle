import os

SECRET_KEY = os.getenv("SECRET_KEY", "seu_segredo_super_seguro")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "360"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secret@postgres:5432/finance")
