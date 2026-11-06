# Warcraft III Online

https://wc3.uplay2.ru/ — DotA Classic (including NewYear) and LoD leaderboards.

GitHub Pages publishes main:/docs. The VDS exports public statistics every two minutes; SQLite/account data, IPs, credentials, maps and game binaries are never published.

Rating policy v1 was approved on 2026-11-07. Each completed 5v5 of ten distinct humans is replayed chronologically. Team Elo starts at 1000, K=50 (equal teams ±25); no individual KDA modifier to MMR. XP is 50 completion +50 victory + up to50 contribution; level L starts at100*(L-1)^2 XP. General match results remain separate from rated totals. Classic/NewYear share one rating, LoD has its own.

Public usernames preserve PvPGN spelling while identity joins stay case-insensitive. Hero names are extracted from the exact hash-verified map metadata. Source archive reference pages are retained in the owner's local project, removed from public navigation and current website files. Original Warcraft artwork belongs to its authors; corporate Blizzard logos are omitted.

Backend source is in tools/. Install only reviewed, checksum-verified pinned versions into /opt/warcraft-iii-online/ladder; the disposable checkout is overwritten by synchronization. Do not put secrets or client files in this repository.
