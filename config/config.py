from pydantic_settings import BaseSettings
from sqlmodel import create_engine, Session
from typing import Generator, Dict, Optional
import yaml
import os


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

# Global webhook mapping storage
_webhook_mapping: Dict[str, str] = {}


def load_webhook_mapping() -> Dict[str, str]:
    """Load webhook ID to name mapping from YAML file"""
    config_path = os.path.join(os.path.dirname(__file__), "webhook_mapping.yaml")

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            return config.get("webhooks", {})
    except FileNotFoundError:
        print(f"Warning: Webhook mapping file not found at {config_path}")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing webhook mapping YAML: {e}")
        return {}


def init_webhook_mapping():
    """Initialize webhook mapping on startup"""
    global _webhook_mapping
    _webhook_mapping = load_webhook_mapping()
    print(f"Loaded {len(_webhook_mapping)} webhook mappings")


def get_webhook_id_by_name(webhook_name: str) -> Optional[str]:
    """Get webhook ID by webhook name"""
    # Create reverse mapping (name -> id)
    name_to_id = {name: webhook_id for webhook_id, name in _webhook_mapping.items()}
    return name_to_id.get(webhook_name)


def get_webhook_name_by_id(webhook_id: str) -> Optional[str]:
    """Get webhook name by webhook ID"""
    return _webhook_mapping.get(webhook_id)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
