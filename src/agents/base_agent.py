from src.llm.provider import LLMProvider
from src.comm.info_filter import PlayerView
from src.engine.state import GameState, Player, Role, Phase
from src.engine.actions import Action, ActionType
import json


class BaseAgent:
    def __init__(self, player_id: int, llm: LLMProvider,system_prompt: str):
        self.player_id = player_id
        self.llm = llm
        self.system_prompt = system_prompt
        self.memory:list[dict] = [] # 记忆历史对话和事件，供后续决策使用

    async def decide(self, view: PlayerView) -> Action:
        # 当前view存进记忆
        self.memory.append({
            "role": "user",
            "content": json.dumps(view.__dict__,ensure_ascii=False,default=str)
        })
        if len(self.memory) > 20:  # 限制记忆长度，避免过长
            self.memory = self.memory[-20:]
        # 拼接完整消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.memory,
        ]
        for attempt in range(3):  # 最多重试3次
            # 调用LLM生成决策
            try:
                # 解析决策
                data = await self.llm.chat_json(messages)
                # 校验
                target_id = data.get("target_id")
                if isinstance(target_id, str) and target_id.isdigit():
                    target_id = int(target_id)
                if not isinstance(target_id, int) or target_id < 1 or target_id > 8:
                    target_id = None  # 无效目标ID，置空

                # 将决策存进记忆
                self.memory.append({
                    "role": "assistant",
                    "content": data.get("thought", "")
                })
                # 返回Action对象
                return Action(
                    player_id=self.player_id,
                    action_type=ActionType(data["action"]),
                    target_id=target_id,
                    speech_content=data.get("speech_content")
                )
            # 超过重试次数，返回默认行动
            except Exception as e:
                if attempt < 2:
                    messages.append({
                        "role": "user",
                        "content": f"你的回答无法解析为JSON，请严格按照格式要求回答。错误详情: {str(e)}"
                    })
                else:
                    return Action(player_id=self.player_id, action_type=ActionType.NOTHING)
        return Action(player_id=self.player_id, action_type=ActionType.NOTHING)