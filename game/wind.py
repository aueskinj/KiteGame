"""The wind field.

Wind is a function of position and time: wind(x, y, t) -> Vec2 in m/s.

* Horizontal speed is a base speed, scaled by height (wind is stronger higher
  up: the power-law wind profile) and modulated by gusts.
* Gusts come from 1D "value noise": random numbers on a lattice, blended with
  a smoothstep curve. Sampling it at (t/tau - x/lam) makes gust fronts travel
  downwind at lam/tau metres per second, like real ones do.
* A weaker, independent noise adds up and down drafts.
"""

import math

from .rng import hash32
from .vec import Vec2

REF_HEIGHT = 10.0   # metres: the height where `base_speed` applies
SHEAR_EXPONENT = 0.2  # power-law wind profile exponent over open ground


def _lattice(seed, i):
    """Pseudo-random value in [-1, 1] for lattice point i."""
    return hash32(seed * 0x9E3779B1 + i) / 2147483648.0 - 1.0


def _smoothstep(f):
    return f * f * (3.0 - 2.0 * f)


def value_noise(seed, s):
    """Smooth 1D noise in [-1, 1]."""
    i = math.floor(s)
    f = s - i
    a = _lattice(seed, i)
    b = _lattice(seed, i + 1)
    return a + (b - a) * _smoothstep(f)


class Wind:
    def __init__(self, seed, base_speed, gustiness, tau=5.0, lam=32.0):
        self.seed = seed & 0xFFFFFFFF
        self.base_speed = base_speed
        self.gustiness = gustiness
        self.tau = tau  # seconds per noise cell
        self.lam = lam  # metres per noise cell

    def _phase(self, x, t):
        return t / self.tau - x / self.lam

    def gust(self, x, t):
        """Normalised gust value in [-1, 1] (two octaves of noise)."""
        q = self._phase(x, t)
        n = 0.65 * value_noise(self.seed, q) + 0.35 * value_noise(self.seed + 1, 2.3 * q + 17.3)
        return max(-1.0, min(1.0, n))

    def shear(self, y):
        return (max(y, 1.0) / REF_HEIGHT) ** SHEAR_EXPONENT

    def at(self, x, y, t):
        q = self._phase(x, t)
        speed = self.base_speed * self.shear(y) * (1.0 + self.gustiness * self.gust(x, t))
        vertical = self.base_speed * 0.12 * value_noise(self.seed + 2, 1.3 * q + 5.0)
        return Vec2(speed, vertical)
