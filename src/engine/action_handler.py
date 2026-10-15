from src.engine.state import GameState
from src.engine.actions import Action,ActionType

class ActionHandler:

    def execute(self,state:GameState,action:Action) -> dict:
        """
        执行一个动作,返回执行结果(供InfoFilter使用)
        """
        player = state.get_player(action.player_id)
        assert player is not None
        target_player = state.get_player(action.target_id) if action.target_id is not None else None
        result = {"action_type": action.action_type.value}
        # 狼人杀人不既死亡，等夜晚结束统一处理死亡逻辑
        if action.action_type == action.action_type.KILL:
            assert target_player is not None
            state.night_killed_player_id = target_player.player_id
        elif action.action_type == action.action_type.CHECK:
            assert target_player is not None
            player.seer_history[target_player.player_id] = target_player.role.value
            # 返回查验信息
            result["target_role"] = target_player.role.value
        # 女巫救人
        elif action.action_type == action.action_type.SAVE:
            player.has_antidote = False
            state.night_killed_player_id = None
        # 女巫毒人，立即生效
        elif action.action_type == action.action_type.POISON:
            assert target_player is not None
            player.has_poison = False
            state.night_poisoned_player_id = target_player.player_id
            target_player.alive = False
            state.alive_players.remove(target_player.player_id)
            state.dead_players.append(target_player.player_id)
        elif action.action_type == action.action_type.NOTHING:
            pass
        elif action.action_type == action.action_type.SPEAK:
            assert action.speech_content is not None
            state.speeches.append((player.player_id, action.speech_content))
        elif action.action_type == action.action_type.VOTE:
            assert target_player is not None
            state.votes[player.player_id] = target_player.player_id
        elif action.action_type == action.action_type.ABSTAIN:
            pass
        # 猎人开枪，立即生效
        elif action.action_type == action.action_type.SHOOT:
            assert target_player is not None
            target_player.alive = False
            state.alive_players.remove(target_player.player_id)
            state.dead_players.append(target_player.player_id)
        return result
              

