"""Carry a deliberately small set of STS2 overlay choices between private runs."""

import json
import os
import re
import secrets
import stat
from contextlib import contextmanager
from pathlib import Path

from .asar import HarnessError

MAX_JSON = 2 * 1024 * 1024
BOOL_KEYS = frozenset({
    "enableOverlay", "showOverlayInBackground", "showTierListHoverTips",
    "enableMerchantGoldLeft", "enableAttackSummary", "enableAncientChoiceStats",
    "enableCardRewardStats", "enableCardUpgradeStats", "enableShopStats",
})
COLORS = frozenset({"ironclad", "silent", "regent", "necrobinder", "defect", "colorless"})
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")


def _directory(path):
    path = Path(path)
    try:
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise HarnessError("Private preferences directory is not canonical")
        info = path.lstat()
    except (OSError, RuntimeError) as exc:
        raise HarnessError("Private preferences directory is unavailable") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise HarnessError("Private preferences directory is not owned mode 0700")
    return path


@contextmanager
def _anchor(path):
    """Pin the selected private root before any leaf operation."""
    path = _directory(path)
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in path.parts[1:]:
            next_descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                      dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise HarnessError("Private preference root changed")
        yield descriptor
    except OSError as exc:
        raise HarnessError("Private preference root cannot be opened safely") from exc
    finally:
        os.close(descriptor)


@contextmanager
def _parent(root_fd, names, *, create=False):
    """Hold each owned descendant directory while opening the next one."""
    descriptor = os.dup(root_fd)
    try:
        for name in names:
            if name not in ("sts2", "tier-lists"):
                raise HarnessError("Unexpected private preference directory")
            if create:
                try:
                    os.mkdir(name, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            next_descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                      dir_fd=descriptor)
            info = os.fstat(next_descriptor)
            if info.st_uid != os.getuid() or info.st_mode & 0o022:
                os.close(next_descriptor)
                raise HarnessError("Private preference ancestor is unsafe")
            os.close(descriptor)
            descriptor = next_descriptor
        yield descriptor
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise HarnessError("Private preference ancestor cannot be opened safely") from exc
    finally:
        os.close(descriptor)


def _read_at(root_fd, names):
    """Read one bounded, owned regular file relative to pinned directory handles."""
    try:
        with _parent(root_fd, names[:-1]) as parent:
            try:
                fd = os.open(names[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=parent)
            except FileNotFoundError:
                return None
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise HarnessError("Private preference source cannot be read safely") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or info.st_size > MAX_JSON):
            raise HarnessError("Private preference source has unsafe attributes")
        raw = os.read(fd, MAX_JSON + 1)
        if len(raw) > MAX_JSON:
            raise HarnessError("Private preference source exceeds size limit")
        return json.loads(raw)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise HarnessError("Private preference source is invalid JSON") from exc
    finally:
        os.close(fd)


def _safe_settings(raw):
    result = {}
    if not isinstance(raw, dict):
        return result
    sts2 = raw.get("sts2")
    if isinstance(sts2, dict):
        clean = {key: sts2[key] for key in BOOL_KEYS if type(sts2.get(key)) is bool}
        if sts2.get("badgeMode") in ("stats", "tiers"):
            clean["badgeMode"] = sts2["badgeMode"]
        if clean:
            result["sts2"] = clean
    if type(raw.get("acceptedTOS")) is bool:
        result["acceptedTOS"] = raw["acceptedTOS"]
    return result


def _safe_tiers(raw):
    if not isinstance(raw, dict) or len(raw) > 128:
        return {}
    clean = {}
    for key, value in raw.items():
        if (not isinstance(key, str) or not UUID.fullmatch(key) or not isinstance(value, dict)
                or value.get("uuid") != key or type(value.get("isEnabled")) is not bool
                or not isinstance(value.get("color"), str) or value["color"] not in COLORS):
            continue
        clean[key] = {"uuid": key, "isEnabled": value["isEnabled"], "color": value["color"]}
    return clean


def _write_at(root_fd, names, value):
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(data) > MAX_JSON:
        raise HarnessError("Private preferences exceed size limit")
    with _parent(root_fd, names[:-1], create=True) as parent:
        try:
            previous = os.stat(names[-1], dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            previous = None
        if previous is not None and (not stat.S_ISREG(previous.st_mode)
                                     or previous.st_uid != os.getuid() or previous.st_nlink != 1):
            raise HarnessError("Private preference destination has unsafe attributes")
        temporary = ".prefs-" + secrets.token_hex(16)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, names[-1], src_dir_fd=parent, dst_dir_fd=parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass


def seed(profile, preferences_dir):
    """Seed only previously harvested local choices into a fresh profile."""
    with _anchor(profile) as profile_fd, _anchor(preferences_dir) as preferences_fd:
        persisted = _read_at(preferences_fd, ("preferences.json",))
        if persisted is None:
            return {"settings_seeded": False, "tier_lists_seeded": 0, "terms_seeded": False}
        settings = _safe_settings(persisted.get("config")) if isinstance(persisted, dict) else {}
        tiers = _safe_tiers(persisted.get("tier_lists")) if isinstance(persisted, dict) else {}
        if settings:
            _write_at(profile_fd, ("config.json",), settings)
        if tiers:
            _write_at(profile_fd, ("sts2", "tier-lists", "index.json"), tiers)
    return {"settings_seeded": bool(settings.get("sts2")), "tier_lists_seeded": len(tiers),
            "terms_seeded": settings.get("acceptedTOS") is True}


def harvest(profile, preferences_dir):
    """Discard all account, token, session, and unknown vendor fields."""
    with _anchor(profile) as profile_fd, _anchor(preferences_dir) as preferences_fd:
        config = _safe_settings(_read_at(profile_fd, ("config.json",)))
        tiers = _safe_tiers(_read_at(profile_fd, ("sts2", "tier-lists", "index.json")))
        _write_at(preferences_fd, ("preferences.json",),
                  {"schema": 1, "config": config, "tier_lists": tiers})
    return {"settings_saved": bool(config.get("sts2")), "tier_lists_saved": len(tiers),
            "terms_saved": config.get("acceptedTOS") is True}
