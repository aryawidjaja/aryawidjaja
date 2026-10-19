"""Profile banner: the name in ASCII on the left, a looping ASCII reel of the work on the right.

    uv run --with fonttools --with brotli assets/banner.py JetBrainsMono-Light.ttf [preview-second]

JetBrains Mono (OFL) is subset to the characters used and embedded, so it renders the same for everyone.
Writes assets/banner-dark.svg and assets/banner-light.svg. With a preview second, writes
assets/preview-<theme>.svg frozen at that moment of the reel instead.
"""
import base64, io, math, random, sys
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont

THEMES = {  # GitHub Primer: fg.default, fg.muted, fg.subtle, accent.fg
    "dark": ("#e6edf3", "#9198a1", "#656c76", "#4493f8"),
    "light": ("#1f2328", "#59636e", "#8c959f", "#0969da"),
}
FS = 14
CW, LH, ASC = FS * 0.6, FS * 1.32, FS * 1.02  # JetBrains Mono: 600 advance, 1020 ascent, 300 descent
PAD, COLS, ROWS = 10, 126, 17
SX = 62                                          # the reel's stage: columns 62-125, rows 0-14, caption on row 16
NOISE = "░▒▓"

NAME = """\
███╗   ███╗██╗   ██╗████████╗ █████╗  ██████╗ ██╗███╗   ██╗
████╗ ████║██║   ██║╚══██╔══╝██╔══██╗██╔═══██╗██║████╗  ██║
██╔████╔██║██║   ██║   ██║   ███████║██║   ██║██║██╔██╗ ██║
██║╚██╔╝██║██║   ██║   ██║   ██╔══██║██║▄▄ ██║██║██║╚██╗██║
██║ ╚═╝ ██║╚██████╔╝   ██║   ██║  ██║╚██████╔╝██║██║ ╚████║
╚═╝     ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝ ╚══▀▀═╝ ╚═╝╚═╝  ╚═══╝"""
SUBTITLE = [(16, "A  R  Y  A  W  I  J  A  Y  A", "f"),
            (15, "Applied ML & Software Engineer", "m"),
            (21, "Jakarta, Indonesia", "m")]

rnd = random.Random(7)
USED, KF, CLS = set(), {}, {}

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def xy(c, r):
    return PAD + c * CW, PAD + r * LH + ASC

def text(c, r, s, cls="", style=""):
    """One run of characters. Leading spaces become an x offset; inner spaces are kept (xml:space)."""
    lead = len(s) - len(s.lstrip(" "))
    s = s.strip(" ")
    if not s:
        return ""
    USED.update(s)
    x, y = xy(c + lead, r)
    return (f'<text x="{x:.1f}" y="{y:.1f}"' + (f' class="{cls}"' if cls else "")
            + (f' style="{style}"' if style else "") + f">{esc(s)}</text>")

def anim(body, dur, timing="linear"):
    """A CSS class running keyframes `body` (a list of (percent, declarations)) forever."""
    body = "".join(f"{p:.3f}%{{{d}}}" for p, d in body)
    name = KF.setdefault(body, f"k{len(KF)}")
    return CLS.setdefault((name, dur, timing), f"z{len(CLS)}")

def lines(art):
    return art.strip("\n").split("\n")

class Scene:
    """Times passed to a scene are seconds from the scene's start; keyframes are placed on the reel's clock."""
    def __init__(self, t0, dur, total):
        self.t0, self.t1, self.T, self.out = t0, t0 + dur, total, []

    def timeline(self, pts):
        pts = sorted((min(max(t, 0), self.T), d) for t, d in pts)
        pts = [(0, pts[0][1])] + pts + [(self.T, pts[-1][1])]
        return anim([(100 * t / self.T, d) for t, d in pts], self.T)

    def window(self, show, hide):
        a = self.t0 + max(show, 0.16)
        b = self.t1 - 0.34 if hide is None else self.t0 + hide
        real = self.timeline([(a - .001, "opacity:0;transform:translateX(6px)"), (a, "opacity:1;transform:translateX(6px)"),
                              (a + .25, "opacity:1;transform:none"), (b, "opacity:1;transform:none"), (b + .001, "opacity:0")])
        noise = self.timeline([(a - .161, "opacity:0"), (a - .16, "opacity:.75"), (a, "opacity:.75"), (a + .001, "opacity:0"),
                               (b, "opacity:0"), (b + .001, "opacity:.75"), (b + .16, "opacity:.75"), (b + .161, "opacity:0")])
        return real, noise

    def put(self, art, c, r, cls="f", show=0, hide=None, noise=True, stagger=0.022):
        """Draw art that scrambles in at `show` and out at `hide` (default: the scene's end)."""
        real, scramble = self.window(show, hide)
        out = []
        for i, line in enumerate(lines(art) if "\n" in art.strip("\n") else [art]):
            style = f"animation-delay:{i * stagger:.3f}s" if i and stagger else ""
            if noise:
                junk = "".join(ch if ch == " " else rnd.choice(NOISE) for ch in line)
                out.append(text(c, r + i, junk, f"a nz {scramble}", style))
            out.append(text(c, r + i, line, f"{cls} {real}", style))
        return "".join(out)

    def move(self, pts, inner):
        """Translate `inner` through (time, columns, rows) points."""
        cls = self.timeline([(self.t0 + t, f"transform:translate({dc * CW:.1f}px,{dr * LH:.1f}px)") for t, dc, dr in pts])
        return f'<g class="{cls}">{inner}</g>'

    def add(self, *parts):
        self.out += parts

def loop(body, dur, inner, delay=0, timing="linear"):
    style = f' style="animation-delay:{delay:.2f}s"' if delay else ""
    return f'<g class="{anim(body, dur, timing)}"{style}>{inner}</g>'

def flip(s, frames, c, r, cls, period, **kw):
    """A flipbook: frames shown in turn, `period` seconds per full cycle."""
    k, out = len(frames), []
    for j, frame in enumerate(frames):
        body = [(0, f"opacity:{int(j == 0)}"), (100 * j / k, "opacity:1"), (100 * (j + 1) / k, "opacity:0"), (100, f"opacity:{int(j == 0)}")]
        out.append(loop(body, period, s.put(frame, c, r, cls, **kw), timing="step-end"))
    return "".join(out)

def bars(heights, rows):
    """Vertical bars from heights in eighths of a row, as `rows` lines of text."""
    return "\n".join("".join(" ▁▂▃▄▅▆▇█"[max(0, min(8, h - (rows - 1 - i) * 8))] for h in heights) for i in range(rows))

TWINKLE = [(0, "opacity:1"), (50, "opacity:.2"), (100, "opacity:1")]
BOB = [(0, "transform:none"), (50, "transform:translateY(-3px)"), (100, "transform:none")]
PULSE = [(0, "opacity:0"), (20, "opacity:1"), (60, "opacity:0"), (100, "opacity:0")]

# ── Scenes ─────────────────────────────────────────────────────────────────────────────────────────────

PLAN = """\
┌─────────────┬──────────┬─────────────┐
│             │          │             │
│  ◎      ◎   │    ◎     │   ◎     ◎   │
│                        │             │
│             │    ⊕     │             │
├──────  ─────┤          ├─────  ──────┤
│             │          │             │
│  ◎      ◎   │          │   ◎     ◎   │
│             └───    ───┘             │
│     ⊕                          ⊕     │
│                                      │
└──────────────────────────────────────┘"""

def takeoff(s):  # Boon: a plan set, symbols counted from one example, then a room's area
    plan, c0, r0 = lines(PLAN), SX + 12, 1
    s.add(s.put(PLAN, c0, r0, "m"))
    syms = [(r, c) for r, l in enumerate(plan) for c, ch in enumerate(l) if ch == "◎"]
    for k, (r, c) in enumerate(syms):
        t = 0.9 + k * 0.17
        s.add(s.put("[◎]", c0 + c - 1, r0 + r, "a", show=t))
    for k, r in enumerate(range(1, 8)):
        row = "".join("░" if plan[r][c] == " " else " " for c in range(15, 25))
        s.add(s.put(row, c0 + 15, r0 + r, "a", show=2.9 + k * 0.1, noise=False))

PHONE = """\
╭───────────╮
│   ─────   │
│           │
│           │
│           │
│           │
│           │
│     ◯     │
╰───────────╯"""
TABLE = """\
┌──────┬──────────┬──────┐
│ ━━━━ │ ━━━━━━   │ ━━━  │
├──────┼──────────┼──────┤
│      │          │      │
│      │          │      │
│      │          │      │
└──────┴──────────┴──────┘"""

def voice(s):  # Boon: an agent calls a driver, and the call becomes rows of data
    s.add(s.put(PHONE, SX + 3, 2, "m"))
    frames = [bars([rnd.randint(3, 22) for _ in range(9)], 3) for _ in range(5)]
    s.add(flip(s, frames, SX + 5, 4, "a", 0.75))
    for k in range(3):
        s.add(loop(PULSE, 1.2, s.put("╲\n │\n ╱", SX + 18 + k * 3, 5, "f"), delay=k * 0.25))
    s.add(s.put(TABLE, SX + 30, 3, "m"))
    for row in range(3):
        for k, (c, w) in enumerate([(32, 6), (39, 10), (50, 6)]):
            s.add(s.put("━" * rnd.randint(2, w - 2), SX + c, 6 + row, "a", show=1.2 + (row * 3 + k) * 0.2))

FLY_BODY = """\
        ▄███▄        
       ▐█████▌       
  ╲╲   ▐█████▌   ╱╱  
    ══▐███████▌══    
      ▐███████▌      
       ▐█▓█▓█▌       
        ▓█▓█▓        
  ╱╱     ▀█▀     ╲╲  """
FLY_EYES = "     ▟█▛     ▜█▙     \n    ▜██       ██▛    "
FLY_WINGS = ["""\
                     
   ░░░         ░░░   
  ░░░░░       ░░░░░  
   ░░░░░     ░░░░░   
     ░░░     ░░░     """, """\
░░                 ░░
░░░░░           ░░░░░
 ░░░░░         ░░░░░ 
   ░░░         ░░░   
                     """]

def fly(s):  # fruit-fly connectome flight control: a fly among firing neurons, then off it goes
    for _ in range(46):
        c, r = rnd.randrange(64), rnd.randrange(15)
        if not (19 <= c <= 43 and 1 <= r <= 10):
            ch, cls = rnd.choice([("·", "s"), ("·", "s"), ("∙", "m"), ("●", "a")])
            s.add(loop(TWINKLE, rnd.uniform(.6, 1.8), s.put(ch, SX + c, r, cls, show=rnd.uniform(.2, .9)), delay=rnd.uniform(0, 1)))
    body = flip(s, FLY_WINGS, SX + 21, 5, "m", 0.14) + s.put(FLY_BODY, SX + 21, 2, "f") + s.put(FLY_EYES, SX + 21, 2, "a")
    s.add(s.move([(0, 0, 0), (3.6, 0, 0), (4.3, 40, -9)], loop(BOB, 1.4, body)))

def car():
    """A low wedge roadster in profile, nose to the right: a filled silhouette over two rows, wheels half tucked in."""
    keys = [(0, 10), (1, 12), (4, 13), (8, 13), (10, 15), (12, 16), (14, 16), (16, 14), (18, 11), (21, 9), (24, 7), (26, 5), (27, 3)]
    h = [next(a + (b - a) * (x - x0) / (x1 - x0) for (x0, a), (x1, b) in zip(keys, keys[1:]) if x0 <= x <= x1) for x in range(28)]
    level = lambda v: " ▁▂▃▄▅▆▇█"[max(0, min(8, round(v)))]
    roof = "".join(level(v - 8) for v in h)
    cabin = range(10, 17)
    paint = "".join(" " if x in cabin else ch for x, ch in enumerate(roof))
    glass = "".join(ch if x in cabin else " " for x, ch in enumerate(roof))
    return paint + "\n" + "".join(level(v) for v in h), glass

def disc(s, cx, cy, size, cls):
    """A round ● of `size` px centred on column cx, row cy (JetBrains Mono: 0.62 em wide, centre 0.30 em in, 0.36 em up)."""
    USED.add("●")
    real, _ = s.window(0, None)
    x, y = PAD + cx * CW - 0.30 * size, PAD + cy * LH + 0.36 * size
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls} {real}" style="font-size:{size}px">●</text>'

PLUME = ["▓▓              ▓▓\n▒▒              ▒▒\n░░              ░░",
         "▓▒              ▒▓\n▒░              ░▒\n░               ░ "]

def roadster(s):  # the rocket roadster: drives in under the name, hops on cold gas, lands, drives off
    paint, glass = car()
    wheels = "".join(disc(s, cx, 1.95, 36, "m") + disc(s, cx, 1.95, 11, "f") for cx in (5.5, 21.5))
    car_art = (s.put("══ ── ─ ·", -11, 1, "s", noise=False) + s.put(paint, 0, 0, "f", noise=False, stagger=0)
               + s.put(glass, 0, 0, "a", noise=False) + wheels
               + s.put("▸", 27, 1, "a", noise=False) + s.put("▐", 0, 1, "a", noise=False))
    plume = flip(s, PLUME, 4.5, 2.7, "a", 0.2, show=2.15, hide=4.05, noise=False, stagger=0)
    s.add(s.move([(0, -36, 12), (2.0, SX + 16, 12), (2.15, SX + 16, 12), (2.7, SX + 19, 4), (3.4, SX + 23, 3),
                  (4.05, SX + 27, 12), (5.2, SX + 80, 12)], car_art + plume))

def forecast(s):  # SentBe: transaction history, a forecast past today, money moving
    s.add(s.put("\n".join(["│"] * 12) + "\n└" + "─" * 52, SX + 4, 0, "m", stagger=0.01))
    heights = [int(34 + 16 * math.sin(k / 1.7) + k * 1.9 + rnd.uniform(-5, 5)) for k in range(22)]
    for k, h in enumerate(heights):
        col, future = bars([h], 11).split("\n"), k >= 15
        for i, ch in enumerate(col):
            if ch != " ":
                s.add(s.put(ch, SX + 6 + k * 2, 1 + i, "a" if future else "f", show=0.5 + k * 0.1 + (10 - i) * 0.02, noise=False))
    s.add(s.put("┊\n" * 11 + "┴", SX + 35, 0, "s", show=2.0, stagger=0.01))
    for k, ch in enumerate("$€¥£$€"):
        rise = [(0, "opacity:0;transform:none"), (15, "opacity:1"), (80, "opacity:1"), (100, f"opacity:0;transform:translateY({-8 * LH:.0f}px)")]
        s.add(loop(rise, 2.4, s.put(ch, SX + 52 + (k % 3) * 4, 11, "f" if k % 2 else "a", noise=False), delay=k * 0.4))

HOME = " ▄█▄\n▟███▙\n▐█▀█▌"
TREE = "  ▲\n ▲▲▲\n▲▲▲▲▲\n  ▕"
TENT = "   ╱╲\n  ╱  ╲\n ╱ ╱╲ ╲\n╱__╱╲__╲"
DRONE = ["══╤═╤══\n  ╰█╯", "──╤─╤──\n  ╰█╯"]

def drone(s):  # insect-brain drone: leaves home, finds the tent past the trees, comes back
    s.add(s.put("─" * 64, SX, 13, "s"), s.put(HOME, SX + 2, 10, "f"), s.put(TENT, SX + 52, 9, "a"))
    for c in (17, 29, 40):
        s.add(s.put(TREE, SX + c, 9, "m"))
    path = [(0.3, 1, 7), (0.9, 1, 3), (1.9, 24, 1), (2.7, 50, 5), (3.1, 51, 6), (3.3, 51, 6), (4.0, 24, 1), (4.6, 1, 7)]
    for (t, c, r), (t2, c2, r2) in zip(path[:3], path[1:4]):
        for k in range(int(abs(c2 - c) + abs(r2 - r)) // 2):
            f = k / max(1, int(abs(c2 - c) + abs(r2 - r)) // 2)
            s.add(s.put("·", SX + round(c + (c2 - c) * f) + 3, round(r + (r2 - r) * f) + 2, "a", show=t + (t2 - t) * f, noise=False))
    s.add(s.move([(t, c, r) for t, c, r in path], flip(s, DRONE, SX, 0, "f", 0.12)))

AGENT = "╭───╮\n│● ●│\n╰───╯"
CLOUD = "   ╭──╮\n╭──╯  ╰──╮\n┤        ├\n╰────────╯"
LINKS = """\
      ┄┄┄┄┄┄┄┄┄┄┄╮
                 │
                 │
                 │
                 │
      ┄┄┄┄┄┄┄┄┄┄┄┼┄┄┄┄
                 │
                 │
                 │
                 │
      ┄┄┄┄┄┄┄┄┄┄┄╯"""

def memory(s):  # Marrow and Spinal Cloud: agents on many machines, one shared memory
    for r in (1, 6, 11):
        s.add(s.put(AGENT, SX + 1, r, "f"))
    s.add(s.put(LINKS, SX, 2, "s"), s.put(CLOUD, SX + 22, 5, "m"), s.put("┄" * 9, SX + 32, 7, "s"))
    nodes = [(42, 7), (48, 3), (48, 11), (55, 5), (55, 9), (61, 7), (61, 2), (61, 12)]
    edges = [(0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 5), (3, 4), (1, 6), (2, 7), (0, 3)]
    for i, j in edges:
        (c, r), (c2, r2) = nodes[i], nodes[j]
        n = max(abs(c2 - c) // 2, abs(r2 - r))
        for k in range(1, n):
            s.add(s.put("·", SX + round(c + (c2 - c) * k / n), round(r + (r2 - r) * k / n), "s", noise=False))
    for k, (c, r) in enumerate(nodes):
        s.add(s.put("●", SX + c, r, "m"), s.put("◉", SX + c, r, "a", show=1.4 + k * 0.22, noise=False))
    for k, (r, turn) in enumerate([(2, 1), (7, 0), (12, -1)]):
        pts = [(0, "transform:none;opacity:1")]
        if turn:
            pts += [(40, f"transform:translateX({11 * CW:.0f}px)")]
        pts += [(70 if turn else 50, f"transform:translate({11 * CW:.0f}px,{(7 - r) * LH:.0f}px)"),
                (100, f"transform:translate({35 * CW:.0f}px,{(7 - r) * LH:.0f}px);opacity:1")]
        s.add(loop(pts, 1.5, s.put("●", SX + 6, r, "a", noise=False), delay=k * 0.5))

def flock(s):  # Silent Flock: drones that only see each other; a spoofed goal pulls most of them away
    s.add(loop(TWINKLE, 0.6, s.put("✕", SX + 52, 1, "a", show=1.2)), s.put("◇", SX + 61, 8, "f", show=0.6))
    for k in range(15):
        c, r = rnd.randint(1, 13), rnd.randint(4, 11)
        anchor = k < 3
        mid = (c + 18, r - 1 + rnd.randint(-1, 1))
        end = (rnd.randint(55, 59), rnd.randint(7, 9)) if anchor else (rnd.randint(42, 54), rnd.randint(0, 3))
        pts = [(0, 0, 0), (1.6, mid[0] - c, mid[1] - r), (3.6 + rnd.uniform(-.2, .2), end[0] - c, end[1] - r)]
        s.add(s.move(pts, s.put("▸", SX + c, r, "a" if anchor else "f")))

HEAD = """\
     ▄▄▄▄▄▄▄▄
   ▄▀▀        ▀▀▄
  █              ▀▄
 █                 █
 █                  ▀▄
 █                   ▀▄
 ▀▄                 ▄▀
   ▀▄             ▀▄
     █        ▄▄▄▄▀
     █        █"""
BRAIN = "  ░▒▓▓▒░\n ░▒▓██▓▒░\n  ░▒▓▓▒░"

def inner_voice(s):  # Inner Voice Check: signals from the brain become speech that was never spoken aloud
    s.add(s.put(HEAD, SX + 4, 2, "m"))
    s.add(loop(TWINKLE, 1.1, s.put(BRAIN, SX + 8, 4, "a")))
    s.add(s.put("∙ ∙ ∙ ∙", SX + 9, 2, "a", show=0.6))
    for k in range(3):
        s.add(loop(PULSE, 1.2, s.put("╲\n │\n ╱", SX + 26 + k * 3, 6, "f", show=1.0), delay=k * 0.25))
    s.add(s.put("╭───────────────────╮\n│                   │\n│                   │\n╰─┬─────────────────╯\n  ╵", SX + 38, 3, "m", show=1.3))
    for k in range(4):
        s.add(s.put("●", SX + 41 + k * 2, 4, "a", show=1.8 + k * 0.2, hide=2.9))
    s.add(s.put("━━━━ ━━ ━━━━━", SX + 41, 4, "f", show=3.0), s.put("━━━ ━━━━━━", SX + 41, 5, "f", show=3.2))

def call(s):  # Stuart: a customer asks on a call, the answer comes from your code, with sources
    s.add(s.put("╭──────────────────╮\n│                  │\n╰─┬────────────────╯\n  ╵", SX + 1, 1, "m"))
    frames = ["".join(" ▁▂▃▄▅▆▇"[rnd.randint(0, 7)] for _ in range(15)) for _ in range(5)]
    s.add(flip(s, frames, SX + 3, 2, "a", 0.7))
    s.add(s.put("╭─────────────────────────────────────╮\n│                                     │\n│                                     │\n│                                     │\n│                                     │\n╰──────────────────────────────────┬──╯\n                                   ╵", SX + 23, 6, "m", show=1.0))
    for k, (bar, cls) in enumerate([("━━━━━ ━━━━ ━━━━━━━ ━━━  ━━━━", "f"), ("━━━━ ━━━━━━━ ━━  ━━━━━━", "f"), ("{ ━━━ ━━ }", "a"), ("[⌂] [◇] [◈]", "m")]):
        s.add(s.put(bar, SX + 26, 7 + k, cls, show=1.5 + k * 0.45))

def brain():
    """A brain from above: two hemispheres, one outline, a fissure down the middle, folds inside."""
    inside = lambda c, r: any(((c - cx) / 15.5) ** 2 + ((r - 6.5) / 5.6) ** 2 <= 1 for cx in (14, 30))
    cells = []
    for r in range(0, 14):
        for c in range(-2, 48):
            if not inside(c, r):
                continue
            edge = not all(inside(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if c == 22 and edge:
                continue                       # the notches front and back
            ch = "▒" if edge else "│" if c == 22 else rnd.choice("~~≈~ ·") if (c + r) % 2 else " "
            cells.append((c, r, ch))
    return cells

def lesion(s):  # Virtual Neurologist: one part of a simulated brain goes quiet; find which
    dead = lambda c, r: (c - 33) ** 2 / 12 + (r - 8) ** 2 / 2.5 <= 1
    for c, r, ch in brain():
        if ch in "▒│":
            s.add(s.put(ch, SX + 6 + c, r, "m", noise=False))
        elif ch != " ":
            hide = 1.3 if dead(c, r) else None
            s.add(loop(TWINKLE, rnd.uniform(.5, 1.6), s.put(ch, SX + 6 + c, r, "f", hide=hide, noise=False), delay=rnd.uniform(0, 1)))
    lens = s.put("╭───╮\n│   │\n╰───╯╲\n      ╲", 0, 0, "a")
    s.add(s.move([(0, SX + 6, 1), (1.0, SX + 8, 2), (1.9, SX + 22, 8), (2.8, SX + 37, 7), (4.4, SX + 37, 7)], lens))
    s.add(s.put("[         ]", SX + 34, 8, "a", show=2.9))

GLASS = """\
▄▄▄▄▄▄▄▄▄▄▄
╲         ╱
 ╲       ╱
  ╲     ╱
   ╲   ╱
    ╲ ╱
    ╱ ╲
   ╱   ╲
  ╱     ╲
 ╱       ╲
╱         ╲
▀▀▀▀▀▀▀▀▀▀▀"""
def card(a, b):
    return f"╭──────────────────╮\n│ {a:<17}│\n│ {b:<17}│\n╰──────────────────╯"

def sand(level):
    """Hourglass sand for level 0 (all on top) to 4 (all below)."""
    glass = lines(GLASS)
    g = [[" "] * 11 for _ in glass]
    for r in range(1, 6):
        for c in range(r, 11 - r):
            if glass[r][c] == " " and r > level:
                g[r][c] = "░"
    for r in range(6, 11):
        for c in range(11 - r, r):
            if glass[r][c] == " " and r >= 11 - level:
                g[r][c] = "▒"
    if level < 4:
        g[6][5] = g[7][5] = "│"
    return "\n".join("".join(l) for l in g)

def halftime(s):  # Halftime: the usage limit hits, and the break becomes a short course
    s.add(s.put(GLASS, SX + 8, 1, "m"))
    for k in range(5):
        s.add(s.put(sand(k), SX + 8, 1, "a", show=0.3 + k * 0.5, hide=None if k == 4 else 0.8 + k * 0.5, noise=False, stagger=0))
    for k in range(3):
        art = card("━━━━━━━", "━━━━ ━━━━━") if k < 2 else card("◇ ◇ ◆ ◇", "━━━━━━━━")
        s.add(s.move([(0, 30, 0), (1.6 + k * 0.4, 30, 0), (2.0 + k * 0.4, 0, 0)], s.put(art, SX + 28, 1 + k * 4, "f" if k < 2 else "a", show=1.6 + k * 0.4)))

ECG = ["          /\\        ", "   _     /  \\       ", "__/ \\___/    \\   ___", "              \\_/   "]

def heartbeat(s):  # Aimé: a clinic, a heartbeat, the conversation turned into notes
    s.add(s.put("╭" + "─" * 52 + "╮\n" + ("│" + " " * 52 + "│\n") * 9 + "╰" + "─" * 52 + "╯", SX + 2, 1, "m", stagger=0.01))
    s.add(s.put("▕▏\n▁▁▁▁▁▁", SX + 26, 12, "m"))
    trace = "\n".join(l * 6 for l in ECG)
    scroll = [(0, "transform:none"), (100, f"transform:translateX({-20 * CW:.0f}px)")]
    s.add(f'<g clip-path="url(#monitor)">{loop(scroll, 1.6, s.put(trace, SX + 3, 3, "a", noise=False, stagger=0))}</g>')
    s.add(loop(PULSE, 0.8, s.put("◆", SX + 51, 2, "a")))
    s.add(flip(s, ["".join(" ▁▂▃▄▅"[rnd.randint(0, 5)] for _ in range(22)) for _ in range(4)], SX + 5, 8, "f", 0.6, show=0.8))
    s.add(s.put("━━━━ ━━━━━━ ━━━", SX + 33, 8, "m", show=1.6), s.put("━━━━━━ ━━━━", SX + 33, 9, "m", show=2.1))

def bounce_path(duration=3.3, w=58, h=10, vx=15.0, vy=4.6):
    """Run the logo backwards from the top-right corner, so the forward path ends exactly in it."""
    x, y, dx, dy, t, pts = w, 0.0, -vx, vy, 0.0, []
    while t < duration:
        tx = (x / -dx) if dx < 0 else ((w - x) / dx)
        ty = (y / -dy) if dy < 0 else ((h - y) / dy)
        step = min(tx, ty, duration - t)
        x, y, t = x + dx * step, y + dy * step, t + step
        pts.append((t, x, y))
        if step == tx:
            dx = -dx
        if step == ty:
            dy = -dy
    return [(duration - t, x, y) for t, x, y in [(0, w, 0.0)] + pts][::-1]

def corner(s):  # Hit the Corner: the shared screensaver, and the moment it finally hits
    frame = "┌" + "─" * 62 + "┐\n" + ("│" + " " * 62 + "│\n") * 12 + "└" + "─" * 62 + "┘"
    s.add(s.put(frame, SX, 1, "m", stagger=0.01), s.put(frame, SX, 1, "a", show=3.75, hide=4.15, noise=False, stagger=0))
    path = bounce_path()
    pts = [(0.2 + t, x, y) for t, x, y in path]
    hues = ["var(--f)", "var(--a)", "var(--m)"]
    fills = [(s.t0 + t, f"fill:{hues[k % 3]}") for k, (t, _, _) in enumerate(pts)]
    logo = f'<g class="{s.timeline(fills)}">' + s.put("▛▀▀▀▜\n▌ ◈ ▐\n▙▄▄▄▟", SX + 2, 2, "", noise=False, stagger=0) + "</g>"
    s.add(s.move([(t, x, y) for t, x, y in pts], logo))
    for k, (dc, dr) in enumerate([(-3, 1), (-6, 0), (-1, 3), (-4, 3)]):
        s.add(s.put("✶", SX + 62 + dc, 1 + dr, "a", show=3.75 + k * 0.05, hide=4.3, noise=False))

HOUSE = """\
       ▄█▄
     ▄█▀ ▀█▄
   ▄█▀     ▀█▄
 ▄█▀         ▀█▄
▀▀█  ▄▄▄▄▄▄▄  █▀▀
  █  █  ◈  █  █
  █  █     █  █
  █▄▄█▄▄▄▄▄█▄▄█"""

def household(s):  # Buatin: a household's money, piling up where it can be seen
    s.add(s.put(HOUSE, SX + 6, 4, "f"))
    for k, c in enumerate((30, 36, 42, 48, 54)):
        for i in range(2 + k * 2):
            s.add(s.put("▄▄▄", SX + c, 11 - i, "a" if i % 2 else "f", show=0.7 + k * 0.3 + i * 0.06, noise=False))
    drop = [(0, "opacity:0;transform:none"), (10, "opacity:1"), (85, "opacity:1"), (100, f"opacity:0;transform:translateY({6 * LH:.0f}px)")]
    for k in range(3):
        s.add(loop(drop, 1.3, s.put("◉", SX + 37 + k * 6, 0, "a", show=0.4, noise=False), delay=k * 0.4))

def road(s):  # Mata Garuda: a road running toward you, the damage on it found and boxed
    for r in range(2, 15):
        w = (r - 1) * 2.4
        s.add(s.put("╱", SX + round(32 - w), r, "m", stagger=0), s.put("╲", SX + round(32 + w), r, "m", stagger=0))
    s.add(s.put("─" * 64, SX, 1, "s"))
    dashes = ["\n".join("│" if (r // 2) % 2 == p else " " for r in range(13)) for p in (0, 1)]
    s.add(flip(s, dashes, SX + 32, 2, "s", 0.5, noise=False, stagger=0))
    for k, (c, r, hole) in enumerate([(22, 11, "▒▓▓▒\n ▒▒"), (37, 7, "▒▓▒"), (17, 13, "▓▒")]):
        w = max(map(len, lines(hole)))
        s.add(s.put(hole, SX + c, r, "f", show=0.5 + k * 0.3))
        box = "┌" + " " * w + "┐\n" + ("" if "\n" in hole else "") + "└" + " " * w + "┘"
        s.add(loop(TWINKLE, 0.7, s.put(box, SX + c - 1, r - 1, "a", show=1.4 + k * 0.4)))

SCENES = [(takeoff, 6.0, "Computer Vision"), (voice, 4.4, "Voice AI Agents"),
          (fly, 4.6, "Connectomics · Flight Control"), (roadster, 5.4, "Aerospace Simulation"),
          (forecast, 4.8, "Time-Series Forecasting"), (drone, 5.0, "Bio-Inspired Autonomy"),
          (memory, 4.6, "Agent Infrastructure"), (flock, 4.4, "Swarm Robotics"),
          (inner_voice, 4.8, "Brain-Computer Interfaces"), (call, 4.6, "Real-Time RAG"),
          (lesion, 4.6, "LLM Agents for Science"), (halftime, 4.4, "Developer Tools"),
          (heartbeat, 4.2, "Clinical Speech AI"), (corner, 4.6, "Real-Time Web & Payments"),
          (household, 4.0, "Mobile Apps"), (road, 4.2, "Object Detection · GIS")]

# ── Assembly ───────────────────────────────────────────────────────────────────────────────────────────

def name_block():
    out = []
    for r, line in enumerate(lines(NAME), start=2):
        for c, ch in enumerate(line):
            delay = f"animation-delay:{c * 18}ms,{2600 + c * 14}ms"
            if ch == "█":
                x, y = PAD + c * CW, PAD + r * LH
                out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CW + .4:.1f}" height="{LH + .4:.1f}" class="b" style="{delay}"/>')
            elif ch in "▀▄":
                top = 0 if ch == "▀" else .5
                x, y = PAD + c * CW, PAD + (r + top) * LH
                out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CW + .4:.1f}" height="{LH / 2 + .4:.1f}" class="b" style="{delay}"/>')
            elif ch != " ":
                out.append(text(c, r, ch, "ns", delay))
    t = 1150
    for (c, s, cls), r in zip(SUBTITLE, (9, 10, 11)):
        for k, ch in enumerate(s):
            if ch != " ":
                out.append(text(c + k, r, ch, f"w {cls}", f"animation-delay:{t}ms"))
            t += 26
    cursor = text(SUBTITLE[2][0] + len(SUBTITLE[2][1]) + 1, 11, "▍", "cursor")
    return "".join(out), cursor, t

def build(theme, font, preview=None):
    fg, muted, subtle, accent = THEMES[theme]
    total = sum(d for _, d, _ in SCENES)
    reel, t0 = [], 0.0
    for fn, dur, label in SCENES:
        scene = Scene(t0, dur, total)
        fn(scene)
        caption = "   ".join(" ".join(word) for word in label.upper().split(" "))
        scene.add(scene.put(caption, SX + (64 - len(caption)) // 2, 16, "m", show=0.45))
        reel.append(f'<g class="{"sc still" if fn is fly else "sc"}">{"".join(scene.out)}</g>')
        t0 += dur
    name, cursor, typed = name_block()
    css = "".join(f"@keyframes {n}{{{b}}}" for b, n in KF.items())
    css += "".join(f".{c}{{animation:{n} {d}s {tf} infinite both}}" for (n, d, tf), c in CLS.items())
    freeze = f"*{{animation-delay:-{preview}s!important;animation-play-state:paused!important}}" if preview is not None else ""
    w, h = PAD * 2 + COLS * CW, PAD * 2 + ROWS * LH
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" role="img" aria-label="MUTAQIN ARYAWIJAYA. Applied ML and Software Engineer, Jakarta, Indonesia. Beside the name, an ASCII animation cycles through the work: construction plans, a phone call, a fruit fly, a flying car, a forecast, a drone, shared memory, a flock, a brain, and more, each with its field named underneath.">
<title>Mutaqin Aryawijaya</title>
<style>
@font-face{{font-family:J;src:url(data:font/woff2;base64,{font}) format("woff2")}}
svg{{--f:{fg};--m:{muted};--a:{accent}}}
text{{font-family:J,ui-monospace,Menlo,monospace;font-size:{FS}px;font-weight:300;white-space:pre}}
.f,.b{{fill:{fg}}}.m,.ns{{fill:{muted}}}.s{{fill:{subtle}}}.a{{fill:{accent}}}
.b{{animation:rise .55s cubic-bezier(.2,.7,.2,1) backwards,glint-b 7s linear infinite}}
.ns{{animation:rise .55s cubic-bezier(.2,.7,.2,1) backwards}}
@keyframes rise{{from{{opacity:0;transform:translateY(-7px)}}}}
@keyframes glint-b{{0%,7%,100%{{fill:{fg}}}2.5%{{fill:{accent}}}}}
.w{{animation:type .08s linear backwards}}
@keyframes type{{from{{opacity:0}}to{{opacity:1}}}}
.cursor{{fill:{accent};animation:type .08s linear backwards {typed + 100}ms,blink 1.1s step-end {typed + 100}ms infinite}}
@keyframes blink{{50%{{opacity:0}}}}
{css}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.sc:not(.still),.nz{{display:none}}}}
{freeze}
</style>
<defs><clipPath id="monitor"><rect x="{xy(SX + 3, 0)[0]:.1f}" y="{PAD + 2 * LH:.1f}" width="{52 * CW:.1f}" height="{9 * LH:.1f}"/></clipPath></defs>
<g>{name}{cursor}</g>
<g class="reel">{"".join(reel)}</g>
</svg>
'''

def font_face(ttf, chars):
    font = TTFont(ttf)
    missing = sorted(c for c in chars if ord(c) not in font.getBestCmap() and c != " ")
    assert not missing, f"not in the font, would break the grid: {''.join(missing)}"
    s = subset.Subsetter(subset.Options())
    s.populate(text=chars)
    s.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()

if __name__ == "__main__":
    out, preview = Path(__file__).parent, (float(sys.argv[2]) if len(sys.argv) > 2 else None)
    build("dark", "")  # first pass collects every character drawn
    font = font_face(sys.argv[1], "".join(USED | set(NOISE)))
    for theme in THEMES:
        rnd.seed(7); KF.clear(); CLS.clear()
        svg = build(theme, font, preview)
        assert svg.count("<text") > 500
        (out / (f"preview-{theme}.svg" if preview is not None else f"banner-{theme}.svg")).write_text(svg)
        print(theme, f"{len(svg) / 1024:.0f} KB", f"reel {sum(d for _, d, _ in SCENES):.1f}s")
