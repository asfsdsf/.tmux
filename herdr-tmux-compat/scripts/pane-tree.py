#!/usr/bin/env python3
"""A tmux choose-tree style workspace/tab/pane navigator for Herdr."""

from __future__ import annotations

import curses
import json
import locale
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from typing import Any


HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
RESULT_PATH = os.environ.get("HERDR_TMUX_PICKER_RESULT", "")
SNAPSHOT_PATH = os.environ.get("HERDR_TMUX_PICKER_SNAPSHOT", "")


@dataclass
class TreeItem:
    kind: str
    label: str
    workspace_id: str
    tab_id: str = ""
    pane_id: str = ""
    parent: str = ""

    @property
    def key(self) -> str:
        return self.pane_id or self.tab_id or self.workspace_id


SGR_PATTERN = re.compile(r"\x1b\[([0-9;:]*)m")
CSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
OSC_PATTERN = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)")


def character_width(character: str) -> int:
    if unicodedata.combining(character):
        return 0
    return 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1


def clip_to_width(text: str, available: int) -> tuple[str, int]:
    kept: list[str] = []
    used = 0
    for character in text:
        width = character_width(character)
        if used + width > available:
            break
        kept.append(character)
        used += width
    return "".join(kept), used


def rgb_for_xterm(index: int) -> tuple[int, int, int]:
    basic = (
        (0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0),
        (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
        (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
        (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
    )
    if index < 16:
        return basic[max(0, index)]
    if index < 232:
        value = index - 16
        levels = (0, 95, 135, 175, 215, 255)
        return levels[value // 36], levels[(value // 6) % 6], levels[value % 6]
    gray = 8 + (max(232, min(255, index)) - 232) * 10
    return gray, gray, gray


def rgb_to_xterm(red: int, green: int, blue: int) -> int:
    best_index = 0
    best_distance = 1 << 62
    for index in range(256):
        candidate = rgb_for_xterm(index)
        distance = sum((left - right) ** 2 for left, right in zip((red, green, blue), candidate))
        if distance < best_distance:
            best_index = index
            best_distance = distance
    return best_index


class AnsiRenderer:
    """Translate common terminal SGR sequences into curses attributes."""

    def __init__(self, screen: Any) -> None:
        self.screen = screen
        self.foreground = -1
        self.background = -1
        self.styles = 0
        self.pairs: dict[tuple[int, int], int] = {}
        self.next_pair = 1

    def reset(self) -> None:
        self.foreground = -1
        self.background = -1
        self.styles = 0

    def usable_color(self, color: int) -> int:
        if color < 0 or not curses.has_colors():
            return -1
        if color < curses.COLORS:
            return color
        red, green, blue = rgb_for_xterm(color)
        candidates = max(1, min(curses.COLORS, 16))
        return min(
            range(candidates),
            key=lambda index: sum(
                (left - right) ** 2
                for left, right in zip((red, green, blue), rgb_for_xterm(index))
            ),
        )

    def color_attribute(self) -> int:
        foreground = self.usable_color(self.foreground)
        background = self.usable_color(self.background)
        if foreground < 0 and background < 0:
            return 0
        key = (foreground, background)
        pair = self.pairs.get(key)
        if pair is None and self.next_pair < curses.COLOR_PAIRS:
            pair = self.next_pair
            try:
                curses.init_pair(pair, foreground, background)
            except curses.error:
                pair = 0
            self.pairs[key] = pair
            self.next_pair += 1
        return curses.color_pair(pair or 0)

    def attribute(self) -> int:
        return self.styles | self.color_attribute()

    def apply_sgr(self, value: str) -> None:
        raw = value.replace(":", ";")
        parameters = [int(item) if item else 0 for item in raw.split(";")] if raw else [0]
        index = 0
        while index < len(parameters):
            code = parameters[index]
            if code == 0:
                self.reset()
            elif code == 1:
                self.styles |= curses.A_BOLD
            elif code == 2:
                self.styles |= curses.A_DIM
            elif code == 3:
                self.styles |= getattr(curses, "A_ITALIC", 0)
            elif code == 4:
                self.styles |= curses.A_UNDERLINE
            elif code == 5:
                self.styles |= curses.A_BLINK
            elif code == 7:
                self.styles |= curses.A_REVERSE
            elif code == 8:
                self.styles |= curses.A_INVIS
            elif code == 22:
                self.styles &= ~(curses.A_BOLD | curses.A_DIM)
            elif code == 23:
                self.styles &= ~getattr(curses, "A_ITALIC", 0)
            elif code == 24:
                self.styles &= ~curses.A_UNDERLINE
            elif code == 25:
                self.styles &= ~curses.A_BLINK
            elif code == 27:
                self.styles &= ~curses.A_REVERSE
            elif code == 28:
                self.styles &= ~curses.A_INVIS
            elif 30 <= code <= 37:
                self.foreground = code - 30
            elif 90 <= code <= 97:
                self.foreground = code - 90 + 8
            elif code == 39:
                self.foreground = -1
            elif 40 <= code <= 47:
                self.background = code - 40
            elif 100 <= code <= 107:
                self.background = code - 100 + 8
            elif code == 49:
                self.background = -1
            elif code in (38, 48) and index + 2 < len(parameters) and parameters[index + 1] == 5:
                if code == 38:
                    self.foreground = parameters[index + 2]
                else:
                    self.background = parameters[index + 2]
                index += 2
            elif code in (38, 48) and index + 4 < len(parameters) and parameters[index + 1] == 2:
                color = rgb_to_xterm(*parameters[index + 2:index + 5])
                if code == 38:
                    self.foreground = color
                else:
                    self.background = color
                index += 4
            index += 1

    def draw_line(self, y: int, x: int, line: str, width: int) -> None:
        line = OSC_PATTERN.sub("", line.replace("\r", ""))
        column = 0
        position = 0
        for match in SGR_PATTERN.finditer(line):
            plain = CSI_PATTERN.sub("", line[position:match.start()])
            plain = "".join(character for character in plain if character == "\t" or ord(character) >= 32)
            plain = plain.expandtabs(4)
            clipped, used = clip_to_width(plain, width - column)
            if clipped:
                try:
                    self.screen.addstr(y, x + column, clipped, self.attribute())
                except curses.error:
                    pass
                column += used
            self.apply_sgr(match.group(1))
            position = match.end()
            if column >= width:
                return
        tail = CSI_PATTERN.sub("", line[position:])
        tail = "".join(character for character in tail if character == "\t" or ord(character) >= 32)
        tail = tail.expandtabs(4)
        clipped, _ = clip_to_width(tail, width - column)
        if clipped:
            try:
                self.screen.addstr(y, x + column, clipped, self.attribute())
            except curses.error:
                pass


def herdr_json(*args: str) -> dict[str, Any]:
    output = subprocess.check_output([HERDR, *args], text=True)
    return json.loads(output)


def load_snapshot() -> dict[str, Any]:
    if SNAPSHOT_PATH:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)["result"]["snapshot"]
    return herdr_json("api", "snapshot")["result"]["snapshot"]


class PaneTree:
    def __init__(self, screen: Any) -> None:
        self.screen = screen
        self.snapshot = load_snapshot()
        self.workspace_expanded = {
            item["workspace_id"] for item in self.snapshot.get("workspaces", [])
        }
        # tmux choose-tree -w starts at window level: sessions are expanded,
        # windows are collapsed until explicitly opened.
        self.tab_expanded: set[str] = set()
        self.selected = 0
        self.offset = 0
        self.preview_cache: dict[str, list[str]] = {}
        self.ansi_renderer: AnsiRenderer | None = None
        self.items: list[TreeItem] = []
        self.rebuild_items(select_current=True)

    def workspace_tabs(self, workspace_id: str) -> list[dict[str, Any]]:
        return [
            tab
            for tab in self.snapshot.get("tabs", [])
            if tab["workspace_id"] == workspace_id
        ]

    def tab_panes(self, tab_id: str) -> list[dict[str, Any]]:
        return [pane for pane in self.snapshot.get("panes", []) if pane["tab_id"] == tab_id]

    def rebuild_items(self, select_current: bool = False) -> None:
        old_key = self.items[self.selected].key if self.items else ""
        items: list[TreeItem] = []
        workspaces = self.snapshot.get("workspaces", [])

        for workspace in workspaces:
            workspace_id = workspace["workspace_id"]
            tabs = self.workspace_tabs(workspace_id)
            expanded = workspace_id in self.workspace_expanded
            marker = "-" if expanded else "+"
            attached = " (attached)" if workspace.get("focused") else ""
            items.append(
                TreeItem(
                    "workspace",
                    f"({workspace['number']}) {marker} {workspace['label']}: "
                    f"{len(tabs)} windows{attached}",
                    workspace_id,
                )
            )
            if not expanded:
                continue

            for tab_index, tab in enumerate(tabs):
                tab_id = tab["tab_id"]
                panes = self.tab_panes(tab_id)
                is_last_tab = tab_index == len(tabs) - 1
                branch = "└─" if is_last_tab else "├─"
                expanded_tab = tab_id in self.tab_expanded
                tab_marker = "-" if expanded_tab else "+"
                flags = "*" if tab.get("focused") else ""
                items.append(
                    TreeItem(
                        "tab",
                        f"    {branch} {tab_marker} {tab['number']}: "
                        f"{tab['label']}{flags} ({len(panes)} panes)",
                        workspace_id,
                        tab_id,
                        parent=workspace_id,
                    )
                )
                if not expanded_tab:
                    continue

                continuation = "       " if is_last_tab else "    │  "
                for pane_index, pane in enumerate(panes):
                    pane_branch = "└─" if pane_index == len(panes) - 1 else "├─"
                    pane_number = pane["pane_id"].rsplit(":p", 1)[-1]
                    title = pane.get("terminal_title_stripped") or pane.get("agent") or "shell"
                    active = "*" if pane.get("focused") else ""
                    items.append(
                        TreeItem(
                            "pane",
                            f"{continuation}{pane_branch} {pane_number}: {title}{active}",
                            workspace_id,
                            tab_id,
                            pane["pane_id"],
                            parent=tab_id,
                        )
                    )

        self.items = items
        desired = self.snapshot.get("focused_tab_id") if select_current else old_key
        if desired:
            for index, item in enumerate(items):
                if item.key == desired:
                    self.selected = index
                    break
            else:
                self.selected = min(self.selected, max(0, len(items) - 1))
        else:
            self.selected = min(self.selected, max(0, len(items) - 1))

    def target_pane(self, item: TreeItem) -> str:
        if item.kind == "pane":
            return item.pane_id

        tab_id = item.tab_id
        if item.kind == "workspace":
            workspace = next(
                (w for w in self.snapshot.get("workspaces", []) if w["workspace_id"] == item.workspace_id),
                None,
            )
            tab_id = workspace.get("active_tab_id", "") if workspace else ""

        layout = next(
            (layout for layout in self.snapshot.get("layouts", []) if layout["tab_id"] == tab_id),
            None,
        )
        if layout and layout.get("focused_pane_id"):
            return layout["focused_pane_id"]
        panes = self.tab_panes(tab_id)
        return panes[0]["pane_id"] if panes else ""

    def preview_lines(self, pane_id: str) -> list[str]:
        if not pane_id:
            return []
        if pane_id not in self.preview_cache:
            try:
                output = subprocess.check_output(
                    [HERDR, "pane", "read", pane_id, "--source", "visible", "--lines", "100", "--format", "ansi", "--raw"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                self.preview_cache[pane_id] = output.splitlines()
            except (OSError, subprocess.CalledProcessError):
                self.preview_cache[pane_id] = ["preview unavailable"]
        return self.preview_cache[pane_id]

    def pane_info(self, pane_id: str) -> dict[str, Any] | None:
        return next(
            (pane for pane in self.snapshot.get("panes", []) if pane["pane_id"] == pane_id),
            None,
        )

    def layout_for_tab(self, tab_id: str) -> dict[str, Any] | None:
        return next(
            (layout for layout in self.snapshot.get("layouts", []) if layout["tab_id"] == tab_id),
            None,
        )

    def pane_label(self, pane_id: str) -> str:
        pane = self.pane_info(pane_id)
        number = pane_id.rsplit(":p", 1)[-1]
        if not pane:
            return f"pane {number}"
        title = pane.get("terminal_title_stripped") or pane.get("agent") or "shell"
        return f"{number}:{title}"

    def draw_preview_box(
        self,
        top: int,
        left: int,
        height: int,
        width: int,
        pane_id: str,
        label: str,
        emphasized: bool = False,
    ) -> None:
        screen_height, screen_width = self.screen.getmaxyx()
        top = max(0, top)
        left = max(0, left)
        height = min(height, screen_height - top - 1)
        width = min(width, screen_width - left)
        if height < 3 or width < 4:
            return

        border_attr = curses.A_BOLD if emphasized else curses.A_DIM
        self.safe_add(top, left, "┌" + "─" * (width - 2) + "┐", width, border_attr)
        for row in range(top + 1, top + height - 1):
            self.safe_add(row, left, "│", 1, border_attr)
            self.safe_add(row, left + width - 1, "│", 1, border_attr)
        self.safe_add(top + height - 1, left, "└" + "─" * (width - 2) + "┘", width, border_attr)

        label_text, _ = clip_to_width(f" {label} ", max(0, width - 4))
        self.safe_add(top, left + 2, label_text, max(0, width - 4), curses.A_BOLD)

        content_height = height - 2
        content_width = width - 2
        preview = self.preview_lines(pane_id)[-content_height:]
        assert self.ansi_renderer is not None
        self.ansi_renderer.reset()
        for row, line in enumerate(preview):
            self.ansi_renderer.draw_line(top + 1 + row, left + 1, line, content_width)

    def draw_workspace_preview(
        self, item: TreeItem, top: int, left: int, height: int, width: int
    ) -> None:
        tabs = self.workspace_tabs(item.workspace_id)
        previews: list[tuple[str, str, bool]] = []
        for tab in tabs:
            layout = self.layout_for_tab(tab["tab_id"])
            focused_pane_id = layout.get("focused_pane_id", "") if layout else ""
            for pane in self.tab_panes(tab["tab_id"]):
                pane_id = pane["pane_id"]
                previews.append(
                    (
                        pane_id,
                        f"{tab['number']}:{tab['label']} / {self.pane_label(pane_id)}",
                        pane_id == focused_pane_id,
                    )
                )
        self.draw_equal_previews(previews, top, left, height, width)

    def draw_equal_previews(
        self,
        previews: list[tuple[str, str, bool]],
        top: int,
        left: int,
        height: int,
        width: int,
    ) -> None:
        if not previews:
            return
        for index, (pane_id, label, emphasized) in enumerate(previews):
            box_left = left + (index * width) // len(previews)
            box_right = left + ((index + 1) * width) // len(previews)
            self.draw_preview_box(
                top,
                box_left,
                height,
                box_right - box_left,
                pane_id,
                label,
                emphasized,
            )

    def draw_tab_preview(
        self, item: TreeItem, top: int, left: int, height: int, width: int
    ) -> None:
        layout = self.layout_for_tab(item.tab_id)
        focused_pane_id = layout.get("focused_pane_id", "") if layout else ""
        previews = [
            (
                pane["pane_id"],
                self.pane_label(pane["pane_id"]),
                pane["pane_id"] == focused_pane_id,
            )
            for pane in self.tab_panes(item.tab_id)
        ]
        self.draw_equal_previews(previews, top, left, height, width)

    def draw_item_preview(
        self, item: TreeItem, top: int, left: int, height: int, width: int
    ) -> None:
        if height < 3 or width < 4:
            return
        if item.kind == "workspace":
            self.draw_workspace_preview(item, top, left, height, width)
        elif item.kind == "tab":
            self.draw_tab_preview(item, top, left, height, width)
        else:
            self.draw_preview_box(
                top,
                left,
                height,
                width,
                item.pane_id,
                self.pane_label(item.pane_id),
                True,
            )

    def move_to_parent(self) -> None:
        if not self.items:
            return
        parent = self.items[self.selected].parent
        if not parent:
            return
        for index, item in enumerate(self.items):
            if item.key == parent:
                self.selected = index
                return

    def collapse_or_parent(self) -> None:
        item = self.items[self.selected]
        if item.kind == "workspace" and item.workspace_id in self.workspace_expanded:
            self.workspace_expanded.remove(item.workspace_id)
            self.rebuild_items()
        elif item.kind == "tab" and item.tab_id in self.tab_expanded:
            self.tab_expanded.remove(item.tab_id)
            self.rebuild_items()
        else:
            self.move_to_parent()

    def expand_or_child(self) -> None:
        item = self.items[self.selected]
        if item.kind == "workspace" and item.workspace_id not in self.workspace_expanded:
            self.workspace_expanded.add(item.workspace_id)
            self.rebuild_items()
        elif item.kind == "tab" and item.tab_id not in self.tab_expanded:
            self.tab_expanded.add(item.tab_id)
            self.rebuild_items()
        elif self.selected + 1 < len(self.items):
            child = self.items[self.selected + 1]
            if child.parent == item.key:
                self.selected += 1

    def list_height(self, height: int) -> int:
        desired = len(self.items) + 1
        return max(4, min(desired, max(4, height // 2)))

    def safe_add(self, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
        if width <= 0:
            return
        try:
            self.screen.addnstr(y, x, text, width, attr)
        except curses.error:
            pass

    def draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        list_height = self.list_height(height)
        visible_height = max(1, list_height - 1)

        if self.selected < self.offset:
            self.offset = self.selected
        elif self.selected >= self.offset + visible_height:
            self.offset = self.selected - visible_height + 1

        for screen_row, item_index in enumerate(range(self.offset, min(len(self.items), self.offset + visible_height))):
            item = self.items[item_index]
            attr = curses.A_REVERSE if item_index == self.selected else curses.A_NORMAL
            if item.kind == "workspace":
                attr |= curses.A_BOLD
            self.safe_add(screen_row, 0, item.label.ljust(width), width, attr)

        separator_y = min(list_height, height - 2)
        if separator_y >= 0:
            self.safe_add(separator_y, 0, "─" * width, width, curses.A_DIM)

        if self.items and separator_y + 1 < height - 1:
            item = self.items[self.selected]
            header = f" {item.kind}: {item.label.strip()} "
            self.safe_add(separator_y, 2, header, max(0, width - 4), curses.A_BOLD)
            self.draw_item_preview(
                item,
                separator_y + 1,
                0,
                max(0, height - separator_y - 2),
                width,
            )

        status = " ↑/↓ j/k move   ←/→ h/l collapse/expand   Enter choose   q/Esc cancel "
        self.safe_add(height - 1, 0, status.ljust(width), width, curses.A_REVERSE)
        self.screen.refresh()

    def run(self) -> str:
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        self.ansi_renderer = AnsiRenderer(self.screen)
        curses.curs_set(0)
        self.screen.keypad(True)
        while True:
            self.draw()
            key = self.screen.getch()
            if key in (ord("q"), 27):
                return ""
            if key in (curses.KEY_UP, ord("k")):
                self.selected = max(0, self.selected - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                self.selected = min(len(self.items) - 1, self.selected + 1)
            elif key in (curses.KEY_PPAGE,):
                self.selected = max(0, self.selected - max(1, self.list_height(self.screen.getmaxyx()[0]) - 2))
            elif key in (curses.KEY_NPAGE,):
                self.selected = min(len(self.items) - 1, self.selected + max(1, self.list_height(self.screen.getmaxyx()[0]) - 2))
            elif key in (curses.KEY_HOME, ord("g")):
                self.selected = 0
            elif key in (curses.KEY_END, ord("G")):
                self.selected = max(0, len(self.items) - 1)
            elif key in (curses.KEY_LEFT, ord("h")):
                self.collapse_or_parent()
            elif key in (curses.KEY_RIGHT, ord("l"), ord(" ")):
                self.expand_or_child()
            elif key in (curses.KEY_ENTER, 10, 13):
                return self.target_pane(self.items[self.selected]) if self.items else ""


def write_result(pane_id: str) -> None:
    if not RESULT_PATH:
        return
    temporary = f"{RESULT_PATH}.tmp.{os.getpid()}"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(f"{pane_id}\n")
    os.replace(temporary, RESULT_PATH)


def main() -> int:
    locale.setlocale(locale.LC_ALL, "")
    if "--dump" in sys.argv:
        tree = PaneTree(None)
        for item in tree.items:
            print(f"{item.kind}\t{item.key}\t{item.label}")
        return 0
    selected = ""
    try:
        selected = curses.wrapper(lambda screen: PaneTree(screen).run())
    finally:
        write_result(selected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
