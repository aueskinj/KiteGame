# KiteGame

> "We have concluded that the trivial mathematics is, on the whole, useful, and that the real mathematics, on the whole, is not."
> G.H. Hardy

A kite flying game with real (if simplified) kite physics. The server simulates the wind, the kite and the line. The browser draws it. Everything is written from scratch on the Python and JavaScript standard libraries, so there is nothing to `pip install`.

The old Flask, SocketIO and Eventlet version is gone. The monkey patching went with it.

## Run it

```bash
python app.py            # then open http://localhost:5000
python app.py --port 8080 --host 0.0.0.0
```

Python 3.8 or newer. It was written and tested on 3.13, and it uses nothing newer than `ThreadingHTTPServer`.

## How to play

| Key | Does |
|---|---|
| Left / Right (or A / D) | Reel the line in / pay it out |
| Up / Down (or W / S) | Tilt the kite steeper (climbs, pulls harder) / flatter (sinks, pulls less) |
| Enter | Play again after game over |

On a phone or tablet, on-screen buttons appear.

Fly through the gold rings to clear a level. Grabbing rings in quick succession builds a combo (up to x5). Two things cost a life:

- **The line snaps.** Hold the tension gauge in the red for about a third of a second and the line goes. Reel out or tilt flatter to ease off.
- **Birds.** They cross the screen. Hit one and you lose a life.

You get three lives and a couple of seconds of protection after every relaunch. Each level brings stronger, gustier wind, a longer line, more rings and more birds, up to a cap.

## How it works

The server owns the game. The browser sends held keys, receives state 30 times a second, and draws it.

**Physics** (`game/kite.py`). The kite is a point mass in a vertical plane with a flat plate for a sail. The force on the plate is the standard flat plate model, pressure proportional to the square of the air speed normal to the plate. Tilting the plate against the flow splits that force into lift and drag on its own, and lift fades at steep angles, so stalling falls out of the math with no lookup tables. The line is a hard constraint: the kite cannot be farther from your hand than the line is long, and line tension is the impulse needed to enforce that. A slack line has zero tension. The sail turns toward the angle the bridle sets (taut line) or weathervanes into the wind (slack line) through a critically damped spring.

**Wind** (`game/wind.py`). Wind speed grows with height (power law profile) and gusts come from smooth value noise that travels downwind, so a gust you see approaching actually arrives. There is a weaker independent up and down draft.

**Determinism** (`game/rng.py`). A small xorshift generator replaces `random`. The same seed and the same inputs give the same game on any machine, which is what makes the physics and the level logic testable.

**Network** (`server/websocket.py`, `server/app.py`). A WebSocket implementation written to RFC 6455: handshake, masking, the three length encodings, fragmentation, ping/pong and close, validated against the RFC's own worked examples. Each connection gets its own thread and its own private game, stepped at a fixed 60 Hz. The server refuses cross-origin upgrades, caps connections at 64, rejects unmasked or oversized frames, and ignores malformed input.

**Client** (`static/`). Plain HTML and Canvas. It keeps the last two snapshots and glides between them, so motion stays smooth at any refresh rate.

### Project layout

```
app.py              entry point
game/
  vec.py            2D vector
  rng.py            deterministic random numbers
  wind.py           wind field
  kite.py           kite and line physics
  world.py          ring placement, birds
  config.py         constants and the difficulty curve
  state.py          the game: rules, collisions, scoring, levels
server/
  websocket.py      RFC 6455 framing
  app.py            HTTP + WebSocket server, one session per player
static/
  index.html
  game.js           rendering, input, interpolation
tests/              91 tests
```

## Tests

```bash
python -m unittest discover -s tests -t .
# or, if you have it:
python -m pytest
```

They cover the vector math, the random generator, the wind, the physics (the line never stretches, a kite flies in steady wind and falls in none, more wind means more tension), the game rules (scoring, combos, level progression, lives, snapping, game over and restart), ring placement across 2,400 generated levels, the WebSocket framing, and a live server on a random port that gets handshakes, garbage input, a bad origin and path traversal attempts.

Level progression has a regression test. The old game froze when you finished a level. This one keeps flying.

## Tuning

Everything you would want to change lives in two places.

- `game/config.py`: lives, snap threshold, combo window, ring size and spacing, and `LevelParams` for how wind, line length, rings and birds scale per level.
- `class KiteParams` in `game/kite.py`: mass, sail area, drag, how fast the sail swings, reel speed. If you change these, run `pytest`. The flight tests will tell you if the kite stopped flying.

## Message protocol

Client to server, JSON text frames:

```json
{"type": "input", "left": false, "right": true, "up": false, "down": false}
{"type": "restart"}
```

`restart` only does anything on the game over screen. Non-boolean values and unknown message types are ignored.

Server to client:

```json
{"type": "init", "view": {...}, "anchor": {...}, "snap_tension": 16.0, "tick_hz": 60}
{"type": "state", "t": 12.3, "phase": "flying", "level": 2, "score": 700, "lives": 3,
 "kite": {...}, "wind": {...}, "rings": [...], "birds": [...], "events": [...]}
```

`init` arrives once on connect. `state` arrives about 30 times a second. `phase` is `flying`, `level_complete` or `game_over`. `events` lists what happened since the last snapshot (`ring`, `life_lost`, `level_complete`, `level_start`, `game_over`).

## Known limits

- Game state lives in memory. Closing the tab ends the game and nothing is saved, so there is no high score table yet.
- One process, one thread per player. Measured at 30 simultaneous players with every one getting a steady 30 snapshots per second, but this is not built for thousands.
- There is no sound.
- The physics is 2D. Real kites also move sideways, which this one cannot.

## License

MIT. Do whatever you want with it.
