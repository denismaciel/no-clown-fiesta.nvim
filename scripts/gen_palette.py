#!/usr/bin/env python3
"""Derive palette.json (semantic schema shared with lumiere.nvim) from palettes.lua.

palettes.lua is the source of truth. Run this after editing it:

    python3 scripts/gen_palette.py            # rewrite palette.json
    python3 scripts/gen_palette.py --check    # exit 1 if palette.json is stale

The output follows the role names used by denismaciel/lumiere.nvim so that
ghostty, tmux, starship and friends can consume either colorscheme through
the same contract.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PALETTES_LUA = ROOT / "lua" / "no-clown-fiesta" / "palettes.lua"
PALETTE_JSON = ROOT / "palette.json"

ANSI_NAMES = (
    "ansi_black",
    "ansi_red",
    "ansi_green",
    "ansi_yellow",
    "ansi_blue",
    "ansi_magenta",
    "ansi_cyan",
    "ansi_white",
    "ansi_bright_black",
    "ansi_bright_red",
    "ansi_bright_green",
    "ansi_bright_yellow",
    "ansi_bright_blue",
    "ansi_bright_magenta",
    "ansi_bright_cyan",
    "ansi_bright_white",
)
SEMANTIC_NAMES = (
    "none",
    "black",
    "white",
    "background",
    "background_inactive",
    "background_error",
    "surface",
    "surface_subtle",
    "surface_raised",
    "surface_selected",
    "surface_overlay",
    "text",
    "text_strong",
    "text_secondary",
    "text_muted",
    "text_faint",
    "text_invisible",
    "text_on_accent",
    "punctuation",
    "border",
    "border_strong",
    "red",
    "red_bg",
    "orange",
    "orange_bg",
    "yellow",
    "yellow_bg",
    "green",
    "green_bg",
    "cyan",
    "cyan_bg",
    "blue",
    "blue_bg",
    "magenta",
    "magenta_bg",
    "search_bg",
)
EXPECTED_NAMES = (*SEMANTIC_NAMES, *ANSI_NAMES)


def parse_lua_palettes(source: str) -> dict[str, dict[str, str]]:
    palettes: dict[str, dict[str, str]] = {}
    block = re.compile(r"^\s{2}(\w+) = \{\n(.*?)^\s{2}\},", re.S | re.M)
    entry = re.compile(r'(\w+) = "([^"]+)"')
    for name, body in block.findall(source):
        palettes[name] = {key: value.lower() for key, value in entry.findall(body)}
    return palettes


def rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def hex_(channels: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(channel))):02x}" for channel in channels)


def mix(first: str, second: str, amount: float) -> str:
    a = rgb(first)
    b = rgb(second)
    return hex_(tuple(a[i] + (b[i] - a[i]) * amount for i in range(3)))


def semantic(p: dict[str, str]) -> dict[str, str]:
    bg = p["bg"]
    fg = p["fg"]

    def tint(accent: str) -> str:
        # Matches the subtlety of the upstream accent_red/green/blue tints.
        return mix(bg, accent, 0.05)

    def bright(accent: str) -> str:
        return mix(accent, "#ffffff", 0.2)

    return {
        "none": "NONE",
        "black": bg,
        "white": fg,
        "background": bg,
        "background_inactive": p["alt_bg"],
        "background_error": p["accent_red"],
        "surface": p["alt_bg"],
        "surface_subtle": p["accent"],
        "surface_raised": p["accent"],
        "surface_selected": p["gray"],
        "surface_overlay": p["accent"],
        "text": fg,
        "text_strong": mix(fg, "#ffffff", 0.5),
        "text_secondary": p["light_gray"],
        "text_muted": p["medium_gray"],
        "text_faint": mix(p["medium_gray"], p["gray"], 0.5),
        "text_invisible": p["gray"],
        "text_on_accent": p["cursor_fg"],
        "punctuation": p["light_gray"],
        "border": p["gray"],
        "border_strong": p["medium_gray"],
        "red": p["red"],
        "red_bg": p["accent_red"],
        "orange": p["orange"],
        "orange_bg": tint(p["orange"]),
        "yellow": p["yellow"],
        "yellow_bg": tint(p["yellow"]),
        "green": p["green"],
        "green_bg": p["accent_green"],
        "cyan": p["cyan"],
        "cyan_bg": tint(p["cyan"]),
        "blue": p["blue"],
        "blue_bg": p["accent_blue"],
        "magenta": p["magenta"],
        "magenta_bg": tint(p["magenta"]),
        "search_bg": p["orange"],
        "ansi_black": bg,
        "ansi_red": p["red"],
        "ansi_green": p["green"],
        "ansi_yellow": p["yellow"],
        "ansi_blue": p["blue"],
        "ansi_magenta": p["magenta"],
        "ansi_cyan": p["cyan"],
        "ansi_white": fg,
        "ansi_bright_black": p["medium_gray"],
        "ansi_bright_red": bright(p["red"]),
        "ansi_bright_green": bright(p["green"]),
        "ansi_bright_yellow": bright(p["yellow"]),
        "ansi_bright_blue": bright(p["blue"]),
        "ansi_bright_magenta": bright(p["magenta"]),
        "ansi_bright_cyan": bright(p["cyan"]),
        "ansi_bright_white": "#ffffff",
    }


def build() -> dict[str, dict[str, str]]:
    lua = parse_lua_palettes(PALETTES_LUA.read_text(encoding="utf-8"))
    output = {"dark": semantic(lua["dark"])}
    for mode, colors in output.items():
        assert tuple(colors) == EXPECTED_NAMES, f"{mode}: schema drifted"
        for name, value in colors.items():
            if name != "none":
                assert re.fullmatch(r"#[0-9a-f]{6}", value), f"{mode}.{name}={value}"
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if palette.json is stale")
    args = parser.parse_args()

    rendered = json.dumps(build(), indent=2) + "\n"
    if args.check:
        current = PALETTE_JSON.read_text(encoding="utf-8") if PALETTE_JSON.exists() else ""
        if current != rendered:
            print("palette.json is stale; run scripts/gen_palette.py", file=sys.stderr)
            return 1
        return 0

    PALETTE_JSON.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
