"""The whole game as one object with one method: step(controls).

No sockets, no clock, no globals. Give it a seed and a stream of controls and
it plays out the same way every time, which is what the tests rely on.

Phases:
    flying          normal play
    level_complete  all rings collected; short pause, then the next level
    game_over       out of lives; call restart() to play again
"""

import math

from . import config
from .kite import Kite, Controls
from .rng import XorShift32
from .vec import Vec2
from .wind import Wind
from .world import generate_rings, spawn_bird

FLYING = "flying"
LEVEL_COMPLETE = "level_complete"
GAME_OVER = "game_over"


class GameState:
    def __init__(self, seed=1, level=1):
        self.seed = seed
        self.score = 0
        self.lives = config.START_LIVES
        self.best_combo = 1
        self.phase = FLYING
        self.events = []
        self._start_level(level)

    # --- setup -----------------------------------------------------------

    def _start_level(self, level):
        self.level = level
        self.params = config.level_params(level)
        self.rng = XorShift32(self.seed * 1000 + level)
        self.wind = Wind(self.seed * 7 + level, self.params.wind_speed, self.params.gustiness)
        lx, ly = self._launch_point()
        self.rings = generate_rings(self.rng, self.params.ring_count, self.params.line_max, config.ANCHOR,
                                    avoid=(lx, ly, config.LAUNCH_CLEAR_RADIUS))
        self.collected = 0
        self.birds = []
        self._next_bird_id = 1
        self.bird_timer = self.params.bird_interval * 0.7
        self.t = 0.0
        self.phase = FLYING
        self.phase_timer = 0.0
        self.combo = 1
        self.combo_timer = 0.0
        self.snap_timer = 0.0
        self.tension_smooth = 0.0
        self._launch()

    @staticmethod
    def _launch_point():
        return config.ANCHOR.x + 9.0, config.ANCHOR.y + 2.0

    def _launch(self):
        """Put the kite in the air downwind of the player with a safety window."""
        L = min(self.params.line_max, 10.0)
        self.kite = Kite(Vec2(*self._launch_point()),
                         Vec2(0.0, 1.0), line_len=L)
        self.grace = config.LAUNCH_GRACE
        self.snap_timer = 0.0
        self.tension_smooth = 0.0

    def restart(self):
        self.score = 0
        self.lives = config.START_LIVES
        self.best_combo = 1
        self.events = []
        self._start_level(1)

    # --- stepping --------------------------------------------------------

    def step(self, controls):
        """Advance one tick. Returns the list of events that happened."""
        self.events = []
        if self.phase == GAME_OVER:
            return self.events
        dt = config.DT
        self.t += dt

        if self.phase == LEVEL_COMPLETE:
            self.phase_timer -= dt
            self._move_kite(dt, controls)
            if self.phase_timer <= 0.0:
                self._start_level(self.level + 1)
                self.events.append({"type": "level_start", "level": self.level})
            return self.events

        self._move_kite(dt, controls)
        self._update_birds(dt)
        self._check_rings()
        if self.phase == FLYING:
            self._check_hazards(dt)
        self.combo_timer = max(0.0, self.combo_timer - dt)
        if self.combo_timer == 0.0:
            self.combo = 1
        self.grace = max(0.0, self.grace - dt)
        return self.events

    def _move_kite(self, dt, controls):
        k = self.kite
        k.advance(dt, controls, self.wind.at, config.ANCHOR, self.params.line_max, t=self.t)
        # Ground and ceiling are soft walls: the kite stops, it does not bounce.
        if k.pos.y < config.GROUND_Y:
            k.pos.y = config.GROUND_Y
            if k.vel.y < 0.0:
                k.vel.y = 0.0
            k.vel.x *= 0.9
        elif k.pos.y > config.CEILING_Y:
            k.pos.y = config.CEILING_Y
            if k.vel.y > 0.0:
                k.vel.y = 0.0
        self.tension_smooth += config.TENSION_SMOOTHING * (k.tension - self.tension_smooth)

    def _update_birds(self, dt):
        if self.phase != FLYING:
            return
        self.bird_timer -= dt
        if self.bird_timer <= 0.0:
            self.bird_timer = self.params.bird_interval * self.rng.uniform(0.7, 1.3)
            self.birds.append(spawn_bird(self.rng, self._next_bird_id, self.params, config.ANCHOR))
            self._next_bird_id += 1
        for b in self.birds:
            b.x += b.vx * dt
        lo, hi = config.VIEW["x0"] - 4.0, config.VIEW["x1"] + 4.0
        self.birds = [b for b in self.birds if lo <= b.x <= hi]

    def _check_rings(self):
        if self.phase != FLYING:
            return
        k = self.kite
        remaining = []
        for r in self.rings:
            if math.hypot(k.pos.x - r.x, k.pos.y - r.y) <= r.r + config.KITE_RADIUS:
                self.collected += 1
                points = config.RING_POINTS * self.combo
                self.score += points
                self.events.append({"type": "ring", "id": r.id, "x": r.x, "y": r.y,
                                    "points": points, "combo": self.combo})
                self.best_combo = max(self.best_combo, self.combo)
                self.combo = min(self.combo + 1, config.COMBO_MAX)
                self.combo_timer = config.COMBO_WINDOW
            else:
                remaining.append(r)
        self.rings = remaining
        if not self.rings:
            bonus = 250 * self.level
            self.score += bonus
            self.phase = LEVEL_COMPLETE
            self.phase_timer = config.LEVEL_COMPLETE_PAUSE
            self.birds = []
            self.events.append({"type": "level_complete", "level": self.level, "bonus": bonus})

    def _check_hazards(self, dt):
        k = self.kite
        if self.grace > 0.0:
            self.snap_timer = 0.0
            return
        for b in self.birds:
            if math.hypot(k.pos.x - b.x, k.pos.y - b.y) <= config.BIRD_RADIUS + config.KITE_RADIUS:
                self._lose_life("bird")
                return
        if self.tension_smooth > config.SNAP_TENSION:
            self.snap_timer += dt
            if self.snap_timer >= config.SNAP_DWELL:
                self._lose_life("snap")
        else:
            self.snap_timer = max(0.0, self.snap_timer - dt)

    def _lose_life(self, cause):
        self.lives -= 1
        self.combo = 1
        self.combo_timer = 0.0
        self.events.append({"type": "life_lost", "cause": cause, "lives": self.lives,
                            "x": self.kite.pos.x, "y": self.kite.pos.y})
        if self.lives <= 0:
            self.phase = GAME_OVER
            self.events.append({"type": "game_over", "score": self.score})
        else:
            self.birds = []
            self._launch()

    # --- snapshot --------------------------------------------------------

    def snapshot(self):
        """Everything the client needs to draw one frame, as plain JSON types."""
        k = self.kite
        w = self.wind.at(k.pos.x, k.pos.y, self.t)
        return {
            "t": round(self.t, 3),
            "phase": self.phase,
            "level": self.level,
            "score": self.score,
            "lives": self.lives,
            "combo": self.combo,
            "combo_left": round(self.combo_timer / config.COMBO_WINDOW, 3),
            "grace": round(self.grace, 2),
            "rings_left": len(self.rings),
            "rings_total": self.params.ring_count,
            "kite": {
                "x": round(k.pos.x, 3), "y": round(k.pos.y, 3),
                "theta": round(k.theta, 4), "beta": round(k.beta, 4),
                "line": round(k.line_len, 3), "line_max": self.params.line_max,
                "tension": round(self.tension_smooth, 2),
                "slack": round(k.slack, 3),
            },
            "wind": {"x": round(w.x, 3), "y": round(w.y, 3),
                     "gust": round(self.wind.gust(k.pos.x, self.t), 3)},
            "rings": [{"id": r.id, "x": round(r.x, 3), "y": round(r.y, 3), "r": r.r} for r in self.rings],
            "birds": [{"id": b.id, "x": round(b.x, 3), "y": round(b.y, 3), "vx": round(b.vx, 3)}
                      for b in self.birds],
            "snap_risk": round(min(1.0, self.snap_timer / config.SNAP_DWELL), 3),
            "events": self.events,
        }

    def static_info(self):
        """Constants the client needs once, at connect time."""
        return {"view": config.VIEW, "anchor": {"x": config.ANCHOR.x, "y": config.ANCHOR.y},
                "ground_y": config.GROUND_Y, "snap_tension": config.SNAP_TENSION,
                "kite_radius": config.KITE_RADIUS, "bird_radius": config.BIRD_RADIUS,
                "tick_hz": config.TICK_HZ}
