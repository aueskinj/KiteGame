"""Game constants and the difficulty curve. All lengths are in metres."""

from .vec import Vec2

TICK_HZ = 60
DT = 1.0 / TICK_HZ

# The visible world. The server tells the client these numbers so both agree.
VIEW = {"x0": -2.0, "x1": 34.0, "y0": -2.25, "y1": 18.0}
ANCHOR = Vec2(5.0, 1.4)     # the player's hand
GROUND_Y = 0.15             # lowest point the kite can reach
CEILING_Y = 17.5            # the kite cannot climb past this

START_LIVES = 3
LAUNCH_GRACE = 2.5          # seconds of safety after a (re)launch
LEVEL_COMPLETE_PAUSE = 3.0  # seconds between levels

KITE_RADIUS = 0.5
RING_RADIUS = 1.3
BIRD_RADIUS = 0.7

SNAP_TENSION = 16.0         # newtons: the line breaks if held above this...
SNAP_DWELL = 0.3            # ...for this many seconds
TENSION_SMOOTHING = 0.2     # EMA factor per tick

COMBO_WINDOW = 8.0          # seconds to grab the next ring and keep the combo
COMBO_MAX = 5
RING_POINTS = 100

RING_ELEV_MIN = 22.0        # degrees above the horizon, seen from the player
RING_ELEV_MAX = 58.0
LAUNCH_CLEAR_RADIUS = 3.0   # no rings this close to where the kite launches
RING_MIN_SPACING = 2.7      # ring centres at least this far apart (rings have radius 1.3)
RING_MIN_DIST = 7.0
RING_EDGE_MARGIN = 1.5      # rings sit this far inside the line's reach
RING_MIN_Y = 4.0


class LevelParams:
    __slots__ = ("level", "wind_speed", "gustiness", "line_max", "ring_count",
                 "bird_interval", "bird_speed")

    def __init__(self, level):
        n = level - 1
        self.level = level
        self.wind_speed = min(5.0 + 0.45 * n, 8.0)       # m/s at 10 m height
        self.gustiness = min(0.20 + 0.06 * n, 0.50)      # fraction of base speed
        self.line_max = min(15.0 + 1.0 * n, 20.0)        # metres of line
        self.ring_count = min(3 + level, 9)
        self.bird_interval = max(16.0 - 2.0 * n, 6.0)    # seconds between birds
        self.bird_speed = min(3.0 + 0.4 * n, 6.0)        # m/s


def level_params(level):
    return LevelParams(level)
