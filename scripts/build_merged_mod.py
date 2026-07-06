#!/usr/bin/env python3
"""Assemble x4_rebirthed_explorer_suite from the six read-only mods/JP_* sources.

Two-pass: (A) assemble merged tree with ORIGINAL names/content, reconciling
duplicate order diffs into unions and merging experiences/icons/t; (B) apply
ordered string renames to every file, then rename files per the map.
Deterministic — safe to re-run (wipes target first).
"""
from __future__ import annotations
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "mods"
DST = ROOT / "x4_rebirthed_explorer_suite"

MODS = [
    "JP_ScriptLibrary",
    "JP_AbandonedShipExplorer",
    "JP_AnotherExplorer",
    "JP_DataVaultExplorer",
    "JP_SpiralExplorer",
    "JP_TradeSubscriptionExplorer",
]

# Ordered (find, replace) — see plan "Rename map". Order is significant.
REPLACEMENTS: list[tuple[str, str]] = [
    ("JP_AbandonedShipExplorerG", "x4re.AbandonedShipExplorer.global"),
    ("JP_AnotherExplorerG", "x4re.AnotherExplorer.global"),
    ("JP_AnotherExplorerS", "x4re.AnotherExplorer.solo"),
    ("JP_DataVaultExplorerG", "x4re.DataVaultExplorer.global"),
    ("JP_SpiralExplorerG", "x4re.SpiralExplorer.global"),
    ("JP_SpiralExplorerS", "x4re.SpiralExplorer.solo"),
    ("JP_TradeSubscriptionExplorerG", "x4re.TradeSubscriptionExplorer.global"),
    ("JP_TradeSubscriptionExplorerS", "x4re.TradeSubscriptionExplorer.solo"),
    ("JP_AbandonedShipExplorer_MD", "x4re_AbandonedShipExplorer_MD"),
    ("JP_AnotherExplorer_MD", "x4re_AnotherExplorer_MD"),
    ("JP_DataVaultExplorer_MD", "x4re_DataVaultExplorer_MD"),
    ("JP_SpiralExplorer_MD", "x4re_SpiralExplorer_MD"),
    ("JP_TradeSubscriptionExplorer_MD", "x4re_TradeSubscriptionExplorer_MD"),
    ("JP_ScriptLibrary_MD", "x4re_ScriptLibrary_MD"),
    ("jp.lib.", "x4re.lib."),
    ("jp.", "x4re."),
    ("jp_", "x4re_"),
    ("JP_", "X4RE_"),
    ("8888888", "28900000"),
]

# Basename renames for files (order.* untouched).
def rename_basename(name: str) -> str:
    m = {
        "JP_AbandonedShipExplorerG.xml": "x4re.AbandonedShipExplorer.global.xml",
        "JP_AnotherExplorerG.xml": "x4re.AnotherExplorer.global.xml",
        "JP_AnotherExplorerS.xml": "x4re.AnotherExplorer.solo.xml",
        "JP_DataVaultExplorerG.xml": "x4re.DataVaultExplorer.global.xml",
        "JP_SpiralExplorerG.xml": "x4re.SpiralExplorer.global.xml",
        "JP_SpiralExplorerS.xml": "x4re.SpiralExplorer.solo.xml",
        "JP_TradeSubscriptionExplorerG.xml": "x4re.TradeSubscriptionExplorer.global.xml",
        "JP_TradeSubscriptionExplorerS.xml": "x4re.TradeSubscriptionExplorer.solo.xml",
    }
    if name in m:
        return m[name]
    if name.startswith("jp.lib."):
        return "x4re.lib." + name[len("jp.lib."):]
    if name.startswith("jp.") and name.endswith(".md.xml"):
        return "x4re." + name[len("jp."):]
    return name


def apply_replacements(text: str) -> str:
    for find, repl in REPLACEMENTS:
        text = text.replace(find, repl)
    return text


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# ---- Pass A helpers -------------------------------------------------------

def assemble_aiscripts() -> None:
    """Copy every non-order aiscript; dedupe identical order stubs; union diffs."""
    order_dock_wait: list[str] = []
    order_assist: list[str] = []
    seen_identical: dict[str, str] = {}  # basename -> content (must match)
    copied: dict[str, str] = {}  # basename -> content; guards accidental overwrite

    for mod in MODS:
        adir = SRC / mod / "aiscripts"
        if not adir.is_dir():
            continue
        for f in sorted(adir.glob("*.xml")):
            name = f.name
            content = read(f)
            if name == "order.dock.wait.xml":
                order_dock_wait.append((mod, content))
            elif name == "order.assist.xml":
                order_assist.append((mod, content))
            elif name in ("order.dock.xml", "order.move.follow.xml", "order.move.wait.xml"):
                # identical trio across nothing but the library; keep one copy
                if name not in seen_identical:
                    seen_identical[name] = content
                    write(DST / "aiscripts" / name, content)
                elif seen_identical[name] != content:
                    raise RuntimeError(
                        f"{name} differs between sources (found in {mod}); "
                        "the identical-trio assumption is violated"
                    )
            else:
                if name in copied and copied[name] != content:
                    raise RuntimeError(
                        f"aiscript basename collision: {name} differs between "
                        f"sources (also in {mod}); a later mod would overwrite an earlier one"
                    )
                copied[name] = content
                write(DST / "aiscripts" / name, content)

    write(DST / "aiscripts" / "order.dock.wait.xml",
          apply_v9_selector_fixes("order.dock.wait.xml", union_diff(order_dock_wait)))
    write(DST / "aiscripts" / "order.assist.xml",
          apply_v9_selector_fixes("order.assist.xml", union_diff(order_assist)))


def union_diff(variants: list[tuple[str, str]]) -> str:
    """Merge multiple <diff> files into one by concatenating their <add> blocks."""
    header = ('<?xml version="1.0" encoding="utf-8"?>\n\n'
              '<diff xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
              'xsi:noNamespaceSchemaLocation='
              '"http://x4dynlib.access.ly\\libraries\\aiscripts.xsd">\n')
    blocks: list[str] = []
    add_re = re.compile(r"<add\b.*?</add>", re.DOTALL)
    for mod, content in variants:
        adds = [m.group(0).strip() for m in add_re.finditer(content)]
        if not adds:
            continue
        body = "\n   ".join(adds)
        blocks.append(f"   <!-- from {mod} -->\n   {body}")
    return header + "\n" + "\n\n".join(blocks) + "\n\n</diff>\n"


# ---- v9 compatibility fixes -----------------------------------------------
# `validate-schema` only checks element/attribute *names*, not whether a
# <diff> `sel=` still matches anything in vanilla — X4 diffs fail SOFT
# (a non-matching <add> is silently dropped, no error at load time). So a
# vanilla attribute-value drift between game versions can silently break a
# patch even though nothing looks "wrong" structurally.
#
# Confirmed via `x4cat extract` of v9.00 vanilla `aiscripts/order.assist.xml`
# (2026-07-06): vanilla's do_if value gained a
# "(@$orderdef and $createdefaultorder?) or " prefix versus the 2023-era
# source mods, so the union's `sel="//do_if[@value='not $order.requiredskill
# or (this.combinedskill ge $order.requiredskill)']"` no longer matches any
# node in v9 and all three feature <add> blocks (AnotherExplorer,
# SpiralExplorer, TradeSubscriptionExplorer) would be silently dropped.
# `order.dock.wait.xml`'s selectors (//params, //create_order[...], //init,
# //interrupts) were re-checked against the same v9 extract and still match.
V9_SELECTOR_FIXES: dict[str, tuple[str, str]] = {
    "order.assist.xml": (
        "not $order.requiredskill or (this.combinedskill ge $order.requiredskill)",
        "(@$orderdef and $createdefaultorder?) or not $order.requiredskill or "
        "(this.combinedskill ge $order.requiredskill)",
    ),
}


def apply_v9_selector_fixes(name: str, text: str) -> str:
    """Patch known vanilla-drift `sel=` selectors so unioned <add> blocks still match."""
    fix = V9_SELECTOR_FIXES.get(name)
    if fix is None:
        return text
    old, new = fix
    if old not in text:
        raise RuntimeError(
            f"{name}: expected v9-selector-fix pattern not found; "
            "vanilla may have changed again or the union content shifted"
        )
    return text.replace(old, new)


def assemble_md() -> None:
    copied: dict[str, str] = {}  # basename -> content; guards accidental overwrite
    for mod in MODS:
        mdir = SRC / mod / "md"
        if not mdir.is_dir():
            continue
        for f in sorted(mdir.glob("*.xml")):
            content = read(f)
            if f.name in copied and copied[f.name] != content:
                raise RuntimeError(
                    f"md basename collision: {f.name} differs between sources "
                    f"(also in {mod}); a later mod would overwrite an earlier one"
                )
            copied[f.name] = content
            write(DST / "md" / f.name, content)


def assemble_libraries() -> None:
    exp_blocks: list[str] = []
    icon_lines: dict[str, str] = {}  # name -> full line (dedupe by name)
    exp_re = re.compile(r"<experience\b.*?</experience>", re.DOTALL)
    icon_re = re.compile(r'<icon\b[^>]*name="([^"]+)"[^>]*>(?:</icon>)?')
    for mod in MODS:
        ldir = SRC / mod / "libraries"
        exp = ldir / "experiences.xml"
        if exp.is_file():
            for m in exp_re.finditer(read(exp)):
                exp_blocks.append("   " + m.group(0).strip())
        ico = ldir / "icons.xml"
        if ico.is_file():
            for m in icon_re.finditer(read(ico)):
                icon_lines.setdefault(m.group(1), "   " + m.group(0).strip())

    write(DST / "libraries" / "experiences.xml",
          '<?xml version="1.0" encoding="utf-8"?>\n\n<experiences>\n'
          + "\n".join(exp_blocks) + "\n</experiences>\n")
    write(DST / "libraries" / "icons.xml",
          '<?xml version="1.0" encoding="utf-8"?>\n\n<icons>\n'
          + "\n".join(icon_lines[k] for k in sorted(icon_lines)) + "\n</icons>\n")


def assemble_t() -> None:
    """Merge t/ per language into a single page 8888888 (renamed later)."""
    t_re = re.compile(r"<t\b.*?</t>", re.DOTALL)
    by_lang: dict[str, list[str]] = {}
    for mod in MODS:
        tdir = SRC / mod / "t"
        if not tdir.is_dir():
            continue
        for f in sorted(tdir.glob("*.xml")):
            entries = ["      " + m.group(0).strip() for m in t_re.finditer(read(f))]
            by_lang.setdefault(f.name, []).extend(entries)
    for fname, entries in by_lang.items():
        m = re.search(r"-L(\d+)\.xml$", fname)
        # 0001.xml has no language attr; 0001-L0NN.xml declares language="NN"
        body = ('<?xml version="1.0" encoding="utf-8"?>\n\n<language id="'
                + (str(int(m.group(1))) if m else "44") + '">\n'
                if m else '<?xml version="1.0" encoding="utf-8"?>\n\n<language id="44">\n')
        page = '   <page id="8888888">\n' + "\n".join(entries) + "\n   </page>\n"
        write(DST / "t" / fname, body + page + "</language>\n")


CONTENT_XML = '''<?xml version="1.0" encoding="utf-8"?>

<content id="x4_rebirthed_explorer_suite" name="X4 Rebirthed Explorer Suite" description="Merged, X4 v9-updated suite of JanPanthera's Explorer mods: abandoned-ship, object, datavault, spiral (fog) and trade-subscription explorers, plus the shared script library. Based on JanPanthera's Explorer mods (GPL)." author="sebastianmaute" version="900" date="2026-07-06" save="0" enabled="1">
   <dependency version="900"/>
</content>
'''

CHANGELOG = '''X4 Rebirthed Explorer Suite
Based on JanPanthera's Explorer mods (GPL): JP_ScriptLibrary, JP_AbandonedShipExplorer,
JP_AnotherExplorer, JP_DataVaultExplorer, JP_SpiralExplorer, JP_TradeSubscriptionExplorer.

v900 (2026-07-06)
- Merged the six mods into one extension; folded JP_ScriptLibrary in (no external dependency).
- Reconciled the divergent vanilla-order diff patches (order.dock.wait, order.assist)
  into one unified diff each, fixing the mutual conflict the six mods had when co-installed.
- Full rebrand to the x4re_ family; text page 8888888 -> 28900000.
- Updated for X4 Foundations v9.00 (dependency version=900).
'''

LICENSE = '''This mod is based on JanPanthera's X4 Explorer mods, which are licensed GPL.
As a derivative work it is distributed under the same GPL terms.
Original author: JanPanthera. Merge/v9 update: sebastianmaute.
'''


def pass_b_rename() -> None:
    """Rewrite every file's content, then rename files per the map."""
    for f in sorted(DST.rglob("*")):
        if f.is_file():
            f.write_text(apply_replacements(read(f)), encoding="utf-8")
    for f in sorted(DST.rglob("*.xml")):
        new = rename_basename(f.name)
        if new != f.name:
            f.rename(f.with_name(new))


def main() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    assemble_aiscripts()
    assemble_md()
    assemble_libraries()
    assemble_t()
    pass_b_rename()
    # Static attribution prose — written AFTER the rename pass so their literal
    # JP_* credits and the "8888888 -> 28900000" note are preserved verbatim.
    write(DST / "content.xml", CONTENT_XML)
    write(DST / "changelog.txt", CHANGELOG)
    write(DST / "LICENSE", LICENSE)
    print(f"Built {DST}")


if __name__ == "__main__":
    main()
