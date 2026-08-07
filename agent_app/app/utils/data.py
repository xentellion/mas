import os
import logging

import yaml


def load_prompts(path: str = "data/prompt_data.yaml") -> dict[str, str]:
    try:
        with open(path, "r", encoding="UTF-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logging.error(f"Error loading prompts:\n{e}")
        return {}


def load_ui(path):
    return os.path.join("assets/ui", path)
