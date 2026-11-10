"""Exact STS2 settings menu gate for the pinned renderer bundle."""

from .asar import HarnessError


SETTINGS_UI_ENTRY = "dist/renderer/assets/Main-DlHDXYoX.js"

UI_OLD = '''    content: Sts2Settings,
    platforms: ["win32", "linux"],
    requireLogin: {
      franchise: "STS2"
    },'''
UI_NEW = '''    content: Sts2Settings,
    platforms: ["win32", "linux", "darwin"],
    requireLogin: {
      franchise: "STS2"
    },'''


def patch_settings_ui(source: str) -> str:
    """Allow the pinned STS2 settings menu on macOS, once and only once."""
    count = source.count(UI_OLD)
    if count != 1:
        raise HarnessError(f"STS2 settings UI anchor must occur once (found {count})")
    return source.replace(UI_OLD, UI_NEW, 1)
