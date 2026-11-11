# KiteGame

> "We have concluded that the trivial mathematics is, on the whole, useful, and that the real mathematics, on the whole, is not."
> G.H. Hardy (probably talking about my code)

## What is this?

I'm Austin, a backend developer who was learning "advanced Python" until I hit the stage where I no longer know what I know, what I don't, or why `*args` and `**kwargs` made sense at 3 AM.

So I decided to build a game. Nothing says "I understand async/await" like rendering palm trees in real time.

## How it got here

This started as Beach Buggy Racing, which the world did not need. Another racing game. Then I wondered why race on a beach when you could fly a kite on one, and that was that.

I'm pivoting to a kite flying simulator for three reasons:
1. It's slightly more original.
2. Wind physics sounded fun. They are not.
3. I've put in six hours already and sunk cost is my love language.

You'll still find `BeachBuggy` classes and `sand_friction` variables all over the codebase. Pretend they're kites. It's a feature.

## Tech stack (things I googled)

- Python 3.x, because I still can't escape the whitespace wars
- Flask and SocketIO for the real-time connection (I copied it from a tutorial)
- Eventlet, monkey patching included. Yes, we literally patch monkeys. No, I don't know why.
- HTML5 Canvas, where SVGs either render nicely or turn into invisible rectangles
- JavaScript, because no Python dev's suffering is complete without it

## Why TDD?

I'm big on test-driven development, to an annoying degree. I write the tests first and Google "how to make test pass" afterwards.

That's why the project has 47 TODOs and 3 working features. Those 3 features do have 95% test coverage, though. The rest, we'll cross that `AssertionError` when we get to it.

## Current status

```python
class ProjectStatus(Enum):
    BEACH_BUGGY = "deprecated"  # RIP 2024-2024
    KITE_GAME = "in_progress"    # Current delusion
    ACTUALLY_WORKS = "not_found"  # Maybe someday
```

What works:
- The server starts, about half the time.
- You can see something on screen.
- Tests exist. They don't pass, but they exist.

What doesn't:
- The game concept
- Physics (the wind goes swoosh and the kite goes thunk)
- Level progression, which freezes the car. Yes, the kite. Don't ask.
- My grasp of promises vs observables vs async

What I'm unsure about: whether I'm building a game or a cry for help, why Python has 14 ways to do the same thing, and whether anyone will play this.

## Issues

I wrote up a bunch of GitHub issues to steer this toward completion. A few favorites:

- #1: "I defined the same class twice because copy-paste is my debugging strategy"
- #7: "Level progression freezes the car" (in a kite game)
- #10: "I wrote an entire EventSystem and forgot to use it"

The rest are in the [Issues tab](https://github.com/aueskinj/KiteGame/issues).

## Installation

```bash
# Clone it
git clone https://github.com/yourusername/KiteGame.git
cd KiteGame

# Make a virtual environment (global installs are for anarchists)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run it
python app.py
```

Then open `http://localhost:5000` and lower your expectations.

## Running tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=game tests/

# Verbose, for when you want to question your life choices
pytest -v
```

What you'll probably see:
```
======================== test session starts =========================
collected 0 items

========================= no tests ran in 0.01s ======================
```

I said I was big on TDD. I never said I was good at it.

## How to play (in theory)

Controls:
- Arrow keys move the kite (or the buggy, depending on the commit)
- `Ctrl+R` restarts. You'll need it.
- `Ctrl+C` exits the game and the existential crisis
- `Ctrl+Z` undoes life choices, depending on your OS

The goal is to fly the kite through something (clouds? air currents?), collect something (points? wind? validation?) and avoid something (birds? obstacles? reality?). I'll fill in the details once I know what this game is.

## Blog

I'm writing the whole thing up on Medium, since misery likes company: [medium.com/@austinkmhi](https://medium.com/@austinkmhi)

Planned posts:
- "Why I Rewrote the Same Class Twice (And Still Got It Wrong)"
- "Wind Physics: A Love Story (Spoiler: It's Toxic)"
- "10 Ways to Debug WebSocket Issues (Number 7 Will Make You Cry)"
- "I Tried Test-Driven Development and Now I Have 0 Features and 100 Tests"

## Contributing

Found a bug? Of course you did. There are dozens of us.

Open an issue, send a PR (I'll review it between existential crises), or roast my code. I'm dead inside anyway. All code is guilty until proven innocent by tests.

## Philosophy

The Hardy quote up top is basically my motto if you swap "mathematics" for "programming projects."

Is this game useful? No. Is it fun to work on? Weirdly, yes. Will anyone play it? Probably not. Will I finish it? `TODO: implement motivation`

## License

MIT. The code is bad enough that it should be free. Port it to Rust, rewrite it in TypeScript, use it as a cautionary tale. I've stopped caring.

## If you read this far

You're probably one of these:
1. A recruiter (hi, I'm more competent than this README suggests)
2. A developer who knows this chaos
3. My dad (thanks for the support, dad)
4. Lost (check your `sys.path`)

Code is temporary, but bugs are forever. Now I'm going to go write more tests that won't fix anything but will feel like progress.

---

Status: compiles sometimes
Test coverage: aspirational
Sanity level: `None` (get it? because Python?)
Kite flying accuracy: about as good as my understanding of decorators

## Links

- [GitHub Issues](https://github.com/aueskinj/KiteGame/issues): where dreams go to die
- [Tests](./tests/): `FileNotFoundError: [Errno 2] No such file or directory`
- [Documentation](./docs/): coming soon
- [My Medium](https://medium.com/@austinkmhi): misery loves company

PS: There's a `game_state_clean.py` because I tried to fix `game_state.py` and made it worse. It's the "before" photo in a weight-loss ad, with no "after."

PPS: Yes, eventlet monkey patching is controversial. Yes, I'm using it anyway. No questions, please.

PPPS: The kite SVG took 3 hours. The game logic took 45 minutes. Priorities.
