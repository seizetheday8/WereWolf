import yaml

def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return raw["system"]