"""Game state serialization and rendering logic."""
from typing import Dict, Any, List
import math
from ..entities.base import GameEntity
from ..entities.player import BeachBuggy

class Renderer:
    def __init__(self):
        self.camera_x = 0
        self.camera_y = 0
        self.view_width = 800
        self.view_height = 600
        self.zoom = 1.0
        
    def follow_player(self, player: BeachBuggy) -> None:
        """Update camera position to follow player."""
        # Keep camera centered on player with smooth following
        target_x = player.x - self.view_width / 2
        target_y = player.y - self.view_height / 2
        
        # Smooth camera movement
        smoothing = 0.05  # Lower value = smoother but slower following
        self.camera_x += (target_x - self.camera_x) * smoothing
        self.camera_y += (target_y - self.camera_y) * smoothing
        
    def world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        """Convert world coordinates to screen coordinates."""
        screen_x = (x - self.camera_x) * self.zoom
        screen_y = (y - self.camera_y) * self.zoom
        return screen_x, screen_y
        
    def is_visible(self, x: float, y: float, width: float, height: float) -> bool:
        """Check if an object is visible in the current view with generous margins."""
        screen_x, screen_y = self.world_to_screen(x, y)
        
        # Add generous margins to keep objects visible longer
        margin = 200
        
        return (screen_x + width * self.zoom >= -margin and
                screen_x <= self.view_width + margin and
                screen_y + height * self.zoom >= -margin and
                screen_y <= self.view_height + margin)
                
    def serialize_game_state(self, player: BeachBuggy, 
                           entities: List[GameEntity],
                           collectibles: List[Dict],
                           score: int,
                           time_left: float,
                           level: int,
                           game_over: bool) -> Dict[str, Any]:
        """Convert game state to a format suitable for client rendering."""
        # Update camera to follow player
        self.follow_player(player)
        
        # Convert all game objects to screen coordinates
        visible_entities = []
        for entity in entities:
            if self.is_visible(entity.x, entity.y, entity.width, entity.height):
                screen_x, screen_y = self.world_to_screen(entity.x, entity.y)
                entity_data = entity.render()
                entity_data.update({
                    'screen_x': screen_x,
                    'screen_y': screen_y
                })
                visible_entities.append(entity_data)
                
        # Convert player position
        player_screen_x, player_screen_y = self.world_to_screen(player.x, player.y)
        player_data = player.render()
        player_data.update({
            'screen_x': player_screen_x,
            'screen_y': player_screen_y
        })
        
        # Convert collectibles
        visible_collectibles = []
        for collectible in collectibles:
            if self.is_visible(collectible['x'], collectible['y'], 20, 20):
                screen_x, screen_y = self.world_to_screen(collectible['x'], collectible['y'])
                collectible_data = collectible.copy()
                collectible_data.update({
                    'screen_x': screen_x,
                    'screen_y': screen_y
                })
                visible_collectibles.append(collectible_data)
                
        return {
            'player': player_data,
            'entities': visible_entities,
            'collectibles': visible_collectibles,
            'camera': {
                'x': self.camera_x,
                'y': self.camera_y,
                'zoom': self.zoom
            },
            'score': score,
            'timeLeft': time_left,
            'level': level,
            'gameOver': game_over
        }