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


# Public UUIDs from the pinned companion's bundled defaultTierLists.
DEFAULT_TIERS = {
    "baalorlord": dict(zip(("ironclad", "silent", "regent", "necrobinder", "defect"), (
        "004de170-026a-4dd4-a280-3b904be0b5d6", "6d61ea21-0552-4c49-8bb5-a5c15530fc00",
        "0e6c1e23-bec6-4887-a9e0-dbf49ede974d", "43d0b41f-7d6d-4ce9-928e-c1310a413983",
        "5a512e04-4583-4a16-9271-d46864c6cb4c"))),
    "jorbs": dict(zip(("ironclad", "silent", "regent", "necrobinder", "defect"), (
        "6b3390b7-bcbc-4ebc-ae78-ae9a400c66dc", "2cd72d4b-eeb4-42ab-89ca-4ac682137672",
        "c47dbfda-4983-4107-8c9c-c33d5ae32b23", "3ae661e6-6190-4a45-b00e-63e8400fff94",
        "5f8d3e04-1f50-4b56-b51a-d8650b000ce3"))),
}


def _fill_default_tiers(tiers):
    # Prefer the already selected bundled author. Preserve every enabled custom list.
    author = max(DEFAULT_TIERS, key=lambda name: sum(
        tiers.get(uuid, {}).get("isEnabled") is True for uuid in DEFAULT_TIERS[name].values()))
    covered = {entry["color"] for entry in tiers.values() if entry["isEnabled"]}
    result = dict(tiers)
    for color, uuid in DEFAULT_TIERS[author].items():
        if color not in covered:
            result[uuid] = {"uuid": uuid, "color": color, "isEnabled": True}
    if len(result) > 128:
        raise HarnessError("Default tier lists exceed preference limit")
    return result


def seed(profile, preferences_dir, *, enable_default_tiers=False):
    """Seed only previously harvested local choices into a fresh profile."""
    with _anchor(profile) as profile_fd, _anchor(preferences_dir) as preferences_fd:
        persisted = _read_at(preferences_fd, ("preferences.json",))
        settings = _safe_settings(persisted.get("config")) if isinstance(persisted, dict) else {}
        tiers = _safe_tiers(persisted.get("tier_lists")) if isinstance(persisted, dict) else {}
        migrated = isinstance(persisted, dict) and persisted.get("default_tiers_version") == 1
        if enable_default_tiers and not migrated:
            tiers = _fill_default_tiers(tiers)
            migrated = True
        if migrated:
            _write_at(profile_fd, ("harness-default-tiers.json",), {"version": 1})
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
        saved = {"schema": 1, "config": config, "tier_lists": tiers}
        if _read_at(profile_fd, ("harness-default-tiers.json",)) == {"version": 1}:
            saved["default_tiers_version"] = 1
        _write_at(preferences_fd, ("preferences.json",), saved)
    return {"settings_saved": bool(config.get("sts2")), "tier_lists_saved": len(tiers),
            "terms_saved": config.get("acceptedTOS") is True}
