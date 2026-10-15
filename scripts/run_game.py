import asyncio
from src.engine.config_loader import load_config
from src.engine.manager import GameManager


config = load_config("configs/game.yaml")
game_manager = GameManager(config)
asyncio.run(game_manager.run())

print(f"游戏结束！胜者: {game_manager.state.winner}")