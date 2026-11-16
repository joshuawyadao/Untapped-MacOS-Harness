"""Guarded STS2-only macOS full-screen window construction repair."""
from .asar import HarnessError

VERSION = 1

WINDOW_OLD = '''    const window = Services.createWindow(`/overlay/${this.routerPath}`, {
      title: "Untapped.gg Overlay",
      frame: false,'''
WINDOW_NEW = '''    const window = Services.createWindow(`/overlay/${this.routerPath}`, {
      ...(process.platform === "darwin" && this.routerPath === "sts2" ? { type: "panel" } : {}),
      title: "Untapped.gg Overlay",
      frame: false,'''


def patch_core(source):
    """Apply the pinned window option without changing visibility/account gates."""
    count = source.count(WINDOW_OLD)
    if count != 1 or WINDOW_NEW in source:
        raise HarnessError(f"Full-screen overlay anchor must occur once (found {count})")
    return source.replace(WINDOW_OLD, WINDOW_NEW, 1)
