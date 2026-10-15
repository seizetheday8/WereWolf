from src.engine.state import Faction, GameState
from typing import Optional


def check_win_condition(game_state: GameState) -> Optional[Faction]:
    """
    检查游戏是否结束，返回获胜方 "werewolf" 或 "villager"，如果游戏未结束则返回 None。
    """
    alive_players = [p for p in game_state.players if p.alive]
    wolf_count = 0
    villager_count = 0
    for p in alive_players:
        if p.is_wolf:
            wolf_count += 1
        elif p.is_good:
            villager_count += 1
    # alive_wolves = [p for p in alive_players if p.is_wolf]
    # alive_villagers = [p for p in alive_players if p.is_good]

    if not wolf_count:
        return Faction.VILLAGER
    elif wolf_count >= villager_count:
        return Faction.WEREWOLF
    else:
        return None