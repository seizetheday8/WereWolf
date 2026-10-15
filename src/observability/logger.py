from src.engine.events import EventBus, GameEvent, EventType
from src.engine.state import GameState, Phase
import json

class GameLogger:
    def __init__(self,event_bus,game_id:str):
        self.events = []
        event_bus.subscribe_all(self._on_event)
        self.game_id = game_id

    def _on_event(self,event:GameEvent):
        self.events.append({
            "event_type": event.event_type,
            "round": event.round,
            "phase": event.phase,
            "data": event.data,
        })
    
    def save(self):
        path = f"data/logs/{self.game_id}.json"
        with open(path,"w",encoding="utf-8") as f:
            json.dump(self.events,f,ensure_ascii=False,indent=2)