# Issues with Tissues stats

[![Site](https://img.shields.io/website?url=https%3A%2F%2Fcarraigo.github.io%2Fiwt-stats%2F&label=site&up_message=live&down_message=down)](https://carraigo.github.io/iwt-stats/)
[![Pages](https://github.com/carraigo/iwt-stats/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/carraigo/iwt-stats/actions/workflows/pages/pages-build-deployment)
[![Data updated](https://img.shields.io/github/last-commit/carraigo/iwt-stats/main?path=data.json&label=data%20updated)](https://github.com/carraigo/iwt-stats/commits/main/data.json)
[![Addon](https://img.shields.io/github/v/release/carraigo/issues-with-tissues?label=addon)](https://github.com/carraigo/issues-with-tissues/releases/latest)
![Python](https://img.shields.io/badge/python-3.8%2B-3776ab)

A small public page for the Issues with Tissues guild on WoW: Forever: guild kill totals, the Elite Soldier, crafters by crafting profession, the donation goal, polls and loot notes.

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

**Automatic:** run `tools\autostart.bat` once. It starts a hidden watcher, now and at every Windows login, that exports and pushes whenever the game saves (logout or `/reload`). It only pushes when the guild data actually changed, and at most once per refresh window (00:00 to 08:00, 08:00 to 16:00 and 16:00 to 00:00, your PC's time): the first save in a window pushes at once, and later saves wait for the next window. `tools\publish.bat` always pushes straight away. The windows are set at the top of `tools\export.py`. `tools\autostart.bat off` turns it off, and `tools\watch.log` shows what it did.

To export by hand: `py -3 tools\export.py "<path to IssuesWithTissues.lua>" data.json`, with `--watch` to re-export every time the game saves.

## Diagnostics reports

Players can send a report about how the addon runs on their client: `/iwt report` in game, then paste it at [the page's report section](https://carraigo.github.io/iwt-stats/#report). The page checks and shows what's inside, then opens a pre-filled issue in the addon repo (label `diagnostics`), or copies it for Discord. `tools/decode_report.py` turns reports back into JSON.

## Performance page

`perf.html` (not linked from the main page, and hidden from search engines, but public like the rest of the site) charts how the addon ran on the exporting PC, one point per play session: a health score out of 100, memory, start-up time, time to catch up, traffic, records held, problems and the busiest send queue, plus saved size per set. The addon (1.3.0-beta.4 and later) saves these numbers at logout and /reload; the exporter adds each new session to `perf.json` (the last 300) and pushes it with `data.json`. It holds numbers only: no names or chat.

## What's published

Character names, levels, classes, ranks, honourable and creature kills, crafting professions (Alchemy, Blacksmithing, Enchanting, Engineering, Leatherworking and Tailoring; Cooking was dropped in addon 1.3.0) and recipe counts, poll results, the donation goal and loot notes. Gathering skills aren't tracked by the addon and are left out even if an older version shared them. Guild notes, officer notes, guild chat and guild news stay in the game and are never published.

© 2026 Issues with Tissues. All rights reserved.
