import math
import unittest

from game import config
from game.kite import Controls
from game.rng import XorShift32
from game.state import GameState, FLYING, LEVEL_COMPLETE, GAME_OVER
from game.vec import Vec2
from game.world import generate_rings, Bird

NONE = Controls()


def teleport_to(gs, x, y):
    """Put the kite at (x, y), paying out enough line that the constraint does not pull it back."""
    gs.kite.line_len = max(gs.kite.line_len, math.hypot(x - config.ANCHOR.x, y - config.ANCHOR.y) + 1.0)
    gs.kite.line_len = min(gs.kite.line_len, gs.params.line_max)
    gs.kite.pos = Vec2(x, y)
    gs.kite.vel = Vec2(0, 0)


class TestLevelParams(unittest.TestCase):
    def test_difficulty_increases_then_caps(self):
        a, b, c = config.level_params(1), config.level_params(5), config.level_params(60)
        self.assertLess(a.wind_speed, b.wind_speed)
        self.assertLess(a.gustiness, b.gustiness)
        self.assertGreater(a.bird_interval, b.bird_interval)
        self.assertLessEqual(c.wind_speed, 8.0)
        self.assertLessEqual(c.line_max, 20.0)
        self.assertGreaterEqual(c.bird_interval, 6.0)
        self.assertLessEqual(c.ring_count, 9)


class TestRingGeneration(unittest.TestCase):
    def test_all_rings_reachable_and_spaced(self):
        for seed in range(40):
            for level in range(1, 12):
                p = config.level_params(level)
                rings = generate_rings(XorShift32(seed * 31 + level), p.ring_count, p.line_max, config.ANCHOR,
                                       avoid=(14.0, 3.4, config.LAUNCH_CLEAR_RADIUS))
                self.assertEqual(len(rings), p.ring_count)
                for i, a in enumerate(rings):
                    for b in rings[i + 1:]:
                        self.assertGreaterEqual(math.hypot(a.x - b.x, a.y - b.y), config.RING_MIN_SPACING - 1e-9,
                                                (seed, level))
                for r in rings:
                    d = math.hypot(r.x - config.ANCHOR.x, r.y - config.ANCHOR.y)
                    self.assertLessEqual(d, p.line_max)                 # within reach of the line
                    self.assertGreaterEqual(r.y, config.RING_MIN_Y)
                    self.assertLess(r.x, config.VIEW["x1"])             # on screen
                    self.assertLess(r.y, config.VIEW["y1"])

    def test_avoid_zone_respected(self):
        for seed in range(30):
            rings = generate_rings(XorShift32(seed), 5, 15.0, config.ANCHOR, avoid=(14.0, 3.4, 3.0))
            for r in rings:
                self.assertGreaterEqual(math.hypot(r.x - 14.0, r.y - 3.4), 3.0 - 1e-9)

    def test_same_seed_same_rings(self):
        a = generate_rings(XorShift32(5), 6, 15.0, config.ANCHOR)
        b = generate_rings(XorShift32(5), 6, 15.0, config.ANCHOR)
        self.assertEqual([(r.x, r.y) for r in a], [(r.x, r.y) for r in b])

    def test_always_terminates_even_when_cramped(self):
        rings = generate_rings(XorShift32(1), 11, 9.0, config.ANCHOR, avoid=(14.0, 3.4, 9.0))
        self.assertEqual(len(rings), 11)


class TestGameFlow(unittest.TestCase):
    def test_initial_state(self):
        gs = GameState(seed=1)
        self.assertEqual(gs.phase, FLYING)
        self.assertEqual(gs.lives, config.START_LIVES)
        self.assertEqual(gs.score, 0)
        self.assertEqual(len(gs.rings), gs.params.ring_count)
        self.assertGreater(gs.grace, 0.0)

    def test_collecting_a_ring_scores_and_removes_it(self):
        gs = GameState(seed=1)
        r = gs.rings[0]
        teleport_to(gs, r.x, r.y)
        events = gs.step(NONE)
        self.assertEqual(gs.score, config.RING_POINTS)
        self.assertEqual(len(gs.rings), gs.params.ring_count - 1)
        self.assertTrue(any(e["type"] == "ring" and e["id"] == r.id for e in events))

    def test_combo_multiplies_then_resets_after_window(self):
        gs = GameState(seed=1)
        r1, r2 = gs.rings[0], gs.rings[1]
        teleport_to(gs, r1.x, r1.y); gs.step(NONE)
        teleport_to(gs, r2.x, r2.y); gs.step(NONE)
        self.assertEqual(gs.score, config.RING_POINTS * 1 + config.RING_POINTS * 2)
        self.assertEqual(gs.combo, 3)
        for r in gs.rings:                        # move the rest out of reach so the kite cannot extend the combo
            r.x, r.y = 900.0, 900.0
        gs.grace = 99.0
        for _ in range(int(config.COMBO_WINDOW * 60) + 5):
            gs.kite.vel = Vec2(0, 0)
            gs.step(NONE)
            if gs.phase != FLYING:
                break
        self.assertEqual(gs.combo, 1)

    def test_combo_is_capped(self):
        gs = GameState(seed=2)
        for _ in range(7):
            if len(gs.rings) <= 1:
                break
            r = gs.rings[0]
            teleport_to(gs, r.x, r.y); gs.step(NONE)
        self.assertLessEqual(gs.combo, config.COMBO_MAX)

    def test_clearing_all_rings_completes_level_and_advances(self):
        gs = GameState(seed=3)
        while gs.rings:
            r = gs.rings[0]
            teleport_to(gs, r.x, r.y)
            gs.step(NONE)
        self.assertEqual(gs.phase, LEVEL_COMPLETE)
        score = gs.score
        self.assertGreater(score, 0)
        for _ in range(int(config.LEVEL_COMPLETE_PAUSE * 60) + 5):
            gs.step(NONE)
        self.assertEqual(gs.phase, FLYING)
        self.assertEqual(gs.level, 2)
        self.assertEqual(len(gs.rings), config.level_params(2).ring_count)
        self.assertEqual(gs.score, score)       # score carries over
        self.assertEqual(gs.lives, config.START_LIVES)

    def test_level_progression_does_not_freeze_the_kite(self):
        """Regression for the original 'level progression freezes the car' bug."""
        gs = GameState(seed=3)
        for lvl in range(1, 4):
            while gs.rings:
                r = gs.rings[0]
                teleport_to(gs, r.x, r.y); gs.step(NONE)
            for _ in range(int(config.LEVEL_COMPLETE_PAUSE * 60) + 5):
                gs.step(NONE)
            self.assertEqual(gs.level, lvl + 1)
            before = (gs.kite.pos.x, gs.kite.pos.y)
            for _ in range(120):
                gs.step(NONE)
            self.assertNotEqual((gs.kite.pos.x, gs.kite.pos.y), before)
            self.assertEqual(gs.phase, FLYING)

    def test_bird_strike_costs_a_life_and_relaunches(self):
        gs = GameState(seed=1)
        gs.grace = 0.0
        gs.birds = [Bird(99, gs.kite.pos.x, gs.kite.pos.y, 1.0)]
        events = gs.step(NONE)
        self.assertEqual(gs.lives, config.START_LIVES - 1)
        self.assertTrue(any(e["type"] == "life_lost" and e["cause"] == "bird" for e in events))
        self.assertGreater(gs.grace, 0.0)
        self.assertEqual(gs.birds, [])

    def test_grace_period_protects_the_kite(self):
        gs = GameState(seed=1)
        self.assertGreater(gs.grace, 0.0)
        gs.birds = [Bird(99, gs.kite.pos.x, gs.kite.pos.y, 1.0)]
        gs.step(NONE)
        self.assertEqual(gs.lives, config.START_LIVES)

    def test_sustained_overtension_snaps_the_line(self):
        gs = GameState(seed=1)
        gs.grace = 0.0
        lost = False
        for _ in range(int(config.SNAP_DWELL * 60) + 5):
            gs.tension_smooth = config.SNAP_TENSION + 5
            gs.events = []
            gs._check_hazards(config.DT)
            if any(e["type"] == "life_lost" and e["cause"] == "snap" for e in gs.events):
                lost = True
                break
        self.assertTrue(lost)

    def test_real_physics_in_a_gale_snaps_the_line(self):
        """Integration: strong wind + a steeply pitched kite really does overload the line."""
        from game.wind import Wind
        gs = GameState(seed=1)
        gs.wind = Wind(1, 16.0, 0.0)
        gs.grace = 0.0
        gs.rings = gs.rings[:1]                      # keep the level from completing
        gs.rings[0].x, gs.rings[0].y = 900.0, 900.0  # ...by putting its only ring far away
        broke = False
        for _ in range(60 * 30):
            if any(e["type"] == "life_lost" and e["cause"] == "snap" for e in gs.step(Controls(up=True))):
                broke = True
                break
        self.assertTrue(broke)

    def test_brief_tension_spike_does_not_snap(self):
        gs = GameState(seed=1)
        gs.grace = 0.0
        gs.tension_smooth = config.SNAP_TENSION + 5
        gs.snap_timer = 0.0
        gs._check_hazards(config.DT)           # a single tick over the limit
        self.assertEqual(gs.lives, config.START_LIVES)

    def test_game_over_then_restart(self):
        gs = GameState(seed=1)
        for _ in range(config.START_LIVES):
            gs.grace = 0.0
            gs.birds = [Bird(1, gs.kite.pos.x, gs.kite.pos.y, 0.0)]
            gs.step(NONE)
        self.assertEqual(gs.phase, GAME_OVER)
        t = gs.t
        gs.step(NONE)                             # frozen while game over
        self.assertEqual(gs.t, t)
        gs.restart()
        self.assertEqual(gs.phase, FLYING)
        self.assertEqual(gs.lives, config.START_LIVES)
        self.assertEqual(gs.score, 0)
        self.assertEqual(gs.level, 1)

    def test_ground_and_ceiling_hold(self):
        gs = GameState(seed=1)
        gs.kite.pos = Vec2(8, -5); gs.step(NONE)
        self.assertGreaterEqual(gs.kite.pos.y, config.GROUND_Y - 1e-9)
        gs.kite.pos = Vec2(config.ANCHOR.x + 5, 40); gs.step(NONE)
        self.assertLessEqual(gs.kite.pos.y, config.CEILING_Y + 1e-9)

    def test_birds_spawn_and_leave(self):
        gs = GameState(seed=1)
        gs.grace = 99.0
        seen = False
        for _ in range(60 * 60):
            gs.step(NONE)
            if gs.phase != FLYING:
                break
            seen = seen or bool(gs.birds)
            for b in gs.birds:
                self.assertGreaterEqual(b.y, 4.0)
        self.assertTrue(seen)
        self.assertLess(len(gs.birds), 10)

    def test_same_seed_same_game(self):
        def play(seed):
            gs = GameState(seed=seed)
            for i in range(900):
                gs.step(Controls(up=(i % 200 < 60), right=(i % 300 < 100)))
            return gs.snapshot()
        self.assertEqual(play(7), play(7))
        self.assertNotEqual(play(7)["kite"], play(8)["kite"])

    def test_long_random_play_never_breaks(self):
        rng = XorShift32(99)
        for seed in range(1, 6):
            gs = GameState(seed=seed)
            ctl = Controls()
            for i in range(60 * 90):
                if i % 20 == 0:
                    ctl = Controls(rng.random() < .3, rng.random() < .3, rng.random() < .4, rng.random() < .4)
                gs.step(ctl)
                if gs.phase == GAME_OVER:
                    gs.restart()
            snap = gs.snapshot()
            for v in (snap["kite"]["x"], snap["kite"]["y"], snap["kite"]["tension"]):
                self.assertTrue(math.isfinite(v))


class TestSnapshot(unittest.TestCase):
    def test_snapshot_is_json_serialisable_and_complete(self):
        import json
        gs = GameState(seed=1)
        gs.step(NONE)
        snap = gs.snapshot()
        json.dumps(snap)
        for key in ("phase", "level", "score", "lives", "combo", "kite", "wind", "rings", "birds", "events"):
            self.assertIn(key, snap)
        for key in ("x", "y", "theta", "line", "line_max", "tension", "slack"):
            self.assertIn(key, snap["kite"])

    def test_events_do_not_leak_between_ticks(self):
        gs = GameState(seed=1)
        r = gs.rings[0]
        teleport_to(gs, r.x, r.y)
        self.assertTrue(gs.step(NONE))
        self.assertEqual(gs.step(NONE), [])


if __name__ == "__main__":
    unittest.main()
