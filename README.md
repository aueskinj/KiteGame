# KiteGame 🪁

> "We have concluded that the trivial mathematics is, on the whole, useful, and that the real mathematics, on the whole, is not."  
> — G.H. Hardy (probably talking about my code)

## What Fresh Hell Is This?

Hi, I'm Austin, a self-proclaimed backend developer who was learning "advanced Python" until I hit that beautiful stage where I no longer know what I know, what I don't know, or why I thought `*args` and `**kwargs` made sense at 3 AM.

So naturally, I decided to build a game. Because nothing says "I understand async/await" quite like rendering palm trees in real-time.

## The Origin Story (Or: How I Learned to Stop Worrying and Love the Pivot)

This project started as **Beach Buggy Racing** ... you know, another racing game, because the world definitely needed one more of those. Riveting stuff. Revolutionary. Groundbreaking. *Yawn*.

But then I had an epiphany (or a crisis, hard to tell): **Why race on the beach when you can fly a kite ON the beach?** 

Mind. Blown. 🤯

So I'm pivoting from Beach Buggy to **Kite Flying Simulator** because:
1. It's more original (barely)
2. Wind physics sound fun (they're not)
3. I've already spent 6 hours on this and I'm in too deep to quit now (sunk cost fallacy is my love language)

**Translation:** You'll see a lot of `BeachBuggy` classes and `sand_friction` variables in the codebase. Just pretend they're kites. Use your imagination. It's a feature, not a bug.

## Tech Stack (AKA: Things I Googled)

- **Python 3.x** - Because I still can't escape the whitespace wars
- **Flask + SocketIO** - For that sweet, sweet real-time connection (and definitely not because I copied it from a tutorial)
- **Eventlet** - Monkey patching included! (Yes, we literally patch monkeys. No, I don't know why.)
- **HTML5 Canvas** - Where SVGs go to either render beautifully or become invisible rectangles
- **JavaScript** - Because no Python dev's suffering is complete without also writing JS

## Why TDD? (Test-Driven Development, Not That-Doesn't-Deploy)

I'm **quite big on TDD**. Like, obnoxiously big. The kind of person who writes tests first and then Googles "how to make test pass" later.

You'll see a *lot* of tests before any real code changes. This is intentional. This is the way. This is also why the project has 47 TODOs and 3 working features.

But hey, at least those 3 features have **95% test coverage**. 💪

The rest? Well... we'll cross that `AssertionError` when we get to it.

## Current Status: It's Complicated

```python
class ProjectStatus(Enum):
    BEACH_BUGGY = "deprecated"  # RIP 2024-2024
    KITE_GAME = "in_progress"    # Current delusion
    ACTUALLY_WORKS = "not_found"  # Maybe someday
```

**What works:**
- ✅ The server starts (50% of the time)
- ✅ You can see... something on screen
- ✅ Tests exist (they don't pass, but they exist)

**What doesn't work:**
- ❌ The entire game concept
- ❌ Physics (wind goes *swoosh* but kite goes *thunk*)
- ❌ Level progression (causes mysterious car freezing... yes, the *kite* freezes. Don't ask.)
- ❌ My understanding of promises vs observables vs async

**What I'm not sure about:**
- 🤷 Whether I'm building a game or a cry for help
- 🤷 Why Python has 14 ways to do the same thing
- 🤷 If anyone will actually play this

## The Issues (GitHub AND Existential)

I've created a bunch of GitHub issues that should guide this beautiful trainwreck to completion:

- **Issue #1:** "I defined the same class twice because copy-paste is my debugging strategy"
- **Issue #7:** "Level progression freezes the car" (in a game about kites. Yes.)
- **Issue #10:** "I wrote an entire EventSystem and forgot to use it" (it me)

Check out the [Issues](https://github.com/aueskinj/KiteGame/issues) tab for the full comedy special.

## Installation (Abandon Hope, All Ye Who Enter Here)

```bash
# Clone this masterpiece
git clone https://github.com/yourusername/KiteGame.git
cd KiteGame

# Create virtual environment (because global installs are for anarchists)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate (we don't judge)

# Install dependencies
pip install -r requirements.txt

# Pray to the Python gods
# (Optional but recommended)

# Run the "game"
python app.py
```

Navigate to `http://localhost:5000` and prepare for disappointment!

## Running Tests (The Fun Part)

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest

# Run tests with coverage
pytest --cov=game tests/

# Run tests and question your life choices
pytest -v
```

**Expected output:** 
```
======================== test session starts =========================
collected 0 items

========================= no tests ran in 0.01s ======================
```

Look, I *said* I was big on TDD. I didn't say I was *good* at it yet. Baby steps.

## How to Play (Theoretical)

**Controls:**
- ↑ ↓ ← → : Move kite (or buggy, depending on which commit you're on)
- `Ctrl+R` : Restart (you'll need this)
- `Ctrl+C` : Exit game (and existential crisis)
- `Ctrl+Z` : Undo life choices (OS dependent)

**Objective:**
- Fly the kite through... clouds? Air currents? Existential dread?
- Collect... points? Wind? Validation?
- Don't hit... birds? Obstacles? Reality?

*Details TBD when I figure out what this game actually is.*

## Blog Series: "A Journey Into Madness"

I'm documenting this whole adventure on Medium because misery loves company and developers love reading about other people's failures.

**Follow along at:** [link to Medium](https://medium.com/@austinkmhi)

**Planned posts:**
- "Why I Rewrote the Same Class Twice (And Still Got It Wrong)"
- "Wind Physics: A Love Story (Spoiler: It's Toxic)"
- "10 Ways to Debug WebSocket Issues (Number 7 Will Make You Cry)"
- "I Tried Test-Driven Development and Now I Have 0 Features and 100 Tests"

## Contributing

Found a bug? Of course you did. There are dozens of us. DOZENS!

- Open an issue (add it to the pile)
- Submit a PR (I'll review it between existential crises)
- Roast my code (I'm dead inside anyway)

Just remember: All code is guilty until proven innocent by tests.

## The Philosophy

This project embodies the spirit of that famous G.H. Hardy quote:

> "We have concluded that the trivial mathematics is, on the whole, useful, and that the real mathematics, on the whole, is not."

Replace "mathematics" with "programming projects" and you've got my life motto.

Is this game useful? Absolutely not.  
Is it fulfilling? Surprisingly yes.  
Will anyone play it? Probably not.  
Will I finish it? `TODO: implement motivation`

## License

MIT License - Because this code is so bad it should be free.

Do whatever you want with it. Port it to Rust. Rewrite it in TypeScript. Use it as a cautionary tale. I don't care anymore.

## Final Words

If you've read this far, you're either:
1. A recruiter (hi! I promise I'm more competent than this README suggests)
2. A fellow developer who relates to this chaos
3. My dad (thanks for the support, dad)
4. Lost (check your `sys.path`)

Remember: Code is temporary, but bugs are forever.

Now if you'll excuse me, I have some tests to write that definitely won't make my code work but will make me *feel* like I'm making progress.

---

**Status:** Compiles sometimes  
**Test Coverage:** Aspirational  
**Sanity Level:** `None` (get it? because Python?)  
**Kite Flying Accuracy:** Similar to my understanding of decorators

*Made with 💻, ☕, and that one brain cell working overtime 🧠*

---

## Quick Links

- [GitHub Issues]([./issues.md](https://github.com/aueskinj/KiteGame/issues)) - Where dreams go to die
- [Tests](./tests/) - `FileNotFoundError: [Errno 2] No such file or directory`
- [Documentation](./docs/) - Coming soon™
- [My Medium](link-here) - Misery loves company

**PS:** If you're wondering why there's a `game_state_clean.py` file, it's because I tried to fix `game_state.py` and made it worse. That file is the "before" picture in a weight-loss commercial, except there's no "after."

**PPS:** Yes, I know eventlet monkey patching is controversial. Yes, I'm using it anyway. No, I won't be taking questions at this time.

**PPPS:** The kite SVG took me 3 hours to make. The actual game logic? 45 minutes. Priorities. ✨
