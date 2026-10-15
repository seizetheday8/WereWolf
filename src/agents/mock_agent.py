import random
from src.engine.actions import Action,ActionType
from src.engine.state import GameState, Phase, Role


class MockAgent:
    def __init__(self, player_id: int):
        self.player_id = player_id
    
    async def decide(self,state:GameState) -> Action:
        """
        根据当前游戏阶段和角色，随机选一个合法行动
        """

        if state.phase == Phase.NIGHT:
            player = state.get_player(self.player_id)
            if player.role == Role.WEREWOLF:
                # 狼人夜晚行动：随机选择一个目标（不能是自己）
                targets = [p for p in state.get_alive_players() if p.player_id != self.player_id and not p.is_wolf]
                if targets:
                    target = random.choice(targets)
                    return Action(player_id=self.player_id,action_type=ActionType.KILL , target_id=target.player_id)
            elif player.role == Role.SEER:
                # 预言家夜晚行动：随机选择一个目标查验
                targets = [p for p in state.get_alive_players() if p.player_id != self.player_id]
                if targets:
                    target = random.choice(targets)
                    return Action(player_id=self.player_id,action_type=ActionType.CHECK,target_id=target.player_id)
            elif player.role == Role.WITCH:
                # 女巫夜晚行动：如果有解药,50%概率救被狼人杀的；如果不救，有毒药，50%概率随机选择一个目标毒死（不能是自己）;或者空过
                if player.has_antidote:
                    if random.random() < 0.5:
                        return Action(player_id=self.player_id,action_type=ActionType.SAVE,target_id=state.night_killed_player_id)
                if player.has_poison:
                    if random.random() < 0.5:
                        targets = [p for p in state.get_alive_players() if p.player_id != self.player_id]
                        if targets:
                            target = random.choice(targets)
                            return Action(player_id=self.player_id,action_type=ActionType.POISON,target_id=target.player_id)
                return Action(player_id=self.player_id,action_type=ActionType.NOTHING)
        # 白天行动：随机发言或投票
        elif state.phase == Phase.DAY_DISCUSS:
            if random.random() < 0.5:
                targets = [p for p in state.get_alive_players() if p.player_id != self.player_id]
                if targets:
                    target = random.choice(targets)
                    return Action(player_id=self.player_id,action_type=ActionType.SPEAK,speech_content=f"我觉得玩家{target.player_id}可疑")
            else:
                return Action(player_id=self.player_id,action_type=ActionType.ABSTAIN)
        elif state.phase == Phase.DAY_VOTE:
            targets = [p for p in state.get_alive_players() if p.player_id != self.player_id]
            if targets:
                target = random.choice(targets)
                return Action(player_id=self.player_id,action_type=ActionType.VOTE,target_id=target.player_id)
        elif state.phase == Phase.HUNTER_TRIGGER:
            if random.random() < 0.5:
                targets = [p for p in state.get_alive_players() if p.player_id != self.player_id]
                if targets:
                    target = random.choice(targets)
                    return Action(player_id=self.player_id,action_type=ActionType.SHOOT,target_id=target.player_id)
            return Action(player_id=self.player_id,action_type=ActionType.NOTHING)
        return Action(player_id=self.player_id,action_type=ActionType.NOTHING)