"""Deterministic random numbers, built from scratch.

Why not the `random` module? Two reasons: the output of this one is the same on
every Python version and platform, and it is small enough to read in a minute.
Same seed in, same game out, which is what makes the physics testable.
"""

MASK32 = 0xFFFFFFFF


def hash32(x):
    """Scramble an integer into a well-mixed 32-bit integer (murmur3 finalizer)."""
    x &= MASK32
    x ^= x >> 16
    x = (x * 0x85EBCA6B) & MASK32
    x ^= x >> 13
    x = (x * 0xC2B2AE35) & MASK32
    x ^= x >> 16
    return x


class XorShift32:
    """Marsaglia's xorshift32 generator, seeded through hash32."""

    def __init__(self, seed):
        self.state = hash32(seed) or 0x9E3779B9  # state must never be zero
        for _ in range(8):  # warm up so small seeds do not look alike
            self.next_u32()

    def next_u32(self):
        x = self.state
        x ^= (x << 13) & MASK32
        x ^= x >> 17
        x ^= (x << 5) & MASK32
        self.state = x
        return x

    def random(self):
        """Float in [0, 1)."""
        return self.next_u32() / 4294967296.0

    def uniform(self, a, b):
        return a + (b - a) * self.random()

    def randint(self, a, b):
        """Integer in [a, b], both ends included."""
        return a + int(self.random() * (b - a + 1))

    def choice(self, seq):
        return seq[int(self.random() * len(seq))]
