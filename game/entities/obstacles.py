import random
from .base import GameEntity

class Obstacle(GameEntity):
    def __init__(self, x: float, y: float, width: float, height: float):
        super().__init__(x, y, width, height)
        
class Rock(Obstacle):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, width=30, height=30)
        
class PalmTree(Obstacle):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, width=40, height=60)
        
class Wave(Obstacle):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, width=80, height=20)
        self.speed = random.uniform(50, 100)
        self.distance = random.uniform(100, 200)
        self.origin_x = x
        
    def update(self, dt: float) -> None:
        """Move wave back and forth."""
        self.x = self.origin_x + self.distance * \
                 (0.5 + 0.5 * (self.x / self.distance % 1.0))
        super().update(dt)