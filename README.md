# Issues with Tissues stats

A small public page for the Issues with Tissues guild on WoW: Forever: guild kill totals, the Elite Soldier, crafters by profession, the donation goal, polls and loot notes.

**Live page:** https://carraigo.github.io/iwt-stats/

## How it works

WoW addons can't reach the internet, but the game saves each addon's data to disk on logout or `/reload`. The [Issues with Tissues addon](https://github.com/carraigo/issues-with-tissues) shares guild data between members, so one player's saved file holds the whole guild's picture.

1. `tools/export.py` reads `WTF\Account\<ACCOUNT>\SavedVariables\IssuesWithTissues.lua` and writes `data.json`. It needs Python 3.8 or newer and nothing else.
2. `index.html` loads `data.json` and draws the page. GitHub Pages serves both from `main`.

## Updating the page

After logging out of the game (or a `/reload`), run:

```
tools\publish.bat
```

It exports the data, commits `data.json` and pushes. The page updates about a minute later.

**Automatic:** run `tools\autostart.bat` once. It starts a hidden watcher, now and at every Windows login, that exports and pushes whenever the game saves (logout or `/reload`). It only pushes when the guild data actually changed. `tools\autostart.bat off` turns it off, and `tools\watch.log` shows what it did.

To export by hand: `py -3 tools\export.py "<path to IssuesWithTissues.lua>" data.json`, with `--watch` to re-export every time the game saves.

## What's published

Character names, levels, classes, ranks, honourable and creature kills, professions and recipe counts, poll results, the donation goal and loot notes. Officer notes are never saved or published.

© 2026 Issues with Tissues. All rights reserved.
