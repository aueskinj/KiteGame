class GameEntity:
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        
    def update(self, dt: float) -> None:
        """Update entity state based on time delta."""
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        
    def render(self) -> dict:
        """Return render data for client."""
        return {
            'type': self.__class__.__name__.lower(),
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height
        }
        
    def check_collision(self, other: 'GameEntity') -> bool:
        """Basic AABB collision detection."""
        return (
            self.x < other.x + other.width and
            self.x + self.width > other.x and
            self.y < other.y + other.height and
            self.y + self.height > other.y
        )