from typing import Dict, Set
from .base import GameEntity

class BeachBuggy(GameEntity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, width=40, height=60)
        self.speed = 200.0  # pixels per second
        self.acceleration = 400.0  # pixels per second squared
        self.max_speed = 400.0
        self.rotation = 0.0  # degrees
        self.turn_speed = 180.0  # degrees per second
        self.is_shielded = False
        self.boost_time = 0.0
        
    def handle_input(self, keys: Set[str], dt: float) -> None:
        """Process keyboard input."""
        # Acceleration
        if 'ArrowUp' in keys:
            self._accelerate(dt)
        elif 'ArrowDown' in keys:
            self._accelerate(-dt * 0.5)  # Slower reverse speed
            
        # Turning
        if 'ArrowLeft' in keys:
            self.rotation -= self.turn_speed * dt
        if 'ArrowRight' in keys:
            self.rotation += self.turn_speed * dt
            
        # Normalize rotation to 0-360 degrees
        self.rotation = self.rotation % 360
        
    def _accelerate(self, dt: float) -> None:
        """Apply acceleration in current direction."""
        import math
        rad = math.radians(self.rotation)
        
        # Update velocities based on rotation
        self.velocity_x += math.sin(rad) * self.acceleration * dt
        self.velocity_y -= math.cos(rad) * self.acceleration * dt
        
        # Cap speed
        speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        if speed > self.max_speed:
            scale = self.max_speed / speed
            self.velocity_x *= scale
            self.velocity_y *= scale
            
    def apply_physics(self, dt: float) -> None:
        """Apply friction and bounds checking."""
        # Apply friction
        friction = 0.95
        self.velocity_x *= friction ** dt
        self.velocity_y *= friction ** dt
        
        # Update position
        super().update(dt)
        
        # Apply boundary constraints (keep car on screen)
        # These should match the canvas size from the client
        canvas_width = 800
        canvas_height = 600
        
        # Keep car within bounds
        half_width = self.width / 2
        half_height = self.height / 2
        
        if self.x - half_width < 0:
            self.x = half_width
            self.velocity_x = max(0, self.velocity_x)  # Stop leftward movement
        elif self.x + half_width > canvas_width:
            self.x = canvas_width - half_width
            self.velocity_x = min(0, self.velocity_x)  # Stop rightward movement
            
        if self.y - half_height < 0:
            self.y = half_height
            self.velocity_y = max(0, self.velocity_y)  # Stop upward movement
        elif self.y + half_height > canvas_height:
            self.y = canvas_height - half_height
            self.velocity_y = min(0, self.velocity_y)  # Stop downward movement
        
    def render(self) -> Dict:
        """Return render data including rotation."""
        data = super().render()
        data['rotation'] = self.rotation
        return data