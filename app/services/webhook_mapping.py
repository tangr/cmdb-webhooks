from typing import Dict, Optional
import yaml
import os


# Global webhook mapping storage
_webhook_mapping: Dict[str, str] = {}


def load_webhook_mapping() -> Dict[str, str]:
    """Load webhook ID to name mapping from YAML file"""
    config_path = os.path.join(
        os.path.dirname(__file__), "../../config/webhook_mapping.yaml"
    )

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
