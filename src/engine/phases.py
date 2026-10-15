from src.engine.state import GameState, Phase, Role


def next_phase(state:GameState) -> Phase:
    if state.phase == Phase.NIGHT:
        # 如果被刀的人是猎人，进入猎人触发阶段，否则进入白天讨论阶段
        if state.night_killed_player_id and state.get_player(state.night_killed_player_id).role == Role.HUNTER:
            return Phase.HUNTER_TRIGGER
        return Phase.DAY_DISCUSS
    elif state.phase == Phase.DAY_DISCUSS:
        return Phase.DAY_VOTE
    elif state.phase == Phase.DAY_VOTE:
        # 如果被投出的人是猎人，进入猎人触发阶段，否则进入下一轮夜晚
        if state.vote_out_player_id and state.get_player(state.vote_out_player_id).role == Role.HUNTER:
            return Phase.HUNTER_TRIGGER
        return Phase.NIGHT
    elif state.phase == Phase.HUNTER_TRIGGER:
        return Phase.NIGHT
    else:
        return Phase.GAME_END
