import os
import json
import logging


def load_prompts(path="data/prompt.json"):
    with open(path, "r", encoding="UTF-8") as f:
        try:
            data = json.load(f)
        except FileNotFoundError:
            logging.error("Failed to load prompts")
            return None
        for k, v in data.items():
            os.environ[str(k).upper()] = str(v)


def load_ui(path):
    return os.path.join("assets/ui", path)
