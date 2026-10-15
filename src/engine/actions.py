from dataclasses import dataclass

from src.engine.state import GameState, Phase, Player, Role
from typing import Optional
from enum import Enum

class ActionType(str, Enum):
    # 夜晚行动
    KILL = "kill" # 狼人杀人
    WHISPER = "whisper" # 狼人私聊
    CHECK = "check" # 预言家查验
    NOTHING = "nothing" # 无行动
    SAVE = "save" # 女巫救人
    POISON = "poison" # 女巫毒人
    # 白天行动
    SPEAK = "speak" # 发言
    # 投票行动
    VOTE = "vote" # 投票
    ABSTAIN = "abstain" # 放弃投票
    # 猎人行动
    SHOOT = "shoot"  # 猎人开枪

@dataclass
class Action:
    player_id: int
    action_type: ActionType
    target_id: Optional[int] = None
    speech_content:Optional[str] = None

def validate_action(game_state: GameState, action: Action)-> tuple[bool, str]:
    """
    验证玩家的行动是否合法。
    """
    try:
        player = game_state.get_player(action.player_id)
    except KeyError:
        return False, "无效的玩家ID"

    try:    
        if game_state.phase == Phase.NIGHT:
            if player.role == Role.WEREWOLF and action.action_type == ActionType.KILL:
                if action.target_id is None:
                    return False, "狼人必须指定一个目标进行杀人"
                else:
                    target_player = game_state.get_player(action.target_id)
                    if not target_player.alive:
                        return False, "目标玩家已死亡"
                    elif target_player.player_id == player.player_id:
                        return False, "狼人不能攻击自己"
                    else:
                        return True, ""
            elif player.role == Role.SEER and action.action_type == ActionType.CHECK:
                if action.target_id is None:
                    return False, "预言家必须指定一个目标进行查验"
                else:
                    target_player = game_state.get_player(action.target_id)
                    if not target_player.alive:
                        return False, "目标玩家已死亡"
                    elif target_player.player_id == player.player_id:
                        return False, "预言家不能查验自己"
                    else:
                        return True, ""
            elif player.role == Role.WITCH:
                if action.action_type == ActionType.SAVE:
                    if not player.has_antidote:
                        return False, "女巫没有解药了"
                    elif action.target_id is None:
                        return False, "女巫必须指定一个目标进行救人"
                    elif action.target_id != game_state.night_killed_player_id:
                        return False, "女巫只能救被狼人杀死的玩家"
                    else:
                        return True, ""
                elif action.action_type == ActionType.POISON:
                    if not player.has_poison:
                        return False, "女巫没有毒药了"
                    elif action.target_id is None:
                        return False, "女巫必须指定一个目标进行毒人"
                    elif action.target_id == player.player_id:
                        return False, "女巫不能毒自己"
                    else:
                        target_player = game_state.get_player(action.target_id)
                        if not target_player.alive:
                            return False, "目标玩家已死亡"
                        else:
                            return True, ""
                elif action.action_type == ActionType.NOTHING:
                    return True, ""
                else:
                    return False, "女巫在夜晚只能选择救人、毒人或无行动"
            else:
                return False, "其他角色在夜晚不能执行任何行动"
        elif game_state.phase == Phase.HUNTER_TRIGGER:
            if player.role == Role.HUNTER and action.action_type == ActionType.SHOOT:
                if action.target_id is None:
                    return False, "猎人必须指定一个目标进行开枪"
                elif action.target_id == player.player_id:
                    return False, "猎人不能开枪射击自己"
                else:
                    target_player = game_state.get_player(action.target_id)
                    if not target_player.alive:
                        return False, "目标玩家已死亡"
                    else:
                        return True, ""
            elif player.role == Role.HUNTER and action.action_type == ActionType.NOTHING:
                return True, ""
            else:
                return False, "非猎人角色在猎人触发阶段不能执行任何行动"
        elif game_state.phase == Phase.DAY_DISCUSS:
            if action.action_type == ActionType.SPEAK:
                return True, ""
            elif action.action_type == ActionType.ABSTAIN:
                return True, ""
            else:
                return False, "在讨论阶段只能选择发言"
        elif game_state.phase == Phase.DAY_VOTE:
            if action.action_type == ActionType.VOTE:
                if action.target_id is None:
                    return False, "投票必须指定一个目标"
                elif action.target_id == player.player_id:
                    return False, "玩家不能投票给自己"
                else:
                    target_player = game_state.get_player(action.target_id)
                    if not target_player.alive:
                        return False, "目标玩家已死亡"
                    else:
                        return True, ""
            elif action.action_type == ActionType.ABSTAIN:
                return True, ""
            else:
                return False, "在投票阶段只能选择投票或放弃投票"
        return False, "无效的行动类型"
    except KeyError:
        return False, "无效的目标玩家ID"