"""Kite physics, from first principles.

The kite is a point mass in a vertical plane (x downwind, y up) with a flat
plate for a sail. Four things act on it:

1. Gravity.
2. Aerodynamic force from the air moving past the sail. We use the flat plate
   model: pressure force acts perpendicular to the plate, proportional to the
   square of the air speed *normal* to the plate:

       F_n = 1/2 * rho * A * Cn * (u . n) * |u . n| * n

   where u = wind - kite_velocity is the air velocity relative to the kite.
   Tilting the plate to the flow splits that force into lift and drag
   automatically, and lift fades at steep angles (stall). No lookup tables.
   A little skin friction along the plate plus drag from the tail and bridle
   keeps the kite from sliding forever.
3. The line: an inextensible string that can pull but not push. Modelled as a
   constraint |kite - anchor| <= length. The tension is the impulse needed to
   hold that constraint, divided by the time step.
4. Nothing else. Orientation is not a force.

Orientation: the kite hangs from a bridle. While the line is taut, the bridle
holds the sail at a fixed angle `beta` away from perpendicular-to-the-line, so
beta is what the player changes with up and down. Smaller beta puts the sail
nearer the line direction's perpendicular and the kite flies higher; larger
beta lays it flatter and it sinks. A critically damped spring turns the sail
toward that target, which gives it some inertia. With a slack line there is no
bridle pull, so the kite weathervanes: it points into the relative wind at a
natural trim angle.
"""

import math

from .vec import Vec2, wrap_angle, clamp


class Controls:
    """Held-key state. left/right reel the line in/out, up/down tilt the kite."""

    __slots__ = ("left", "right", "up", "down")

    def __init__(self, left=False, right=False, up=False, down=False):
        self.left = bool(left)
        self.right = bool(right)
        self.up = bool(up)
        self.down = bool(down)

    def __repr__(self):
        return "Controls(left=%r, right=%r, up=%r, down=%r)" % (
            self.left, self.right, self.up, self.down)


class KiteParams:
    rho = 1.2            # air density, kg/m^3
    g = 9.81             # m/s^2
    mass = 0.08          # kg
    area = 1.0           # sail area, m^2
    plate_cn = 1.28      # normal force coefficient of a flat plate
    plate_cf = 0.02      # skin friction coefficient along the plate
    body_area = 0.02     # tail + bridle drag area, m^2
    body_cd = 1.0
    spring_omega = 8.0   # rad/s, how fast the sail swings toward its target
    spring_zeta = 1.0    # damping ratio (1 = critically damped)
    trim_alpha = math.radians(30.0)  # free-flight angle of attack
    beta_min = math.radians(12.0)
    beta_max = math.radians(50.0)
    beta_default = math.radians(30.0)
    beta_rate = math.radians(40.0)   # rad/s while a tilt key is held
    reel_speed = 3.5     # m/s
    line_min = 3.0       # m


def plate_force(theta, u, p=KiteParams):
    """Aerodynamic force on the sail.

    theta: direction of the sail's chord (nose direction), radians.
    u: air velocity relative to the kite.
    """
    c = Vec2(math.cos(theta), math.sin(theta))   # along the chord
    n = Vec2(c.y, -c.x)                          # normal to the plate
    un = u.dot(n)
    ut = u.dot(c)
    q = 0.5 * p.rho * p.area
    force = n * (q * p.plate_cn * un * abs(un)) + c * (q * p.plate_cf * ut * abs(ut))
    speed = u.length()
    force = force + u * (0.5 * p.rho * p.body_area * p.body_cd * speed)
    return force


class Kite:
    def __init__(self, pos, vel=None, theta=math.pi - math.radians(30.0),
                 line_len=10.0, beta=None, params=KiteParams):
        self.p = params
        self.pos = Vec2(pos.x, pos.y)
        self.vel = vel.copy() if vel is not None else Vec2(0.0, 0.0)
        self.theta = theta
        self.omega = 0.0
        self.beta = params.beta_default if beta is None else beta
        self.line_len = line_len
        self.tension = 0.0   # newtons, averaged over the last advance()
        self.slack = 0.0     # metres of line that are not taut
        self._last_tension = 0.0

    # --- helpers ---------------------------------------------------------

    def elevation(self, anchor):
        d = self.pos - anchor
        return math.atan2(d.y, d.x)

    # --- stepping --------------------------------------------------------

    def advance(self, dt, controls, wind_at, anchor, line_max, t=0.0, substeps=4):
        """Advance the kite by dt seconds.

        wind_at(x, y, t) -> Vec2 gives the wind. Controls are applied once per
        call; the physics runs `substeps` smaller steps for stability.
        """
        p = self.p
        if controls.up:
            self.beta -= p.beta_rate * dt
        if controls.down:
            self.beta += p.beta_rate * dt
        self.beta = clamp(self.beta, p.beta_min, p.beta_max)

        reel = 0.0
        if controls.right:
            reel += p.reel_speed
        if controls.left:
            reel -= p.reel_speed

        h = dt / substeps
        total = 0.0
        for i in range(substeps):
            w = wind_at(self.pos.x, self.pos.y, t + i * h)
            self._substep(h, reel, w, anchor, line_max)
            total += self._last_tension
        self.tension = total / substeps

    def _substep(self, h, reel, wind, anchor, line_max):
        p = self.p

        # Forces and semi-implicit Euler integration.
        u = wind - self.vel
        force = plate_force(self.theta, u, p)
        force.y -= p.mass * p.g
        self.vel = self.vel + force * (h / p.mass)
        self.pos = self.pos + self.vel * h

        # The line: change its length, then enforce |pos - anchor| <= length.
        new_len = clamp(self.line_len + reel * h, p.line_min, line_max)
        l_dot = (new_len - self.line_len) / h
        self.line_len = new_len

        d = self.pos - anchor
        dist = d.length()
        impulse = 0.0
        if dist > self.line_len:
            n = d / dist
            self.pos = anchor + n * self.line_len
            vr = self.vel.dot(n)  # speed along the line, outward positive
            if vr > l_dot:        # the line stops the kite moving outward faster than it pays out
                dv = vr - l_dot
                self.vel = self.vel - n * dv
                impulse = p.mass * dv
            dist = self.line_len
        self._last_tension = impulse / h
        self.slack = self.line_len - dist

        # Orientation: spring toward the bridle target (taut) or the trim angle (slack).
        r = self.pos - anchor
        eps = math.atan2(r.y, r.x) if r.length() > 1e-9 else math.pi / 2.0
        theta_taut = eps + math.pi / 2.0 + self.beta
        flow = u if u.length() > 0.1 else wind
        phi_flow = math.atan2(flow.y, flow.x)
        theta_slack = phi_flow + math.pi - p.trim_alpha
        w_taut = clamp((dist - (self.line_len - 0.6)) / 0.6, 0.0, 1.0)
        target = theta_slack + w_taut * wrap_angle(theta_taut - theta_slack)

        diff = wrap_angle(target - self.theta)
        wn = p.spring_omega
        alpha = wn * wn * diff - 2.0 * p.spring_zeta * wn * self.omega
        self.omega += alpha * h
        self.theta = wrap_angle(self.theta + self.omega * h)
