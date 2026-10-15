import yaml
from src.engine.state import GameConfig,Role

def load_config(path:str) -> GameConfig:
    with open(path,"r",encoding="utf-8") as f:
        raw = yaml.safe_load(f)
        role_counts = {}
        role_map = {
            "villager": Role.VILLAGER,
            "werewolf": Role.WEREWOLF,
            "seer": Role.SEER,
            "witch": Role.WITCH,
            "hunter": Role.HUNTER,
        }
        for role_name,count in raw["game"]["roles"].items():
            role_counts[role_map[role_name]] = count
        
        return GameConfig(
            role_counts=role_counts,
        )