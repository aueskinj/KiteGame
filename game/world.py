"""Things in the sky: rings to collect and birds to avoid."""

import math

from . import config


class Ring:
    __slots__ = ("id", "x", "y", "r")

    def __init__(self, id, x, y, r=config.RING_RADIUS):
        self.id = id
        self.x = x
        self.y = y
        self.r = r


class Bird:
    __slots__ = ("id", "x", "y", "vx")

    def __init__(self, id, x, y, vx):
        self.id = id
        self.x = x
        self.y = y
        self.vx = vx


def _min_gap(rings):
    gap = float("inf")
    for i, a in enumerate(rings):
        for b in rings[i + 1:]:
            gap = min(gap, math.hypot(a.x - b.x, a.y - b.y))
    return gap


def _place_rings(rng, count, d_max, anchor, avoid):
    """One attempt at placing rings with best-candidate sampling.

    For each ring we draw several candidate spots and keep the one farthest
    from the rings already placed. That spreads them out evenly, which plain
    one-at-a-time random placement cannot do once the sky gets crowded.
    """
    rings = []
    for _ in range(count):
        best, best_score = None, -1.0
        tries = 0
        while tries < 40 or best is None:
            tries += 1
            if tries > 3000:
                avoid = None            # last resort so this always terminates
            d = rng.uniform(config.RING_MIN_DIST, d_max)
            e = math.radians(rng.uniform(config.RING_ELEV_MIN, config.RING_ELEV_MAX))
            x = anchor.x + d * math.cos(e)
            y = anchor.y + d * math.sin(e)
            if y < config.RING_MIN_Y:
                continue
            if avoid is not None and math.hypot(x - avoid[0], y - avoid[1]) < avoid[2]:
                continue
            score = min((math.hypot(x - r.x, y - r.y) for r in rings), default=1e9)
            if score > best_score:
                best, best_score = (x, y), score
        rings.append(Ring(len(rings) + 1, best[0], best[1]))
    return rings


def generate_rings(rng, count, line_max, anchor, avoid=None):
    """Scatter `count` rings where a kite on a `line_max` line can actually go.

    `avoid` is an optional (x, y, radius) circle to keep clear, so rings do not
    spawn on top of the kite's launch point and get collected for free.

    Positions are picked in polar coordinates around the player: distance
    from the hand and elevation above the horizon. We retry until every pair
    of rings is at least RING_MIN_SPACING apart; if that is impossible we
    return the best attempt seen, so this always terminates.
    """
    d_max = max(config.RING_MIN_DIST + 0.5, line_max - config.RING_EDGE_MARGIN)
    best, best_gap = None, -1.0
    for _ in range(60):
        rings = _place_rings(rng, count, d_max, anchor, avoid)
        gap = _min_gap(rings)
        if gap > best_gap:
            best, best_gap = rings, gap
        if gap >= config.RING_MIN_SPACING:
            break
    return best


def spawn_bird(rng, bird_id, params, anchor):
    """A bird enters from just outside the left or right edge of the view."""
    top = min(config.CEILING_Y - 1.5, anchor.y + params.line_max * 0.8)
    y = rng.uniform(4.0, top)
    speed = params.bird_speed * rng.uniform(0.8, 1.25)
    if rng.random() < 0.5:
        return Bird(bird_id, config.VIEW["x0"] - 2.0, y, speed)
    return Bird(bird_id, config.VIEW["x1"] + 2.0, y, -speed)
