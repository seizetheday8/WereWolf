from src.engine.state import GameConfig, GameState, Player, Role
import random
import uuid

def create_game(config:GameConfig)->GameState:
    """
    根据配置创建游戏状态,随机分配角色
    """
    players = []
    roles = []
    for role, count in config.role_counts.items():
        for _ in range(count):
            roles.append(role)
    random.shuffle(roles)
    for i,role in enumerate(roles, start=1):
        player = Player(
            player_id=i,
            name=f"玩家{i}",
            role=role,
            seat_number=i,
        )
        if role == Role.WITCH:
            player.has_antidote = True
            player.has_poison = True
        players.append(player)
    return GameState(players=players, config=config,game_id=str(uuid.uuid4())[:8])