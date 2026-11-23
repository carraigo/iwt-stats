#!/usr/bin/env python3
"""Turn the Issues with Tissues saved data into data.json for the guild web page.

The game writes the addon's data to
  WTF\\Account\\<ACCOUNT>\\SavedVariables\\IssuesWithTissues.lua
when you log out or /reload. This reads that file and writes a tidy JSON file
the page can show. No extra packages needed: Python 3.8+ only.

  python export.py "C:\\Program Files (x86)\\World of Warcraft\\_forever_\\WTF\\Account\\<ACCOUNT>\\SavedVariables\\IssuesWithTissues.lua" site\\data.json
  python export.py <saved file> site\\data.json --watch    (re-export whenever the game saves)
  add --push to also commit data.json and push it with git (run from inside the site repo; this
  is what tools\\autostart.bat sets up). With --watch --push the site is pushed at most once per
  refresh window (PUSH_WINDOWS below, this PC's local time): the first save in a window pushes at
  once; later saves update data.json here and go out when the next window starts.
  tools\\publish.bat always pushes straight away.

It also keeps perf.json next to data.json: one entry per play session (the addon's session stats,
saved at logout and /reload: memory, catch-up, traffic, errors, sizes; numbers only), the last
PERF_KEEP of them, for the performance page (perf.html).
"""
import subprocess
import json
import os
import re
import sys
import time

# Refresh windows, as start hours in local time: 00:00-08:00, 08:00-16:00 and 16:00-00:00.
PUSH_WINDOWS = [0, 8, 16]
# Sessions kept in perf.json (about 1 KB each).
PERF_KEEP = 300
# The window last pushed in, kept next to this file so a restart of the watcher remembers it.
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_push")


def window_of(t=None):
    """(date, start hour) of the refresh window holding time t (local time)."""
    lt = time.localtime(t)
    start = max(h for h in PUSH_WINDOWS if h <= lt.tm_hour)
    return "%04d-%02d-%02d %02d:00" % (lt.tm_year, lt.tm_mon, lt.tm_mday, start)


def next_window_text(t=None):
    """"16:00" (or "00:00" for midnight): when the next window starts."""
    lt = time.localtime(t)
    later = [h for h in PUSH_WINDOWS if h > lt.tm_hour]
    return "%02d:00" % (later[0] if later else PUSH_WINDOWS[0])


def last_window():
    try:
        return open(STATE, encoding="utf-8").read().strip()
    except OSError:
        return ""


def remember_window(w):
    try:
        with open(STATE, "w", encoding="utf-8") as f:
            f.write(w)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# A small reader for the Lua tables WoW saves (strings, numbers, booleans, nil, tables).
# ---------------------------------------------------------------------------
class LuaReader:
    def __init__(self, text):
        self.s, self.i = text, 0

    def ws(self):
        s, n = self.s, len(self.s)
        while self.i < n:
            c = s[self.i]
            if c in " \t\r\n,;":
                self.i += 1
            elif s.startswith("--", self.i):
                j = s.find("\n", self.i)
                self.i = n if j < 0 else j + 1
            else:
                break

    def value(self):
        self.ws()
        c = self.s[self.i]
        if c == "{":
            return self.table()
        if c == '"' or c == "'":
            return self.string()
        m = re.compile(r"-?(?:0x[0-9a-fA-F]+|\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+)").match(self.s, self.i)
        if m:
            self.i = m.end()
            t = m.group(0)
            if "x" in t.lower():
                return int(t, 16)
            f = float(t)
            return int(f) if f.is_integer() and "." not in t and "e" not in t.lower() else f
        for word, val in (("true", True), ("false", False), ("nil", None)):
            if self.s.startswith(word, self.i):
                self.i += len(word)
                return val
        raise ValueError("unexpected %r at %d" % (self.s[self.i:self.i + 20], self.i))

    def string(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        while True:
            c = self.s[self.i]
            if c == q:
                self.i += 1
                return "".join(out)
            if c == "\\":
                self.i += 1
                e = self.s[self.i]
                if e.isdigit():
                    m = re.compile(r"\d{1,3}").match(self.s, self.i)
                    out.append(chr(int(m.group(0))))
                    self.i = m.end()
                    continue
                out.append({"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "\n": "\n"}.get(e, e))
                self.i += 1
            else:
                out.append(c)
                self.i += 1

    def table(self):
        self.i += 1  # {
        d, arr = {}, []
        while True:
            self.ws()
            if self.s[self.i] == "}":
                self.i += 1
                break
            if self.s[self.i] == "[":
                self.i += 1
                key = self.value()
                self.ws()
                assert self.s[self.i] == "]"
                self.i += 1
                self.ws()
                assert self.s[self.i] == "="
                self.i += 1
                d[key] = self.value()
            else:
                m = re.compile(r"([A-Za-z_]\w*)\s*=(?!=)").match(self.s, self.i)
                if m:
                    self.i = m.end()
                    d[m.group(1)] = self.value()
                else:
                    arr.append(self.value())
        if arr and not d:
            return arr
        for n, v in enumerate(arr, 1):
            d[n] = v
        return d


def read_saved(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r"^([A-Za-z_]\w*)\s*=\s*", text, re.M):
        r = LuaReader(text)
        r.i = m.end()
        out[m.group(1)] = r.value()
    return out


# ---------------------------------------------------------------------------
# The page's data
# ---------------------------------------------------------------------------
# The addon tracks crafting professions only (since 0.9.0). Older clients may still have shared
# gathering skills, First Aid or Fishing, so anything else is left out here too.
# Cooking was dropped in 1.3.0 (nearly everyone has it).
CRAFTING = {"Alchemy", "Blacksmithing", "Enchanting", "Engineering", "Leatherworking", "Tailoring"}

def recipe_count(r):
    """How many recipes a record lists, in any of the addon's formats:
    1 "id:Name;..."  2 "12345;s7421;nName"  3 "i2b8.1.4;s5q2;nName" (base 36 gaps)."""
    data = r.get("data") or ""
    v = r.get("v") or 1
    tokens = [t for t in data.split(";") if t]
    if v == 1:
        return sum(1 for t in tokens if ":" in t)
    if v == 2:
        return len(tokens)
    n = 0
    for t in tokens:
        if t[0] in "is":
            n += len([g for g in t[1:].split(".") if g])
        elif t[0] == "n":
            n += 1
    return n


def live(db, name):
    recs = ((db.get("sync") or {}).get(name) or {}).get("records") or {}
    return {str(k): r for k, r in recs.items() if isinstance(r, dict) and not r.get("deleted")}


def build(db):
    snap = db.get("snapshot") or {}
    members = {m["name"]: m for m in snap.get("members") or [] if isinstance(m, dict) and m.get("name")}
    in_guild = (lambda n: n in members) if members else (lambda n: True)

    alts = {k: r.get("data") for k, r in live(db, "alts").items() if r.get("data")}
    main_of = lambda n: alts.get(n) or n

    # Kills
    kills = []
    for who, r in live(db, "kills").items():
        m = re.match(r"^(\d+);(\d+);", r.get("data") or "")
        if m and in_guild(who):
            kills.append({"name": who, "hk": int(m.group(1)), "mobs": int(m.group(2))})
    kills.sort(key=lambda k: (-k["hk"], k["name"]))

    # Professions and recipes
    profs = {}
    for who, r in live(db, "profs").items():
        if not in_guild(who):
            continue
        for part in (r.get("data") or "").split(","):
            p = part.split(":")
            if len(p) == 3 and p[1].isdigit() and p[0] in CRAFTING:
                profs.setdefault(p[0], []).append({"name": who, "rank": int(p[1]), "max": int(p[2])})
    recipes = {}
    for key, r in live(db, "recipes").items():
        who, _, prof = key.partition("#")
        if prof in CRAFTING and in_guild(who):
            recipes[(who, prof)] = recipe_count(r)
    crafting = []
    for prof in sorted(set(profs) | {p for _, p in recipes}):
        people = {c["name"]: dict(c) for c in profs.get(prof, [])}
        for (who, p), names in recipes.items():
            if p == prof:
                people.setdefault(who, {"name": who, "rank": None, "max": None})["recipes"] = names
        crafting.append({"profession": prof, "crafters": sorted(people.values(), key=lambda c: -(c.get("rank") or 0))})

    # Polls (one vote per player: the main's newest)
    votes = live(db, "votes")
    polls = []
    for pid, r in live(db, "polls").items():
        m = re.match(r"^(\d+);([^;]*);(.*)$", r.get("data") or "")
        if not m:
            continue
        answers = m.group(2).split("~")
        best = {}
        for who, v in votes.items():
            if not in_guild(who):
                continue
            for pair in (v.get("data") or "").split(","):
                k, _, n = pair.partition("=")
                if k == pid and n.isdigit():
                    main = main_of(who)
                    if main not in best or v.get("rev", 0) > best[main][1]:
                        best[main] = (int(n), v.get("rev", 0))
        counts = [0] * len(answers)
        for n, _ in best.values():
            if 1 <= n <= len(answers):
                counts[n - 1] += 1
        polls.append({"question": m.group(3), "closes": int(m.group(1)), "open": int(m.group(1)) > time.time(),
                      "answers": [{"text": a, "votes": c} for a, c in zip(answers, counts)]})
    polls.sort(key=lambda p: -p["closes"])

    # Donations
    g = (live(db, "dgoal").get("goal") or {})
    m = re.match(r"^(\d+);(\d+);(.*)$", g.get("data") or "")
    goal = None
    if m:
        title, _, owner = m.group(3).rpartition(";") if m.group(3).count(";") else (m.group(3), "", "")
        goal_id = int(m.group(1))
        givers = []
        for who, r in live(db, "donated").items():
            d = re.match(r"^(\d+);(\d+)$", r.get("data") or "")
            if d and int(d.group(1)) == goal_id and int(d.group(2)) > 0 and in_guild(who):
                givers.append({"name": who, "copper": int(d.group(2))})
        givers.sort(key=lambda x: -x["copper"])
        goal = {"title": title or "Guild bank", "target": int(m.group(2)), "owner": owner or g.get("by"),
                "total": sum(x["copper"] for x in givers), "givers": givers}

    # Loot notes
    loot = []
    for _, r in live(db, "loot").items():
        m = re.match(r"^(\d+);([^;]*);(\d*);([^;]*);(.*)$", r.get("data") or "")
        if m:
            loot.append({"time": int(m.group(1)), "player": m.group(2), "itemID": int(m.group(3)) if m.group(3) else None,
                         "item": m.group(4), "note": m.group(5)})
    loot.sort(key=lambda x: -x["time"])

    roster = sorted(({"name": n, "level": m.get("level"), "class": m.get("class"), "classFile": m.get("classFile"),
                      "rank": m.get("rank"), "rankIndex": m.get("rankIndex"), "days": m.get("days"),
                      "main": alts.get(n)} for n, m in members.items()), key=lambda m: (m["rankIndex"] or 99, m["name"]))
    return {
        "generated": int(time.time()),
        "snapshotAt": snap.get("at"),
        "guild": snap.get("guild") or "Issues with Tissues",
        "addonVersion": snap.get("version"),
        "roster": roster,
        "players": len({main_of(n) for n in members}) if members else None,
        "kills": kills,
        "totals": {"hk": sum(k["hk"] for k in kills), "mobs": sum(k["mobs"] for k in kills), "chars": len(kills)},
        "eliteSoldier": kills[0] if kills and kills[0]["hk"] > 0 else None,
        "crafting": crafting,
        "polls": polls,
        "donations": goal,
        "loot": loot,
    }


def perf_path(dst):
    return os.path.join(os.path.dirname(os.path.abspath(dst)), "perf.json")


def export_perf(db, dst):
    """Add this session's stats to perf.json when they're new; True when the file changed."""
    stats = db.get("stats")
    if not isinstance(stats, dict) or not isinstance(stats.get("at"), (int, float)):
        return False
    path = perf_path(dst)
    try:
        hist = json.load(open(path, encoding="utf-8"))
        sessions = hist.get("sessions") or []
    except (OSError, ValueError, AttributeError):
        sessions = []
    if any(x.get("at") == stats["at"] for x in sessions):
        return False
    sessions.append(stats)
    sessions.sort(key=lambda x: x.get("at") or 0)
    sessions = sessions[-PERF_KEEP:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"updated": int(time.time()), "sessions": sessions}, f, ensure_ascii=False, separators=(",", ":"))
    print("%s  added a session to %s (%d kept)" % (time.strftime("%H:%M:%S"), path, len(sessions)))
    return True


def export(src, dst):
    """Write dst (and perf.json); returns False when nothing but the export time would change."""
    db = read_saved(src).get("IwTDB") or {}
    perf_changed = export_perf(db, dst)
    data = build(db)
    try:
        old = json.load(open(dst, encoding="utf-8"))
        same = {k: v for k, v in old.items() if k != "generated"} == {k: v for k, v in data.items() if k != "generated"}
    except (OSError, ValueError):
        same = False
    if same:
        print("%s  no changes" % time.strftime("%H:%M:%S"))
        return perf_changed
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("%s  wrote %s (%d members, %d with kills)" % (time.strftime("%H:%M:%S"), dst, len(data["roster"]), len(data["kills"])))
    return True


def push(dst):
    """Commit dst (and perf.json) and push it; True when something was pushed. Errors are printed, never raised,
    so a watcher keeps running."""
    folder = os.path.dirname(os.path.abspath(dst))
    run = lambda *a: subprocess.run(["git", *a], cwd=folder, capture_output=True, text=True)
    try:
        run("add", os.path.basename(dst))
        if os.path.exists(perf_path(dst)):
            run("add", "perf.json")
        if run("diff", "--cached", "--quiet").returncode == 0:
            return False
        r = run("commit", "-m", "Update guild data")
        r = r if r.returncode else run("push")
        print("%s  %s" % (time.strftime("%H:%M:%S"), "pushed" if r.returncode == 0 else "git failed: " + (r.stderr or r.stdout).strip()))
        return r.returncode == 0
    except OSError as e:
        print("%s  git not found: %s" % (time.strftime("%H:%M:%S"), e))
        return False


def publish(src, dst, pushing, watching):
    """Export, and push when allowed: always without --watch; with it, once per refresh window."""
    changed = export(src, dst)
    if not pushing:
        return
    if not watching:
        if changed:
            push(dst)
        return
    if pending_or(changed):
        try_push(dst)


waiting = False  # data.json changed here but isn't pushed yet


def pending_or(changed):
    global waiting
    waiting = waiting or changed
    return waiting


def try_push(dst):
    """Push if this window hasn't had its push yet; else say when it will go out."""
    global waiting
    w = window_of()
    if last_window() == w:
        print("%s  held until %s (one push per window)" % (time.strftime("%H:%M:%S"), next_window_text()))
        return
    if push(dst):
        remember_window(w)
    waiting = False  # pushed, or nothing new to push


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    pushing = "--push" in sys.argv
    watching = "--watch" in sys.argv
    # data.json may hold changes a previous watcher held back: check at the first chance.
    waiting = pushing and watching
    publish(src, dst, pushing, watching)
    if watching:
        sys.stdout.flush()
        last = os.path.getmtime(src)
        print("Watching for the game to save (Ctrl+C to stop)...")
        while True:
            time.sleep(5)
            # A new window started with data still waiting: send it now.
            if pushing and waiting and last_window() != window_of():
                try_push(dst)
                sys.stdout.flush()
            try:
                now = os.path.getmtime(src)
            except OSError:
                continue
            if now != last:
                last = now
                time.sleep(3)  # let the game finish writing
                try:
                    publish(src, dst, pushing, watching)
                except Exception as e:  # a half-written file: try again on the next save
                    print("%s  export failed: %s" % (time.strftime("%H:%M:%S"), e))
                sys.stdout.flush()
