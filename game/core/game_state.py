import time
from typing import List, Dict, Any, Optional
from ..entities.player import BeachBuggy
from ..entities.base import GameEntity
from ..entities.obstacles import Rock, PalmTree, Wave
from ..engine.physics import PhysicsEngine
from ..engine.level import Track
from ..engine.renderer import Renderer

class GameState:
    def __init__(self):
        # Game systems
        self.physics = PhysicsEngine()
        self.renderer = Renderer()
        self.track = Track(800, 600)
        
        # Game objects
        self.player = BeachBuggy(400, 300)  # Start at middle of screen
        self.entities: List[GameEntity] = []
        self.collectibles: List[Dict[str, Any]] = []
        
        # Game state
        self.score = 0
        self.time_left = 60.0  # 60 seconds per level
        self.level = 1
        self.game_over = False
        self.keys_pressed = set()
        self.current_checkpoint = 0
        self.active_powerup: Optional[Dict[str, Any]] = None
        
        # Set up initial level
        self._setup_level()
        
    def _setup_level(self):
        """Initialize level with track, obstacles, and collectibles."""
        # Generate new track for current level
        self.track.generate_track(self.level)
        
        # Get generated objects
        self.entities = self.track.obstacles
        self.collectibles = self.track.collectibles
        
        # Reset player position to start
        start_pos = self.track.checkpoints[0]
        self.player.x = start_pos[0]
        self.player.y = start_pos[1]
        self.current_checkpoint = 0
        
        # Reset game state
        self.time_left = 60.0 + (self.level * 10)  # More time for higher levels
        self.active_powerup = None
        
    def update(self, dt: float) -> None:
        """Update game state for current frame."""
        if self.game_over:
            return
            
        # Update time
        self.time_left -= dt
        if self.time_left <= 0:
            self.game_over = True
            return
        
        # Update powerups
        self._update_powerups(dt)
        
        # Update player with current input state
        self.player.handle_input(self.keys_pressed, dt)
        self.player.apply_physics(dt)
        
        # Update other entities
        for entity in self.entities:
            entity.update(dt)
            
        # Check collisions
        self._check_collisions()
        
        # Check collectibles
        self._check_collectibles()
        
        # Check checkpoint progress
        self._check_checkpoints()
                
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Process game events from client."""
        event_type = event.get('type')
        
        if event_type == 'keydown':
            self.keys_pressed.add(event['key'])
        elif event_type == 'keyup':
            self.keys_pressed.discard(event['key'])
                            
    def _check_collisions(self) -> None:
        """Check and handle collisions with obstacles."""
        for entity in self.entities:
            if self.physics.check_collision(
                (self.player.x, self.player.y),
                (self.player.width, self.player.height),
                (entity.x, entity.y),
                (entity.width, entity.height)
            ):
                if isinstance(entity, Wave):
                    # Waves slow down the player gently
                    self.player.velocity_x *= 0.9
                    self.player.velocity_y *= 0.9
                else:
                    # Solid obstacles bounce the player more gently
                    normal = (
                        self.player.x - entity.x,
                        self.player.y - entity.y
                    )
                    # Normalize the vector
                    length = (normal[0]**2 + normal[1]**2)**0.5
                    if length > 0:
                        normal = (normal[0]/length, normal[1]/length)
                        bounce_velocity_x, bounce_velocity_y = \
                            self.physics.resolve_collision(
                                (self.player.x, self.player.y),
                                (self.player.velocity_x, self.player.velocity_y),
                                normal
                            )
                        # Apply much gentler bounce
                        self.player.velocity_x = self.player.velocity_x * 0.8 + bounce_velocity_x * 0.2
                        self.player.velocity_y = self.player.velocity_y * 0.8 + bounce_velocity_y * 0.2
                        
    def _check_collectibles(self) -> None:
        """Check and handle collectible collection."""
        collected_indices = []
        
        for i, collectible in enumerate(self.collectibles):
            if collectible.get('collected', False):
                continue
                
            # Check collision with collectible
            distance = ((self.player.x - collectible['x'])**2 + 
                       (self.player.y - collectible['y'])**2)**0.5
            
            # Collection radius (slightly larger than visual size)
            collection_radius = 25
            
            if distance < collection_radius:
                collectible['collected'] = True
                collected_indices.append(i)
                
                if collectible['type'] == 'coin':
                    self.score += collectible['value']
                    
                elif collectible['type'] == 'powerup':
                    self._activate_powerup(collectible)
        
        # Remove collected items (in reverse order to maintain indices)
        for i in reversed(collected_indices):
            self.collectibles.pop(i)
            
    def _activate_powerup(self, powerup: Dict[str, Any]) -> None:
        """Activate a collected powerup."""
        power_type = powerup['power_type']
        duration = powerup.get('duration', 5.0)
        
        # Deactivate current powerup if any
        if self.active_powerup:
            self._deactivate_powerup()
        
        self.active_powerup = {
            'type': power_type,
            'duration': duration,
            'start_time': time.time()
        }
        
        # Apply powerup effects
        if power_type == 'speed':
            self.player.max_speed *= 1.5
        elif power_type == 'shield':
            if hasattr(self.player, 'is_shielded'):
                self.player.is_shielded = True
        elif power_type == 'magnet':
            # Magnet effect handled in update loop
            pass
        elif power_type == 'time':
            self.time_left += 10  # Add 10 seconds

    def _deactivate_powerup(self) -> None:
        """Deactivate the current powerup."""
        if not self.active_powerup:
            return
            
        power_type = self.active_powerup['type']
        
        # Remove powerup effects
        if power_type == 'speed':
            self.player.max_speed /= 1.5
        elif power_type == 'shield':
            if hasattr(self.player, 'is_shielded'):
                self.player.is_shielded = False
        elif power_type == 'magnet':
            # No persistent effect to remove
            pass
        elif power_type == 'time':
            # No persistent effect to remove
            pass
            
        self.active_powerup = None

    def _attract_nearby_coins(self) -> None:
        """Attract nearby coins when magnet powerup is active."""
        magnet_radius = 80
        
        for collectible in self.collectibles:
            if collectible['type'] == 'coin' and not collectible.get('collected', False):
                distance = ((self.player.x - collectible['x'])**2 + 
                           (self.player.y - collectible['y'])**2)**0.5
                
                if distance < magnet_radius and distance > 0:
                    # Move coin towards player more gently
                    direction_x = (self.player.x - collectible['x']) / distance
                    direction_y = (self.player.y - collectible['y']) / distance
                    
                    # Reduced pull strength
                    pull_strength = 1.5
                    collectible['x'] += direction_x * pull_strength
                    collectible['y'] += direction_y * pull_strength

    def _update_powerups(self, dt: float) -> None:
        """Update active powerups and handle expiration."""
        if self.active_powerup:
            elapsed = time.time() - self.active_powerup['start_time']
            
            if elapsed >= self.active_powerup['duration']:
                self._deactivate_powerup()
            elif self.active_powerup['type'] == 'magnet':
                self._attract_nearby_coins()
                            
    def _check_checkpoints(self) -> None:
        """Check if player has reached the next checkpoint."""
        if self.current_checkpoint >= len(self.track.checkpoints):
            return
            
        next_checkpoint = self.track.checkpoints[self.current_checkpoint]
        distance = ((self.player.x - next_checkpoint[0])**2 + 
                   (self.player.y - next_checkpoint[1])**2)**0.5
                   
        if distance < 50:  # Checkpoint radius
            self.current_checkpoint += 1
            self.score += 50 * self.level
            print(f"Checkpoint {self.current_checkpoint}/{len(self.track.checkpoints)} reached! Score: {self.score}")
            
            # Only progress level when player has completed the full lap AND collected most items
            if (self.current_checkpoint >= len(self.track.checkpoints) and 
                self.score >= 500):  # Require significant score before level progression
                self.level += 1
                print(f"Level {self.level} completed! Generating new level...")
                self._setup_level()

class GameState:
    def __init__(self):
        # Game systems
        self.physics = PhysicsEngine()
        self.renderer = Renderer()
        self.track = Track(800, 600)
        
        # Game objects
        self.player = BeachBuggy(400, 300)  # Start at middle of screen
        self.entities: List[GameEntity] = []
        self.collectibles: List[Dict[str, Any]] = []
        
        # Game state
        self.score = 0
        self.time_left = 60.0  # 60 seconds per level
        self.level = 1
        self.game_over = False
        self.keys_pressed = set()
        self.current_checkpoint = 0
        self.active_powerup: Optional[Dict[str, Any]] = None
        
        # Set up initial level
        self._setup_level()
        
    def _setup_level(self):
        """Initialize level with track, obstacles, and collectibles."""
        # Generate new track for current level
        self.track.generate_track(self.level)
        
        # Get generated objects
        self.entities = self.track.obstacles
        self.collectibles = self.track.collectibles
        
        # Reset player position to start
        start_pos = self.track.checkpoints[0]
        self.player.x = start_pos[0]
        self.player.y = start_pos[1]
        self.current_checkpoint = 0
        
        # Reset game state
        self.time_left = 60.0 + (self.level * 10)  # More time for higher levels
        self.active_powerup = None
        
    def update(self, dt: float) -> None:
        """Update game state for current frame."""
        if self.game_over:
            return
            
        # Update time
        self.time_left -= dt
        if self.time_left <= 0:
            self.game_over = True
            return
        
        # Update powerups
        self._update_powerups(dt)
        
        # Update player with current input state
        self.player.handle_input(self.keys_pressed, dt)
        self.player.apply_physics(dt)
        
        # Update other entities
        for entity in self.entities:
            entity.update(dt)
            
        # Check collisions
        self._check_collisions()
        
        # Check collectibles
        self._check_collectibles()
        
        # Check checkpoint progress
        self._check_checkpoints()
    
    def handle_event(self, event: Dict[str, Any]) -> None:
        """Process game events from client."""
        event_type = event.get('type')
        
        if event_type == 'keydown':
            self.keys_pressed.add(event['key'])
        elif event_type == 'keyup':
            self.keys_pressed.discard(event['key'])
                            
    def _check_collisions(self) -> None:
        """Check and handle collisions with obstacles."""
        for entity in self.entities:
            if self.physics.check_collision(
                (self.player.x, self.player.y),
                (self.player.width, self.player.height),
                (entity.x, entity.y),
                (entity.width, entity.height)
            ):
                if isinstance(entity, Wave):
                    # Waves slow down the player gently
                    self.player.velocity_x *= 0.9
                    self.player.velocity_y *= 0.9
                else:
                    # Solid obstacles bounce the player more gently
                    normal = (
                        self.player.x - entity.x,
                        self.player.y - entity.y
                    )
                    # Normalize the vector
                    length = (normal[0]**2 + normal[1]**2)**0.5
                    if length > 0:
                        normal = (normal[0]/length, normal[1]/length)
                        bounce_velocity_x, bounce_velocity_y = \
                            self.physics.resolve_collision(
                                (self.player.x, self.player.y),
                                (self.player.velocity_x, self.player.velocity_y),
                                normal
                            )
                        # Apply much gentler bounce
                        self.player.velocity_x = self.player.velocity_x * 0.8 + bounce_velocity_x * 0.2
                        self.player.velocity_y = self.player.velocity_y * 0.8 + bounce_velocity_y * 0.2
                        
    def _check_collectibles(self) -> None:
        """Check and handle collectible collection."""
        collected_indices = []
        
        for i, collectible in enumerate(self.collectibles):
            if collectible.get('collected', False):
                continue
                
            # Check collision with collectible
            distance = ((self.player.x - collectible['x'])**2 + 
                       (self.player.y - collectible['y'])**2)**0.5
            
            # Collection radius (slightly larger than visual size)
            collection_radius = 25
            
            if distance < collection_radius:
                collectible['collected'] = True
                collected_indices.append(i)
                
                if collectible['type'] == 'coin':
                    self.score += collectible['value']
                    
                elif collectible['type'] == 'powerup':
                    self._activate_powerup(collectible)
        
        # Remove collected items (in reverse order to maintain indices)
        for i in reversed(collected_indices):
            self.collectibles.pop(i)
    
    def _activate_powerup(self, powerup: Dict[str, Any]) -> None:
        """Activate a collected powerup."""
        power_type = powerup['power_type']
        duration = powerup.get('duration', 5.0)
        
        # Deactivate current powerup if any
        if self.active_powerup:
            self._deactivate_powerup()
        
        self.active_powerup = {
            'type': power_type,
            'duration': duration,
            'start_time': time.time()
        }
        
        # Apply powerup effects
        if power_type == 'speed':
            self.player.max_speed *= 1.5
        elif power_type == 'shield':
            # Shield could prevent collision damage
            self.player.is_shielded = getattr(self.player, 'is_shielded', False) or True
        elif power_type == 'magnet':
            # Magnet attracts nearby coins - handled in update loop
            pass
        elif power_type == 'time':
            self.time_left += 10  # Add 10 seconds
    
    def _deactivate_powerup(self) -> None:
        """Deactivate the current powerup."""
        if not self.active_powerup:
            return
            
        power_type = self.active_powerup['type']
        
        # Remove powerup effects
        if power_type == 'speed':
            self.player.max_speed /= 1.5
        elif power_type == 'shield':
            if hasattr(self.player, 'is_shielded'):
                self.player.is_shielded = False
        elif power_type == 'magnet':
            # No persistent effect to remove
            pass
        elif power_type == 'time':
            # No persistent effect to remove
            pass
            
        self.active_powerup = None

    def _attract_nearby_coins(self) -> None:
        """Attract nearby coins when magnet powerup is active."""
        magnet_radius = 80
        
        for collectible in self.collectibles:
            if collectible['type'] == 'coin' and not collectible.get('collected', False):
                distance = ((self.player.x - collectible['x'])**2 + 
                           (self.player.y - collectible['y'])**2)**0.5
                
                if distance < magnet_radius and distance > 0:
                    # Move coin towards player more gently
                    direction_x = (self.player.x - collectible['x']) / distance
                    direction_y = (self.player.y - collectible['y']) / distance
                    
                    # Reduced pull strength
                    pull_strength = 1.5
                    collectible['x'] += direction_x * pull_strength
                    collectible['y'] += direction_y * pull_strength
    
    def _update_powerups(self, dt: float) -> None:
        """Update active powerups and handle expiration."""
        if self.active_powerup:
            elapsed = time.time() - self.active_powerup['start_time']
            
            if elapsed >= self.active_powerup['duration']:
                self._deactivate_powerup()
            elif self.active_powerup['type'] == 'magnet':
                self._attract_nearby_coins()
                            
    def _check_checkpoints(self) -> None:
        """Check if player has reached the next checkpoint."""
        if not self.track.checkpoints or self.current_checkpoint >= len(self.track.checkpoints):
            return
            
        next_checkpoint = self.track.checkpoints[self.current_checkpoint]
        distance = ((self.player.x - next_checkpoint[0])**2 + 
                   (self.player.y - next_checkpoint[1])**2)**0.5
                   
        if distance < 50:  # Checkpoint radius
            self.current_checkpoint += 1
            self.score += 50 * self.level
            print(f"Checkpoint {self.current_checkpoint} reached! Score: {self.score}")
            
            # Complete level when ALL checkpoints are reached
            if self.current_checkpoint >= len(self.track.checkpoints):
                self.level += 1
                print(f"Level {self.level} completed! Generating new level...")
                self._setup_level()
                
    def get_client_data(self) -> Dict[str, Any]:
        """Serialize current game state for client."""
        # Create a combined player data structure for backwards compatibility
        player_data = {
            'x': self.player.x,
            'y': self.player.y,
            'rotation': getattr(self.player, 'rotation', 0),
            'width': getattr(self.player, 'width', 30),
            'height': getattr(self.player, 'height', 20),
            'velocity_x': getattr(self.player, 'velocity_x', 0),
            'velocity_y': getattr(self.player, 'velocity_y', 0)
        }
        
        # Prepare entities data
        entities_data = []
        for entity in self.entities:
            entities_data.append({
                'type': entity.__class__.__name__.lower(),
                'x': entity.x,
                'y': entity.y,
                'width': getattr(entity, 'width', 20),
                'height': getattr(entity, 'height', 20)
            })
        
        return {
            'player': player_data,
            'entities': entities_data,
            'collectibles': [c for c in self.collectibles if not c.get('collected', False)],
            'score': self.score,
            'timeLeft': self.time_left,
            'level': self.level,
            'game_over': self.game_over,
            'current_checkpoint': self.current_checkpoint,
            'total_checkpoints': len(self.track.checkpoints) if self.track.checkpoints else 0,
            'active_powerup': self.active_powerup
        }