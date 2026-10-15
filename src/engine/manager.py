from src.comm.info_filter import InfoFilter
from src.engine.state import GameConfig, Phase, Player, Role
from src.agents.mock_agent import MockAgent
from src.engine.action_handler import ActionHandler
from src.engine.actions import Action, ActionType, validate_action
from src.engine.game_factory import create_game
from src.engine.events import EventBus, GameEvent, EventType
from src.engine.win_checker import check_win_condition
from src.engine.phases import next_phase
from src.agents.base_agent import BaseAgent
from src.llm.provider import LLMProvider
from collections import Counter
from src.observability.logger import GameLogger
from src.utils.prompt_loader import load_prompt

PROMPT_MAP = {
    Role.SEER: "src/prompts/seer.yaml",
    Role.WITCH: "src/prompts/witch.yaml",
    Role.HUNTER: "src/prompts/hunter.yaml",
    Role.VILLAGER: "src/prompts/villager.yaml",
    Role.WEREWOLF: "src/prompts/werewolf.yaml"
}

class GameManager:
    def __init__(self,config:GameConfig):
        self.state = create_game(config)
        self.llm_provider = LLMProvider(model=None, api_key=None, base_url=None)  # 使用环境变量配置LLM

        self.agents: dict[int, BaseAgent] = {}
        for p in self.state.players:
            self.agents[p.player_id] = BaseAgent(
                player_id=p.player_id,
                llm=self.llm_provider,
                system_prompt = load_prompt(PROMPT_MAP[p.role]),
            )
        
        self.info_filter = InfoFilter()
        self.handler = ActionHandler()
        self.event_bus = EventBus()
        self.logger = GameLogger(self.event_bus,self.state.game_id)

    async def run(self):

        print("========== 游戏开始 ==========")
        for p in self.state.players:
            print(f"座位{p.seat_number}: {p.name} — {p.role}")


        while self.state.phase != Phase.GAME_END:

            print(f"\n--- 第{self.state.round}轮 {self.state.phase} ---")
            print(f"存活: {[p.name for p in self.state.get_alive_players()]}")


            if self.state.phase == Phase.NIGHT:
                await self._run_night()
            elif self.state.phase == Phase.DAY_DISCUSS:
                await self._run_day_discuss()
            elif self.state.phase == Phase.DAY_VOTE:
                await self._run_day_vote()
            elif self.state.phase == Phase.HUNTER_TRIGGER:
                await self._run_hunter_trigger()

            # 判断游戏是否结束
            winner = check_win_condition(self.state)
            if winner:
                self.state.winner = winner
                self.state.phase = Phase.GAME_END
                break

            # 进入下一阶段
            self.state.phase = next_phase(self.state)
        self.logger.save()

    async def _run_night(self):

        self.state.round += 1

        # 夜晚开始前重置夜晚相关状态
        self.state.wolf_whispers.clear()
        self.state.night_killed_player_id = None
        self.state.night_poisoned_player_id = None

        alive_players = self.state.get_alive_players()

        # 第一步:狼人行动
        wolfs = self.state.get_players_by_role(Role.WEREWOLF)
        wolfs = [w for w in wolfs if w.alive]
        
        if wolfs:
            target_id = None
            targets = {}

            for attempt in range(3):  # 最多协商3轮
                targets.clear()
                for wolf in wolfs:
                    agent = self.agents[wolf.player_id]
                    view = self.info_filter.build_view(self.state, wolf)
                    action = None
                    ok = False
                    for _ in range(3):  # 最多尝试3次
                        action = await agent.decide(view)
                        ok, res = validate_action(self.state, action)
                        if not ok:
                            print(f"狼人玩家ID {wolf.player_id} 的行动无效: {res}，尝试重新选择")
                            view.my_info['last_error'] = res  # 将错误信息传递给代理
                        else:
                            print(f"狼人玩家ID {wolf.player_id} 选择了杀玩家ID {action.target_id}，私聊内容: {action.speech_content}")
                            self.state.wolf_whispers.append((wolf.player_id, action.speech_content, action.target_id))
                            self.event_bus.publish(GameEvent(
                                event_type=EventType.ACTION_EXECUTED,
                                game_id=self.state.game_id,
                                round=self.state.round,
                                phase=Phase.NIGHT,
                                data={
                                    "player_id": wolf.player_id,
                                    "role": "werewolf",
                                    "action":"kill",
                                    "target_id": action.target_id,
                                    "speech_content": action.speech_content
                                }
                            ))
                            targets[wolf.player_id] = action.target_id
                            break
                    if not ok:
                        print(f"狼人玩家ID {wolf.player_id} 在第{attempt+1}轮协商中未能做出有效选择，默认选择不行动")

                valid = [t for t in targets.values() if t is not None]
                if valid and len(set(valid)) == 1:  # 所有狼人达成一致
                    target_id = next(iter(set(valid)))
                    break
            if target_id is None:
                from collections import Counter
                cnt = Counter([t for t in targets.values() if t is not None])
                if cnt:
                    most_common = cnt.most_common(1)[0][0]
                    target_id = most_common
                    print(f"狼人未达成一致，默认选择了玩家ID {target_id} 作为目标")

            if target_id:
                action = Action(player_id=wolfs[0].player_id, action_type=ActionType.KILL, target_id=target_id)
                ok, _ = validate_action(self.state, action)
                if ok:
                    self.handler.execute(self.state, action)
                    print(f"狼人最终选择杀死玩家ID {action.target_id}")
                    self.event_bus.publish(GameEvent(
                        event_type=EventType.ACTION_EXECUTED,
                        game_id=self.state.game_id,
                        round=self.state.round,
                        phase=Phase.NIGHT,
                        data={
                            "player_id": wolfs[0].player_id,
                            "role": "werewolf",
                            "action":"kill",
                            "target_id": action.target_id
                        }
                    ))

        # 第二步:预言家行动
        seer = [p for p in alive_players if p.role == Role.SEER]
        if seer:
            seer = seer[0]
            agent = self.agents[seer.player_id]
            view = self.info_filter.build_view(self.state, seer)
            action = None
            ok = False
            for _ in range(3):  # 最多尝试3次
                action = await agent.decide(view)
                ok, res = validate_action(self.state, action)
                if not ok:
                    print(f"预言家玩家ID {seer.player_id} 的查验行动无效: {res}，尝试重新查验")
                    view.my_info['last_error'] = res  # 将错误信息传递给代理
                else:
                    target_role = self.handler.execute(self.state, action)["target_role"]
                    print(f"预言家查验了玩家ID {action.target_id}，角色是 {target_role}")
                    self.event_bus.publish(GameEvent(
                        event_type=EventType.ACTION_EXECUTED,
                        game_id=self.state.game_id,
                        round=self.state.round,
                        phase=Phase.NIGHT,
                        data={
                            "player_id": seer.player_id,
                            "role": "seer",
                            "action":"check",
                            "target_id": action.target_id,
                            "target_role": target_role
                        }
                    ))
                    break
            if not ok:
                print(f"预言家玩家ID {seer.player_id} 在夜晚未能做出有效行动，默认选择不行动")
        
        # 第三步:女巫行动
        witch = [p for p in alive_players if p.role == Role.WITCH]
        if witch:
            witch = witch[0]
            agent = self.agents[witch.player_id]
            view = self.info_filter.build_view(self.state, witch)
            action = None
            ok = False
            for _ in range(3):  # 最多尝试3次
                action = await agent.decide(view)
                ok, res = validate_action(self.state, action)
                if not ok:
                    print(f"女巫玩家ID {witch.player_id} 的行动无效: {res}，尝试重新行动")
                    view.my_info['last_error'] = res  # 将错误信息传递给代理
                else:
                    self.handler.execute(self.state, action)
                    if action.action_type == ActionType.SAVE:
                        print(f"女巫选择救人，救了玩家ID {action.target_id}")
                        self.event_bus.publish(GameEvent(
                            event_type=EventType.ACTION_EXECUTED,
                            game_id=self.state.game_id,
                            round=self.state.round,
                            phase=Phase.NIGHT,
                            data={
                                "player_id": witch.player_id,
                                "role": "witch",
                                "action":"save",
                                "target_id": action.target_id
                            }
                        ))
                    elif action.action_type == ActionType.POISON:
                        print(f"女巫选择毒人，毒了玩家ID {action.target_id}")
                        self.event_bus.publish(GameEvent(
                            event_type=EventType.ACTION_EXECUTED,
                            game_id=self.state.game_id,
                            round=self.state.round,
                            phase=Phase.NIGHT,
                            data={
                                "player_id": witch.player_id,
                                "role": "witch",
                                "action":"poison",
                                "target_id": action.target_id
                            }
                        ))
                    break
            if not ok:
                print(f"女巫玩家ID {witch.player_id} 在夜晚未能做出有效行动，默认选择不行动")
        
        # 夜晚结算
        died = False
        if self.state.night_killed_player_id is not None:
            killed_player = self.state.get_player(self.state.night_killed_player_id)
            if killed_player.alive: #防止被狼人刀的被女巫毒死了
                killed_player.alive = False
                self.state.alive_players.remove(killed_player.player_id)
                self.state.dead_players.append(killed_player.player_id)
                died = True
                print(f"玩家ID {self.state.night_killed_player_id} 被狼人杀死")
                self.event_bus.publish(GameEvent(
                    event_type=EventType.PLAYER_KILLED,
                    game_id=self.state.game_id,
                    round=self.state.round,
                    phase=Phase.NIGHT,
                    data={
                        "player_id": self.state.night_killed_player_id,
                        "cause": "werewolf"
                    }
                ))
        if self.state.night_poisoned_player_id is not None:
            died = True
            print(f"玩家ID {self.state.night_poisoned_player_id} 被女巫毒死")
            self.event_bus.publish(GameEvent(
                event_type=EventType.PLAYER_POISONED,
                game_id=self.state.game_id,
                round=self.state.round,
                phase=Phase.NIGHT,
                data={
                    "player_id": self.state.night_poisoned_player_id,
                    "cause": "witch"
                }
            ))
        if not died:
            print("夜晚平安无事")              

    async def _run_day_discuss(self):
        alive_players = self.state.get_alive_players()
        for p in alive_players:
            agent = self.agents[p.player_id]
            view = self.info_filter.build_view(self.state, p)
            # 提供上轮的投票结果给玩家
            view.my_info['last_round_votes'] = self.state.votes.copy()
            view.my_info['last_vote_out_player_id'] = self.state.vote_out_player_id
            action = None
            ok = False
            for _ in range(3):  # 最多尝试3次
                action = await agent.decide(view)
                ok, res = validate_action(self.state, action)
                if not ok:
                    print(f"玩家ID {p.player_id} 的发言无效: {res}，尝试重新发言")
                    view.my_info['last_error'] = res  # 将错误信息传递给代理
                else:
                    self.handler.execute(self.state, action)
                    if action.speech_content:
                        print(f"玩家ID {p.player_id} 说了: {action.speech_content}")
                        self.event_bus.publish(GameEvent(
                            event_type=EventType.SPEECH_MADE,
                            game_id=self.state.game_id,
                            round=self.state.round,
                            phase=Phase.DAY_DISCUSS,
                            data={
                                "player_id": p.player_id,
                                "content": action.speech_content
                            }
                        ))
                    else:
                        print(f"玩家ID {p.player_id} 选择了保持沉默")
                    break
            if not ok:
                print(f"玩家ID {p.player_id} 在白天讨论中未能做出有效发言，默认选择保持沉默")

    async def _run_day_vote(self):

        # 重置投票状态
        self.state.votes.clear()
        self.state.vote_out_player_id = None

        alive_players = self.state.get_alive_players()
        for p in alive_players:
            agent = self.agents[p.player_id]
            view = self.info_filter.build_view(self.state, p)
            action = None
            ok = False
            for _ in range(3):  # 最多尝试3次
                action = await agent.decide(view)
                ok, res = validate_action(self.state, action)
                if not ok:
                    print(f"玩家ID {p.player_id} 的投票无效: {res}，尝试重新投票")
                    view.my_info['last_error'] = res  # 将错误信息传递给代理
                else:
                    self.handler.execute(self.state, action)
                    if action.action_type == ActionType.VOTE:
                        print(f"玩家ID {p.player_id} 投票给了玩家ID {action.target_id}")
                        self.event_bus.publish(GameEvent(
                            event_type=EventType.VOTE_CAST,
                            game_id=self.state.game_id,
                            round=self.state.round,
                            phase=Phase.DAY_VOTE,
                            data={
                                "voter_id": p.player_id,
                                "target_id": action.target_id
                            }
                        ))
                    elif action.action_type == ActionType.ABSTAIN:
                        print(f"玩家ID {p.player_id} 选择了弃权投票")
                        self.event_bus.publish(GameEvent(
                            event_type=EventType.PLAYER_ABSTAINED,
                            game_id=self.state.game_id,
                            round=self.state.round,
                            phase=Phase.DAY_VOTE,
                            data={
                                "player_id": p.player_id
                            }
                        ))
                    break
            if not ok:
                print(f"玩家ID {p.player_id} 在白天投票中未能做出有效选择，默认选择弃权投票")
        # 统计投票结果
        cnt = Counter(self.state.votes.values())
        if cnt:
            most_voted = cnt.most_common(2)
            if len(most_voted) == 1 or most_voted[0][1] > most_voted[1][1]:  # 有明确的投票结果
                self.state.vote_out_player_id = most_voted[0][0]
                out_player = self.state.get_player(most_voted[0][0])
                out_player.alive = False
                self.state.alive_players.remove(out_player.player_id)
                self.state.dead_players.append(out_player.player_id)
                print(f"白天结束，玩家ID {self.state.vote_out_player_id} 被投票出局")
                self.event_bus.publish(GameEvent(
                    event_type=EventType.PLAYER_VOTED_OUT,
                    game_id=self.state.game_id,
                    round=self.state.round,
                    phase=Phase.DAY_VOTE,
                    data={
                        "player_id": self.state.vote_out_player_id
                    }
                ))
            else:
                print("白天结束，投票结果平票，没有玩家被投出局")
        else:
            print("白天结束，没有玩家投票，未产生出局玩家")
    async def _run_hunter_trigger(self):
        hunter = next((p for p in self.state.players if p.role == Role.HUNTER), None)
        if hunter:
            agent = self.agents[hunter.player_id]
            view = self.info_filter.build_view(self.state, hunter)
            action = None
            ok = False
            for _ in range(3):  # 最多尝试3次  
                action = await agent.decide(view)
                ok, res = validate_action(self.state, action)
                if ok:
                    self.handler.execute(self.state, action)
                    if action.action_type == ActionType.SHOOT:
                        print(f"猎人触发，玩家ID {hunter.player_id} 开枪，射杀了玩家ID {action.target_id}")
                        self.event_bus.publish(GameEvent(
                            event_type=EventType.PLAYER_SHOT,
                            game_id=self.state.game_id,
                            round=self.state.round,
                            phase=Phase.HUNTER_TRIGGER,
                            data={
                                "player_id": hunter.player_id,
                                "target_id": action.target_id
                            }
                        ))
                    elif action.action_type == ActionType.NOTHING:
                        print(f"猎人触发，玩家ID {hunter.player_id} 选择了不射击")
                    break
                else:
                    print(f"玩家ID {hunter.player_id} 的猎人开枪行动无效，尝试重新选择")
                    view.my_info['last_error'] = res  # 将错误信息传递给代理
            if not ok:
                print(f"猎人玩家ID {hunter.player_id} 在猎人触发阶段未能做出有效行动，默认选择不行动")


