from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
  # Esto debe coincidir con las variables de entorno de tu docker-compose.yml
  POSTGRES_USER: str = "postgres"
  POSTGRES_PASSWORD: str = "cinema_db_api_gateway"
  POSTGRES_DB: str = "cinema_db"
  POSTGRES_HOST: str = "postgres"
  POSTGRES_PORT: int = 5432

  DATABASE_URL: str | None = None

  @model_validator(mode="after")
  def _build_database_url(self) -> "Settings":
    if not self.DATABASE_URL:
      # Construye la URL asíncrona usando asyncpg
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
    return self
  
settings = Settings()