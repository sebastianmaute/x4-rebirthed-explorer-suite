# X4 Rebirthed Explorer Suite

A single, **X4: Foundations v9.00-compatible** extension that merges JanPanthera's six
2023-era "Explorer" mods into one mod, fully rebranded and de-conflicted.

> **Based on [JanPanthera's Explorer mods](https://www.nexusmods.com/x4foundations) (GPL).**
> Merge, de-confliction and v9 update by **sebastianmaute**. Distributed under **GPLv3**
> (see [`LICENSE`](LICENSE)), the same license as the originals.

## What it does

Each feature is a ship **order** you assign from the ship's behaviour menu. All five plus the
shared script library now live in one extension:

| Feature | What it does |
|---|---|
| **Abandoned Ship Explorer** | Find, mark, or board abandoned ships across the galaxy. |
| **Another Explorer** | Explore a sector or the whole galaxy, seeking stations, jump gates, accelerators and superhighways. |
| **Data Vault Explorer** | Mark all data vaults with navigation beacons. |
| **Spiral Explorer** | Uncover the fog in a sector or across the entire galaxy. |
| **Trade Subscription Explorer** | Auto-update station trade subscriptions in a sector or galaxy-wide. |
| *Script Library* | Shared aiscript library the features build on (folded in — no separate dependency). |

## Why a merge?

The six originals each shipped their own `<diff>` patches against the **same vanilla order
scripts** (`order.dock.wait`, `order.assist`). Installed together they **silently conflicted** —
X4 diff patches fail soft, so the last-loaded copy of each file won, dropping the others' hooks.
This suite reconciles every patch into **one unified diff per vanilla order**, fixing that
latent conflict, and updates a vanilla-selector that **changed in v9** (the 2023 `order.assist`
selector no longer matched, which would have silently disabled three features).

## Install

1. Download this repository (or a release).
2. Copy the **`x4_rebirthed_explorer_suite/`** folder into your X4 `extensions/` directory:
   - Steam: `…/steamapps/common/X4 Foundations/extensions/x4_rebirthed_explorer_suite/`
3. Enable it in-game under **Extensions**. Requires **X4 v9.00** (`<dependency version="900"/>`).

The extension folder is loose (no `.cat`/`.dat`) and loads as-is — X4 reads `content.xml`
directly from the folder.

## Build from source

`scripts/build_merged_mod.py` is the deterministic, re-runnable build that produced the
extension: it assembles the six sources, reconciles the order diffs, applies the `x4re_`
rebrand, and fixes the v9 selector drift.

Rebuilding requires the **original six JanPanthera mods** unpacked under `mods/JP_*` (not
redistributed here — get them from their source) plus Python 3.13:

```bash
python scripts/build_merged_mod.py   # regenerates x4_rebirthed_explorer_suite/
```

Packing to a `.cat`/`.dat` for distribution is done with
[x4cat](https://github.com/sebastianmaute) (`x4cat pack`); the loose folder above is enough to
play.

## License

GPLv3 — see [`LICENSE`](LICENSE). This is a derivative work of JanPanthera's GPL-licensed
mods and is released under the same terms. Original author: **JanPanthera**.
