"""核心游戏状态定义。所有模块共享这些数据结构."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import uuid


class Phase(str, Enum):
    NIGHT = "night"
    DAY_DISCUSS = "day_discuss"
    DAY_VOTE = "day_vote"
    HUNTER_TRIGGER = "hunter_trigger"
    GAME_END = "game_end"


class Role(str, Enum):
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    VILLAGER = "villager"


class Faction(str, Enum):
    WEREWOLF = "werewolf"
    VILLAGER = "villager"


ROLE_FACTION: dict[Role, Faction] = {
    Role.WEREWOLF: Faction.WEREWOLF,
    Role.SEER: Faction.VILLAGER,
    Role.WITCH: Faction.VILLAGER,
    Role.HUNTER: Faction.VILLAGER,
    Role.VILLAGER: Faction.VILLAGER,
}


@dataclass
class Player:
    player_id: int
    name: str
    role: Role
    seat_number: int           # 座位号 1~N
    alive: bool = True

    # 女巫专属状态
    has_antidote: bool = False
    has_poison: bool = False

    # 预言家专属：历史查验记录 {target_player_id: role_name}
    seer_history: dict[int, str] = field(default_factory=dict)

    @property
    def faction(self) -> Faction:
        return ROLE_FACTION[self.role]

    @property
    def is_good(self) -> bool:
        return self.faction == Faction.VILLAGER

    @property
    def is_wolf(self) -> bool:
        return self.faction == Faction.WEREWOLF


@dataclass
class GameConfig:
    role_counts: dict[Role, int]
    night_duration: int = 30
    day_discuss_duration: int = 120
    vote_duration: int = 30
    wolf_max_negotiation_rounds: int = 3


@dataclass
class GameState:
    """游戏完整状态。引擎唯一真理源."""

    game_id: str
    players: list[Player]
    config: GameConfig
    phase: Phase = Phase.NIGHT
    round: int = 0
    turn: int = 0              # 全局行动序号，递增

    # 存活与死亡
    alive_players: set[int] = field(default_factory=set)
    dead_players: list[int] = field(default_factory=list)  # 按死亡顺序排列

    # 当晚被刀的人（女巫可见）
    night_killed_player_id: Optional[int] = None

    # 当晚被女巫毒死的人
    night_poisoned_player_id: Optional[int] = None

    # 发言记录: [(player_id, content)]
    speeches: list[tuple[int, str]] = field(default_factory=list)

    # 投票记录: [(voter_id, target_id)]
    votes: dict[int, int] = field(default_factory=dict)

    # 投票投出的人
    vote_out_player_id: Optional[int] = None

    # 狼人私密频道聊天: [(wolf_id, content, target_id)]
    wolf_whispers: list[tuple[int, Optional[str], Optional[int]]] = field(default_factory=list)

    # 夜间行动记录（用于日志和复盘）
    night_actions: list[dict] = field(default_factory=list)

    # 胜者
    winner: Optional[Faction] = None

    # 状态历史快照（供复盘使用）
    phase_history: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.alive_players:
            self.alive_players = {p.player_id for p in self.players if p.alive}

    def get_player(self, player_id: int) -> Player:
        for p in self.players:
            if p.player_id == player_id:
                return p
        raise KeyError(f"Player {player_id} not found")

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def get_players_by_role(self, role: Role) -> list[Player]:
        return [p for p in self.players if p.role == role]

    def get_players_by_faction(self, faction: Faction) -> list[Player]:
        return [p for p in self.players if p.faction == faction]
