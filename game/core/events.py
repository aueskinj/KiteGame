from typing import Dict, Any, Callable
from functools import wraps

class EventSystem:
    def __init__(self):
        self._handlers = {}
        
    def register(self, event_type: str, handler: Callable) -> None:
        """Register an event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        
    def emit(self, event_type: str, **kwargs) -> None:
        """Emit an event to all registered handlers."""
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(**kwargs)
                
def game_event(event_type: str):
    """Decorator to register game event handlers."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        EventSystem().register(event_type, wrapper)
        return wrapper
    return decorator