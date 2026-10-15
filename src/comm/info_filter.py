from dataclasses import dataclass
from src.engine.state import GameState, Player, Role, Phase

@dataclass
class PlayerView:
    player_id: int
    role: Role
    phase: Phase
    round: int
    alive_players: set[int]
    recent_speeches: list[dict]
    dead_history: list[int]
    my_info: dict
    
class InfoFilter:
    def build_view(self,state: GameState, player:Player)->PlayerView:
        # 1.公屏信息
        view = PlayerView(
            player_id=player.player_id,
            role=player.role,
            phase=state.phase,
            round=state.round,
            alive_players=state.alive_players,
            recent_speeches=[{"player_id": pid, "content": content} for pid, content in state.speeches[-16:]],
            dead_history=state.dead_players,
            my_info={}
        )
        # 2.私屏信息
        if player.role == Role.WITCH:
            view.my_info["has_antidote"] = player.has_antidote
            view.my_info["has_poison"] = player.has_poison
            if state.night_killed_player_id:
                view.my_info["night_killed"] = state.night_killed_player_id
            if state.night_poisoned_player_id:
                view.my_info["night_poisoned"] = state.night_poisoned_player_id
        elif player.role == Role.SEER:
            view.my_info["seer_history"] = player.seer_history
        elif player.role == Role.WEREWOLF:
            wolves = state.get_players_by_role(Role.WEREWOLF)
            view.my_info["wolf_team"] = [w.player_id for w in wolves if w.player_id != player.player_id]
            view.my_info["wolf_whispers"] = state.wolf_whispers
        
        return view
