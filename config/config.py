from pydantic_settings import BaseSettings
from sqlmodel import create_engine, Session
from typing import Generator


class Settings(BaseSettings):
    app_name: str = "Awesome API"
    admin_email: str
    items_per_user: int = 50

    database_url: str = "mysql+pymysql://root:mypassword@127.0.0.1/test2"
    database_echo: bool = True

    feishu_webhook_base_url: str = "https://open.feishu.cn/open-apis/bot/v2/hook/"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

engine = create_engine(settings.database_url, echo=settings.database_echo)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
