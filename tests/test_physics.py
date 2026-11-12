import math
import unittest

from game.kite import Kite, Controls, KiteParams, plate_force
from game.rng import XorShift32, hash32
from game.vec import Vec2, wrap_angle
from game.wind import Wind, value_noise

ANCHOR = Vec2(5.0, 1.4)


def steady_wind(speed):
    return lambda x, y, t: Vec2(speed, 0.0)


def fly(kite, wind, seconds, controls=None, line_max=40.0, t0=0.0):
    controls = controls or Controls()
    for i in range(int(seconds * 60)):
        kite.advance(1 / 60, controls, wind, ANCHOR, line_max, t=t0 + i / 60)


class TestVec(unittest.TestCase):
    def test_basic_ops(self):
        a, b = Vec2(3, 4), Vec2(1, 2)
        self.assertEqual(a + b, Vec2(4, 6))
        self.assertEqual(a - b, Vec2(2, 2))
        self.assertEqual(a * 2, Vec2(6, 8))
        self.assertEqual(a.length(), 5.0)
        self.assertEqual(a.dot(b), 11.0)
        self.assertEqual(a.cross(b), 2.0)

    def test_normalize_zero_is_safe(self):
        self.assertEqual(Vec2(0, 0).normalized(), Vec2(0, 0))

    def test_rotation(self):
        r = Vec2(1, 0).rotated(math.pi / 2)
        self.assertAlmostEqual(r.x, 0.0, places=9)
        self.assertAlmostEqual(r.y, 1.0, places=9)

    def test_wrap_angle_range(self):
        for a in (-10, -math.pi, 0, math.pi, 3 * math.pi, 100):
            w = wrap_angle(a)
            self.assertTrue(-math.pi < w <= math.pi + 1e-12, (a, w))
            self.assertAlmostEqual(math.cos(w), math.cos(a), places=9)
            self.assertAlmostEqual(math.sin(w), math.sin(a), places=9)


class TestRng(unittest.TestCase):
    def test_deterministic(self):
        a, b = XorShift32(42), XorShift32(42)
        self.assertEqual([a.next_u32() for _ in range(50)], [b.next_u32() for _ in range(50)])

    def test_different_seeds_differ(self):
        self.assertNotEqual(XorShift32(1).next_u32(), XorShift32(2).next_u32())

    def test_range_and_mean(self):
        r = XorShift32(7)
        xs = [r.random() for _ in range(20000)]
        self.assertTrue(all(0.0 <= x < 1.0 for x in xs))
        self.assertAlmostEqual(sum(xs) / len(xs), 0.5, delta=0.01)

    def test_randint_inclusive(self):
        r = XorShift32(3)
        seen = {r.randint(1, 4) for _ in range(500)}
        self.assertEqual(seen, {1, 2, 3, 4})

    def test_zero_seed_does_not_stick(self):
        r = XorShift32(0)
        self.assertNotEqual(r.next_u32(), r.next_u32())

    def test_hash32_known_value_is_stable(self):
        # Pinned so a change to the hash (which would reshuffle every level) is noticed.
        self.assertEqual(hash32(0), 0)
        self.assertEqual(hash32(1), 1364076727)


class TestWind(unittest.TestCase):
    def test_noise_bounds_and_continuity(self):
        prev = value_noise(5, 0.0)
        for i in range(1, 2000):
            v = value_noise(5, i * 0.01)
            self.assertTrue(-1.0 <= v <= 1.0)
            self.assertLess(abs(v - prev), 0.1)   # smooth: no jumps
            prev = v

    def test_stronger_higher_up(self):
        w = Wind(1, 6.0, 0.0)
        self.assertGreater(w.at(0, 20, 0).x, w.at(0, 2, 0).x)

    def test_gust_scales_with_gustiness(self):
        calm, gusty = Wind(9, 6.0, 0.0), Wind(9, 6.0, 0.5)
        ts = [i * 0.1 for i in range(400)]
        spread = lambda w: max(w.at(0, 10, t).x for t in ts) - min(w.at(0, 10, t).x for t in ts)
        self.assertAlmostEqual(spread(calm), 0.0, places=9)
        self.assertGreater(spread(gusty), 1.0)

    def test_wind_never_reverses(self):
        w = Wind(3, 5.0, 0.5)
        for i in range(2000):
            self.assertGreater(w.at(i * 0.05, 8, i * 0.05).x, 0.0)

    def test_reproducible(self):
        self.assertEqual(Wind(4, 5.0, 0.3).at(3, 9, 12.5), Wind(4, 5.0, 0.3).at(3, 9, 12.5))


class TestPlateForce(unittest.TestCase):
    def test_force_is_normal_to_plate_when_no_friction(self):
        class P(KiteParams):
            plate_cf = 0.0
            body_area = 0.0
        theta = math.radians(150)
        c = Vec2(math.cos(theta), math.sin(theta))
        f = plate_force(theta, Vec2(5.0, 1.0), P)
        self.assertAlmostEqual(f.dot(c), 0.0, places=9)

    def test_force_scales_with_speed_squared(self):
        f1 = plate_force(math.radians(150), Vec2(3, 0)).length()
        f2 = plate_force(math.radians(150), Vec2(6, 0)).length()
        self.assertAlmostEqual(f2 / f1, 4.0, delta=0.2)

    def test_no_relative_wind_no_force(self):
        self.assertEqual(plate_force(1.0, Vec2(0, 0)).length(), 0.0)

    def test_lift_exists_for_angled_plate(self):
        # Chord pointing upwind and slightly up: air hits the underside and pushes up.
        f = plate_force(math.radians(150), Vec2(6, 0))
        self.assertGreater(f.y, 0.0)
        self.assertGreater(f.x, 0.0)


class TestKiteBehaviour(unittest.TestCase):
    def test_line_is_never_longer_than_its_length(self):
        k = Kite(Vec2(9, 4), Vec2(3, 3), line_len=10.0)
        for i in range(60 * 30):
            k.advance(1 / 60, Controls(), steady_wind(9.0), ANCHOR, 40.0, t=i / 60)
            self.assertLessEqual((k.pos - ANCHOR).length(), k.line_len + 1e-6)

    def test_everything_stays_finite(self):
        k = Kite(Vec2(9, 4), Vec2(0, 0), line_len=14.0)
        w = Wind(2, 8.0, 0.5)
        ctl = Controls(up=True, right=True)
        for i in range(60 * 60):
            if i % 120 == 0:
                ctl = Controls(left=(i // 120) % 2 == 0, down=(i // 240) % 2 == 0)
            k.advance(1 / 60, ctl, w.at, ANCHOR, 20.0, t=i / 60)
        for v in (k.pos.x, k.pos.y, k.vel.x, k.vel.y, k.theta, k.omega, k.tension):
            self.assertTrue(math.isfinite(v))

    def test_kite_flies_in_steady_wind(self):
        k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=18.0)
        fly(k, steady_wind(5.5), 25)
        self.assertGreater(k.pos.y, 8.0)               # it is up, not on the floor
        self.assertGreater(k.tension, 1.0)             # and the line is pulling
        self.assertLess(k.tension, 15.0)               # without snapping

    def test_kite_settles_to_a_stable_pose(self):
        k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=18.0)
        fly(k, steady_wind(5.5), 25)
        p0 = k.pos.copy()
        fly(k, steady_wind(5.5), 5, t0=25)
        self.assertLess((k.pos - p0).length(), 0.5)

    def test_kite_falls_without_wind(self):
        k = Kite(Vec2(9, 8), Vec2(0, 0), line_len=14.0)
        fly(k, steady_wind(0.0), 8)
        self.assertLess(k.pos.y, 4.0)

    def test_stronger_wind_means_more_tension(self):
        def T(speed):
            k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=18.0)
            fly(k, steady_wind(speed), 25)
            return k.tension
        self.assertLess(T(4.0), T(7.0))
        self.assertLess(T(7.0), T(10.0))

    def test_tilting_flatter_lowers_the_kite(self):
        def height(beta_deg):
            k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=18.0, beta=math.radians(beta_deg))
            fly(k, steady_wind(5.5), 25)
            return k.pos.y
        self.assertGreater(height(20), height(45))

    def test_down_key_lowers_beta_effect_up_key_raises_pull(self):
        k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=18.0)
        fly(k, steady_wind(5.5), 10)
        b0 = k.beta
        fly(k, steady_wind(5.5), 0.5, Controls(down=True), t0=10)
        self.assertGreater(k.beta, b0)
        b1 = k.beta
        fly(k, steady_wind(5.5), 0.5, Controls(up=True), t0=11)
        self.assertLess(k.beta, b1)

    def test_beta_is_clamped(self):
        k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=18.0)
        fly(k, steady_wind(5.5), 10, Controls(up=True))
        self.assertAlmostEqual(k.beta, KiteParams.beta_min, places=6)
        fly(k, steady_wind(5.5), 10, Controls(down=True), t0=10)
        self.assertAlmostEqual(k.beta, KiteParams.beta_max, places=6)

    def test_reel_changes_line_length_at_reel_speed(self):
        k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=10.0)
        fly(k, steady_wind(5.0), 1.0, Controls(right=True))
        self.assertAlmostEqual(k.line_len, 10.0 + KiteParams.reel_speed, places=2)
        fly(k, steady_wind(5.0), 1.0, Controls(left=True), t0=1)
        self.assertAlmostEqual(k.line_len, 10.0, places=2)

    def test_line_length_limits(self):
        k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=10.0)
        fly(k, steady_wind(5.0), 20.0, Controls(right=True), line_max=15.0)
        self.assertAlmostEqual(k.line_len, 15.0, places=6)
        fly(k, steady_wind(5.0), 20.0, Controls(left=True), line_max=15.0, t0=20)
        self.assertAlmostEqual(k.line_len, KiteParams.line_min, places=6)

    def test_opposite_keys_cancel(self):
        k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=10.0)
        fly(k, steady_wind(5.0), 1.0, Controls(left=True, right=True))
        self.assertAlmostEqual(k.line_len, 10.0, places=6)

    def test_deterministic(self):
        def run():
            k = Kite(Vec2(8, 3), Vec2(0, 1.5), line_len=14.0)
            w = Wind(5, 6.0, 0.3)
            for i in range(600):
                k.advance(1 / 60, Controls(up=(i % 90 < 30)), w.at, ANCHOR, 20.0, t=i / 60)
            return (k.pos.x, k.pos.y, k.theta, k.tension)
        self.assertEqual(run(), run())

    def test_tension_is_zero_when_slack(self):
        k = Kite(Vec2(7, 3), Vec2(0, 0), line_len=14.0)
        fly(k, steady_wind(0.0), 0.2)
        self.assertEqual(k.tension, 0.0)
        self.assertGreater(k.slack, 1.0)


if __name__ == "__main__":
    unittest.main()
