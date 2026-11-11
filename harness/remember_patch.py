"""Patch only the harness's own keytar interception in a companion copy."""
from pathlib import Path
from .asar import HarnessError

ANCHOR = '  Module._load = function (request, parent, isMain) {'
KEYTAR = '    if (request === "keytar") return memoryKeytar;'


def inject(source):
    if source.count(ANCHOR) != 1 or source.count(KEYTAR) != 1:
        raise HarnessError('Remember-login bootstrap anchor changed')
    hook = Path(__file__).with_name('remember_bootstrap.cjs').read_text()
    return source.replace(ANCHOR, hook + '\n' + ANCHOR, 1).replace(
        KEYTAR, '    if (request === "keytar") return harnessRememberKeytar || memoryKeytar;', 1)
