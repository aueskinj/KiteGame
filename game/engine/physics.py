"""Physics engine for the Beach Rally game."""
from typing import Tuple
import math

class PhysicsEngine:
    def __init__(self):
        self.gravity = 9.81
        self.sand_friction = 0.25  # High friction for sand
        self.water_friction = 0.1  # Lower friction for water/waves
        
    def apply_forces(self, mass: float, velocity: Tuple[float, float], 
                    force: Tuple[float, float], dt: float, 
                    surface_type: str = 'sand') -> Tuple[float, float]:
        """Apply forces to an object and return new velocity."""
        # Select friction coefficient based on surface
        friction_coef = self.water_friction if surface_type == 'water' else self.sand_friction
        
        # Calculate friction force
        speed = math.sqrt(velocity[0]**2 + velocity[1]**2)
        if speed > 0:
            friction_force = (-friction_coef * mass * self.gravity * velocity[0] / speed,
                            -friction_coef * mass * self.gravity * velocity[1] / speed)
        else:
            friction_force = (0, 0)
            
        # Sum all forces
        total_force = (force[0] + friction_force[0],
                      force[1] + friction_force[1])
                      
        # Calculate acceleration (F = ma)
        acceleration = (total_force[0] / mass,
                      total_force[1] / mass)
                      
        # Update velocity (v = v0 + at)
        new_velocity = (velocity[0] + acceleration[0] * dt,
                      velocity[1] + acceleration[1] * dt)
                      
        return new_velocity
        
    def check_collision(self, pos1: Tuple[float, float], size1: Tuple[float, float],
                       pos2: Tuple[float, float], size2: Tuple[float, float]) -> bool:
        """Check for collision between two rectangles using AABB."""
        return (pos1[0] < pos2[0] + size2[0] and
                pos1[0] + size1[0] > pos2[0] and
                pos1[1] < pos2[1] + size2[1] and
                pos1[1] + size1[1] > pos2[1])
                
    def resolve_collision(self, pos: Tuple[float, float], vel: Tuple[float, float],
                         normal: Tuple[float, float], restitution: float = 0.1) -> Tuple[float, float]:
        """Resolve collision by reflecting velocity along normal vector."""
        # Calculate dot product of velocity and normal
        dot = vel[0] * normal[0] + vel[1] * normal[1]
        
        # Calculate reflected velocity with reduced bounce
        new_velocity = (
            vel[0] - (1 + restitution) * dot * normal[0],
            vel[1] - (1 + restitution) * dot * normal[1]
        )
        
        return new_velocity