from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    app_env: str = "development"
    firebase_credentials_path: str

    class Config():
        env_file = ".env"

settings = Settings()