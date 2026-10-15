from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from src.engine.state import Phase

# 事件类型常量
class EventType(str, Enum):
    GAME_STARTED = "game_started"
    PHASE_CHANGED = "phase_changed"
    PLAYER_ABSTAINED = "player_abstained"
    PLAYER_DIED = "player_died"
    PLAYER_KILLED = "player_killed"
    PLAYER_POISONED = "player_poisoned"
    PLAYER_SAVED = "player_saved"
    PLAYER_VOTED_OUT = "player_voted_out"
    PLAYER_SHOT = "player_shot"
    ACTION_EXECUTED = "action_executed"
    SPEECH_MADE = "speech_made"
    VOTE_CAST = "vote_cast"
    VOTE_RESULT = "vote_result"
    GAME_ENDED = "game_ended"


@dataclass
class GameEvent:
    event_type: str
    game_id:str
    round: int
    phase: Phase
    data:dict

class EventBus:

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self,event_type:str, callback:Callable):
        """
        订阅特定类型的事件，当事件发生时调用回调函数。
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def subscribe_all(self, callback:Callable):
        """
        订阅所有类型的事件。
        """
        if "__all__" not in self._subscribers:
            self._subscribers["__all__"] = []
        self._subscribers["__all__"].append(callback)

    def unsubscribe(self,event_type:str, callback:Callable):
        """
        取消订阅特定类型的事件。
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    def publish(self, event:GameEvent):
        """
        发布事件，通知所有订阅了该事件类型的回调函数。
        """
        for callback in self._subscribers.get(event.event_type, []):
            callback(event)
        for callback in self._subscribers.get("__all__", []):
            callback(event)