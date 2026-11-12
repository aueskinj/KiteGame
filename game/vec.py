"""A tiny 2D vector. x points right, y points up (world coordinates)."""

import math


class Vec2:
    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, o):
        return Vec2(self.x + o.x, self.y + o.y)

    def __sub__(self, o):
        return Vec2(self.x - o.x, self.y - o.y)

    def __mul__(self, k):
        return Vec2(self.x * k, self.y * k)

    __rmul__ = __mul__

    def __truediv__(self, k):
        return Vec2(self.x / k, self.y / k)

    def __neg__(self):
        return Vec2(-self.x, -self.y)

    def __eq__(self, o):
        return isinstance(o, Vec2) and self.x == o.x and self.y == o.y

    def __hash__(self):
        return hash((self.x, self.y))

    def __repr__(self):
        return "Vec2(%.4f, %.4f)" % (self.x, self.y)

    def dot(self, o):
        return self.x * o.x + self.y * o.y

    def cross(self, o):
        """z component of the 3D cross product."""
        return self.x * o.y - self.y * o.x

    def length(self):
        return math.hypot(self.x, self.y)

    def normalized(self):
        n = self.length()
        if n < 1e-12:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / n, self.y / n)

    def rotated(self, angle):
        c, s = math.cos(angle), math.sin(angle)
        return Vec2(self.x * c - self.y * s, self.x * s + self.y * c)

    def copy(self):
        return Vec2(self.x, self.y)

    @staticmethod
    def from_angle(angle):
        return Vec2(math.cos(angle), math.sin(angle))


def wrap_angle(a):
    """Wrap an angle in radians into (-pi, pi]."""
    a = math.fmod(a + math.pi, 2.0 * math.pi)
    if a <= 0.0:
        a += 2.0 * math.pi
    return a - math.pi


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v
