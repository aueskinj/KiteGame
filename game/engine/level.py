"""Track and level generation for Beach Rally."""
from typing import List, Tuple, Dict, Any
import random
import math
from ..entities.obstacles import Rock, PalmTree, Wave
from ..entities.base import GameEntity

class Track:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height
        self.checkpoints: List[Tuple[float, float]] = []
        self.obstacles: List[GameEntity] = []
        self.collectibles: List[Dict[str, Any]] = []
        self.scroll_speed = 0
        self.scroll_position = 0
        
    def generate_track(self, difficulty: int) -> None:
        """Generate a new track with appropriate difficulty."""
        self._place_checkpoints(difficulty)
        self._add_obstacles_intelligent(difficulty)
        self._add_collectibles_strategic(difficulty)
        
        print(f"Generated track with {len(self.obstacles)} obstacles and {len(self.collectibles)} collectibles")
        
    def _place_checkpoints(self, difficulty: int) -> None:
        """Place checkpoints to create the track route."""
        self.checkpoints.clear()
        
        # Start point is always at the bottom center
        self.checkpoints.append((self.width / 2, self.height - 100))
        
        # Generate fewer waypoints to prevent level completion issues
        num_points = 3 + difficulty  # Reduced from 5 + difficulty * 2
        for i in range(num_points):
            x = random.randint(100, int(self.width - 100))
            y = random.randint(100, int(self.height - 100))
            self.checkpoints.append((x, y))
            
        # End point is the start point for lap completion
        self.checkpoints.append(self.checkpoints[0])
        
    def _add_obstacles_intelligent(self, difficulty: int) -> None:
        """Add obstacles with intelligent placement inspired by endless runners."""
        self.obstacles.clear()
        
        # Define safe zones around checkpoints
        safe_radius = 80
        
        # Create obstacle patterns based on difficulty
        patterns = self._get_obstacle_patterns(difficulty)
        
        for pattern in patterns:
            placed = False
            attempts = 0
            
            while not placed and attempts < 50:
                x, y = pattern['position']
                
                # Check if position is safe from checkpoints
                safe = True
                for checkpoint in self.checkpoints:
                    distance = math.sqrt((x - checkpoint[0])**2 + (y - checkpoint[1])**2)
                    if distance < safe_radius:
                        safe = False
                        break
                
                # Check distance from other obstacles to avoid clustering
                for obstacle in self.obstacles:
                    distance = math.sqrt((x - obstacle.x)**2 + (y - obstacle.y)**2)
                    if distance < pattern['min_distance']:
                        safe = False
                        break
                
                if safe:
                    if pattern['type'] == 'rock':
                        self.obstacles.append(Rock(x, y))
                    elif pattern['type'] == 'palmtree':
                        self.obstacles.append(PalmTree(x, y))
                    elif pattern['type'] == 'wave':
                        self.obstacles.append(Wave(x, y))
                    placed = True
                else:
                    # Regenerate position
                    pattern['position'] = (
                        random.randint(50, int(self.width - 50)),
                        random.randint(50, int(self.height - 50))
                    )
                
                attempts += 1
    
    def _get_obstacle_patterns(self, difficulty: int) -> List[Dict[str, Any]]:
        """Get obstacle patterns based on difficulty."""
        patterns = []
        
        # Rocks - scattered around
        num_rocks = 3 + difficulty * 2
        for _ in range(num_rocks):
            patterns.append({
                'type': 'rock',
                'position': (
                    random.randint(50, int(self.width - 50)),
                    random.randint(50, int(self.height - 50))
                ),
                'min_distance': 100
            })
        
        # Palm trees - along edges and in clusters
        num_trees = 2 + difficulty
        for _ in range(num_trees):
            if random.random() < 0.6:  # 60% chance near edges
                if random.random() < 0.5:
                    x = random.randint(50, 150)  # Left side
                else:
                    x = random.randint(int(self.width - 150), int(self.width - 50))  # Right side
                y = random.randint(50, int(self.height - 50))
            else:  # 40% chance anywhere
                x = random.randint(50, int(self.width - 50))
                y = random.randint(50, int(self.height - 50))
            
            patterns.append({
                'type': 'palmtree',
                'position': (x, y),
                'min_distance': 80
            })
        
        # Waves - create clusters for water areas
        num_wave_clusters = 1 + difficulty // 2
        for _ in range(num_wave_clusters):
            center_x = random.randint(100, int(self.width - 100))
            center_y = random.randint(100, int(self.height - 100))
            
            # Create 3-5 waves per cluster
            waves_per_cluster = random.randint(3, 5)
            for _ in range(waves_per_cluster):
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(20, 60)
                x = center_x + math.cos(angle) * distance
                y = center_y + math.sin(angle) * distance
                
                # Keep within bounds
                x = max(50, min(x, self.width - 50))
                y = max(50, min(y, self.height - 50))
                
                patterns.append({
                    'type': 'wave',
                    'position': (x, y),
                    'min_distance': 40
                })
        
        return patterns
            
    def _add_collectibles_strategic(self, difficulty: int) -> None:
        """Add collectibles with strategic placement."""
        self.collectibles.clear()
        
        # Create coin trails that lead players through safe paths
        self._create_coin_trails(difficulty)
        
        # Add scattered bonus coins in challenging positions
        self._add_bonus_coins(difficulty)
        
        # Add power-ups in strategic locations
        self._add_strategic_powerups(difficulty)
    
    def _create_coin_trails(self, difficulty: int) -> None:
        """Create trails of coins that guide the player."""
        if len(self.checkpoints) < 2:
            return
        
        # Create trails between checkpoints
        for i in range(len(self.checkpoints) - 1):
            start = self.checkpoints[i]
            end = self.checkpoints[i + 1]
            
            # Calculate path
            distance = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
            num_coins = max(3, int(distance / 80))  # One coin every 80 units
            
            for coin_idx in range(num_coins):
                t = coin_idx / (num_coins - 1) if num_coins > 1 else 0
                
                # Linear interpolation with some randomness
                base_x = start[0] + t * (end[0] - start[0])
                base_y = start[1] + t * (end[1] - start[1])
                
                # Add some variation to avoid straight lines
                offset_x = random.uniform(-30, 30)
                offset_y = random.uniform(-30, 30)
                
                x = max(30, min(base_x + offset_x, self.width - 30))
                y = max(30, min(base_y + offset_y, self.height - 30))
                
                # Check if position is safe from obstacles
                safe = True
                for obstacle in self.obstacles:
                    distance = math.sqrt((x - obstacle.x)**2 + (y - obstacle.y)**2)
                    if distance < 50:  # 50 unit safe distance
                        safe = False
                        break
                
                if safe:
                    self.collectibles.append({
                        'type': 'coin',
                        'x': x,
                        'y': y,
                        'value': 10,
                        'collected': False
                    })
    
    def _add_bonus_coins(self, difficulty: int) -> None:
        """Add bonus coins in challenging but reachable positions."""
        num_bonus = 2 + difficulty
        
        for _ in range(num_bonus):
            attempts = 0
            placed = False
            
            while not placed and attempts < 30:
                x = random.randint(50, int(self.width - 50))
                y = random.randint(50, int(self.height - 50))
                
                # Check if near obstacles (risk/reward)
                near_obstacle = False
                for obstacle in self.obstacles:
                    distance = math.sqrt((x - obstacle.x)**2 + (y - obstacle.y)**2)
                    if 60 <= distance <= 100:  # Sweet spot near obstacles
                        near_obstacle = True
                        break
                
                # Ensure not too close to other collectibles
                safe_distance = True
                for collectible in self.collectibles:
                    distance = math.sqrt((x - collectible['x'])**2 + (y - collectible['y'])**2)
                    if distance < 40:
                        safe_distance = False
                        break
                
                if near_obstacle and safe_distance:
                    self.collectibles.append({
                        'type': 'coin',
                        'x': x,
                        'y': y,
                        'value': 25,  # Higher value for bonus coins
                        'collected': False
                    })
                    placed = True
                
                attempts += 1
    
    def _add_strategic_powerups(self, difficulty: int) -> None:
        """Add power-ups in strategic locations."""
        num_powerups = 1 + difficulty // 2
        
        powerup_types = ['speed', 'shield', 'magnet', 'time']
        
        for _ in range(num_powerups):
            attempts = 0
            placed = False
            
            while not placed and attempts < 30:
                x = random.randint(100, int(self.width - 100))
                y = random.randint(100, int(self.height - 100))
                
                # Ensure safe distance from obstacles
                safe = True
                for obstacle in self.obstacles:
                    distance = math.sqrt((x - obstacle.x)**2 + (y - obstacle.y)**2)
                    if distance < 80:
                        safe = False
                        break
                
                # Ensure safe distance from other powerups
                for collectible in self.collectibles:
                    if collectible['type'] == 'powerup':
                        distance = math.sqrt((x - collectible['x'])**2 + (y - collectible['y'])**2)
                        if distance < 150:
                            safe = False
                            break
                
                if safe:
                    power_type = random.choice(powerup_types)
                    self.collectibles.append({
                        'type': 'powerup',
                        'power_type': power_type,
                        'x': x,
                        'y': y,
                        'duration': 5.0 + difficulty,  # Longer duration at higher levels
                        'collected': False
                    })
                    placed = True
                
                attempts += 1
    
    def update_scroll(self, player_y: float, speed: float) -> None:
        """Update scrolling based on player position (endless runner style)."""
        self.scroll_speed = speed
        self.scroll_position += speed
        
        # Generate new content ahead of player
        if self.scroll_position > self.height:
            self._generate_ahead()
    
    def _generate_ahead(self) -> None:
        """Generate new obstacles and collectibles ahead of the player."""
        # This would be used for endless mode
        # For now, we'll keep the lap-based system
        pass