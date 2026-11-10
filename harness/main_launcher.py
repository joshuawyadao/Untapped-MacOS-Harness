"""Explicitly opted-in copied-game launcher for existing main-account Steam progress."""

import argparse
import json
import os
import platform
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import cli, controlled, game_debug, game_launch, main_account, reward_probe, signing
from .asar import HarnessError, sha256

WORKSPACE_RELATIVE = Path("Library/Application Support/UntappedSTS2Harness")
APP_ID = "2868840"
DEFAULT_SECONDS = 4 * 60 * 60
MAX_SECONDS = 8 * 60 * 60
STEAM_OK = "Steamworks initialization succeeded!"
CLOUD_STORE = "Steam is enabled, we will write saves to steam storage. Enabled for account: "
STEAM_FAILURES = ("Steamworks initialization failed!", "Steamworks initialization threw an exception:",
                  "Steam initialization skipped", "Failed to initialize Steam!")
MESSAGES = {
    "MAIN_ACCOUNT_REQUIRED": "Run this launcher in the normal macOS account, without sudo.",
    "WORKSPACE_UNAVAILABLE": "The private main-account workspace is missing or redirected.",
    "WORKSPACE_EXISTS": "A main-account workspace already exists; it will not be overwritten.",
    "UNSUPPORTED_PROGRESS": "One unambiguous Steam account and an existing normal profile are required.",
    "SOURCE_CHANGED": "The installed game changed; prepare and review a new compatible copy.",
    "PREPARATION_INVALID": "Prepared files or identity changed; the launcher will not continue.",
    "SIGNING_APPROVAL_REQUIRED": "Review the proposal before approving copied-app signing.",
    "ACTIVATION_REQUIRED": "The copied apps must be explicitly activated before launch.",
    "LIVE_CONFIRMATIONS_REQUIRED": "Explicit launch, up-to-date Cloud, and intended Steam-account confirmations are required.",
    "CLOSE_STEAM_AND_GAME": "Quit Steam and every Slay the Spire 2 instance before the backup step.",
    "OPEN_INTENDED_STEAM": "Open Steam in the intended normal account, with every game copy closed.",
    "STEAM_STARTUP_FAILED": "The copied game did not confirm Steam and enabled Cloud storage. Quit it normally; no restore is automatic.",
    "TARGET_CONFLICT": "An unexpected game or Steam process was detected. Quit games normally before retrying.",
    "INTERACTIVE_TERMINAL_REQUIRED": "Start from an interactive Terminal so you can open and confirm Steam after backup.",
    "BACKUP_FAILED": "The private progress backup could not be verified. No game was launched.",
    "PROGRESS_CHANGED": "Progress changed after backup. Quit Steam and games, then make a fresh verified backup.",
    "INSPECTION_FAILED": "A local validation failed. Private data and logs are not included in this error.",
}


class LauncherError(HarnessError):
    def __init__(self, code):
        self.code = code if code in MESSAGES else "INSPECTION_FAILED"
        super().__init__(MESSAGES[self.code])


def _fail(code):
    raise LauncherError(code)


def account():
    uid = os.getuid()
    user = pwd.getpwuid(uid)
    home = Path(user.pw_dir)
    if (platform.system() != "Darwin" or uid == 0 or uid != os.geteuid()
            or home != game_launch.PROTECTED_HOME or user.pw_name != home.name
            or main_account._directory_status(home, uid) != "DIRECTORY"):
        _fail("MAIN_ACCOUNT_REQUIRED")
    return uid, home


def _private(path):
    if main_account._directory_status(path, os.getuid()) != "DIRECTORY":
        _fail("WORKSPACE_UNAVAILABLE")
    info = path.lstat()
    if stat.S_IMODE(info.st_mode) != 0o700:
        _fail("WORKSPACE_UNAVAILABLE")
    return path


def _write(path, value):
    _private(path.parent)
    if path.exists() or path.is_symlink():
        _fail("PREPARATION_INVALID")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(value, output, indent=2)
        output.write("\n")


def _read(path):
    parent = main_account._open_directory(path.parent, os.getuid())
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as source:
            info = os.fstat(source.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 2 * 1024 * 1024):
                _fail("PREPARATION_INVALID")
            raw = source.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                _fail("PREPARATION_INVALID")
            value = json.loads(raw)
            if not isinstance(value, dict):
                _fail("PREPARATION_INVALID")
            return value
    finally:
        os.close(parent)


def _progress(data_root, selected_profile=None):
    """Select existing directory identities privately; contents remain unopened."""
    budget = [main_account.LIMIT_TOTAL]
    steam = data_root / "steam"
    if main_account._directory_status(steam, os.getuid()) != "DIRECTORY":
        _fail("UNSUPPORTED_PROGRESS")
    rows, limit, incomplete = main_account._scan_directory(steam, os.getuid(), budget)
    identities = [(name, path) for name, path in rows if re.fullmatch(r"[1-9][0-9]{0,19}", name)]
    if limit or incomplete or len(identities) != 1 or len(rows) != 1:
        _fail("UNSUPPORTED_PROGRESS")
    steam_id, base = identities[0]
    profiles, limit, incomplete = main_account._scan_directory(base, os.getuid(), budget)
    choices = [int(name[7:]) for name, _ in profiles if re.fullmatch(r"profile(?:0|[1-9][0-9]?)", name)]
    if limit or incomplete or not choices:
        _fail("UNSUPPORTED_PROGRESS")
    if selected_profile is None:
        if len(choices) != 1:
            _fail("UNSUPPORTED_PROGRESS")
        selected_profile = choices[0]
    if type(selected_profile) is not int or selected_profile not in choices:
        _fail("UNSUPPORTED_PROGRESS")
    return steam_id, selected_profile


def _source(home):
    source = home / main_account.GAME_RELATIVE
    try:
        files = game_launch.verified_app(source)
    except (HarnessError, OSError):
        _fail("SOURCE_CHANGED")
    if game_debug._tree_hash(files) != game_debug.ORIGINAL_TREE_SHA256:
        _fail("SOURCE_CHANGED")
    return source


def _gateway_review(session):
    review = controlled.proposal(session)
    review.update(supervisor="MAIN_ACCOUNT_COMPANION", maximum_seconds=MAX_SECONDS,
                  default_seconds=DEFAULT_SECONDS, post_auth_maximum_seconds=None,
                  authentication_shortens_session=False)
    return review


def prepare(companion_app, *, selected_profile=None):
    uid, home = account()
    root = home / WORKSPACE_RELATIVE
    if root.exists() or root.is_symlink():
        _fail("WORKSPACE_EXISTS")
    if main_account._directory_status(root.parent, uid) != "DIRECTORY":
        _fail("WORKSPACE_UNAVAILABLE")
    source = _source(home)
    steam_id, profile = _progress(home / main_account.DATA_RELATIVE, selected_profile)
    root.mkdir(mode=0o700)
    game_proposal = game_debug.prepare(source, root / "game")
    cli.prepare(Path(companion_app), root / "companion")
    manifest = cli.read_json(root / "companion/manifest.json")
    if manifest.get("main_steam_guard_version") != 1:
        _fail("PREPARATION_INVALID")
    companion_proposal = signing.signing_proposal(root / "companion")
    for name in ("backups", "runs", "preferences"):
        (root / name).mkdir(mode=0o700)
    binding = {"schema": 1, "uid": uid, "home": str(home), "steam_id": steam_id,
               "profile": profile, "source_tree_sha256": game_debug.ORIGINAL_TREE_SHA256,
               "companion_asar_sha256": manifest["patched_asar_sha256"]}
    _write(root / "main-launch.json", binding)
    review = {"schema": 1, "proposal_only": True, "activation_required": True,
              "workspace": str(root), "game_signing": game_proposal,
              "companion_signing": companion_proposal,
              "installed_game_modified": False, "save_restore_implemented": False,
              "progress": "EXISTING_STEAM_ACCOUNT_AND_PROFILE_PRIVATE_BINDING",
              "backup_source": str(home / main_account.DATA_RELATIVE),
              "backup_destination": str(root / "backups"), "backup_requires_steam_and_games_closed": True,
              "steam_app_id": APP_ID, "game_permissions": "NORMAL_CURRENT_USER_AND_STEAM",
              "game_sandbox": False, "steam_cloud": "NORMAL_STEAM_BEHAVIOR_OWNER_CONFIRMS_FRESHNESS",
              "game_command": [str(root / "game" / game_debug.APP / game_launch.EXECUTABLE),
                               "--force-steam=on", "--nomods", "--windowed"],
              "steam_app_id_file": "PRIVATE_WORKING_DIRECTORY_ONLY",
              "companion_seconds_default": DEFAULT_SECONDS, "companion_seconds_maximum": MAX_SECONDS,
              "companion_outer_sandbox_retained": True, "chromium_sandbox": False,
              "gateway": _gateway_review(root / "companion"),
              "preferences": "VALIDATED_STS2_AND_TIER_SELECTIONS_ONLY", "credentials": "SESSION_MEMORY_ONLY",
              "game_exit": "OWNER_NORMAL_QUIT_NEVER_AUTOMATIC_KILL",
              "cloud_conflicts": "OWNER_REVIEW_NO_AUTOMATIC_RESOLUTION"}
    _write(root / "main-proposal.json", review)
    return review


def _prepared():
    uid, home = account()
    root = _private(home / WORKSPACE_RELATIVE)
    binding = _read(root / "main-launch.json")
    if (binding.get("schema") != 1 or binding.get("uid") != uid or binding.get("home") != str(home)
            or binding.get("source_tree_sha256") != game_debug.ORIGINAL_TREE_SHA256):
        _fail("PREPARATION_INVALID")
    _source(home)
    steam_id, profile = _progress(home / main_account.DATA_RELATIVE, binding.get("profile"))
    if steam_id != binding.get("steam_id") or profile != binding.get("profile"):
        _fail("PREPARATION_INVALID")
    manifest = cli.read_json(root / "companion/manifest.json")
    if (manifest.get("main_steam_guard_version") != 1
            or manifest.get("patched_asar_sha256") != binding.get("companion_asar_sha256")):
        _fail("PREPARATION_INVALID")
    controlled.proposal(root / "companion")
    return root, home, binding


def activate(*, approved=False):
    if not approved:
        _fail("SIGNING_APPROVAL_REQUIRED")
    root, _, _ = _prepared()
    if not (root / "game" / game_debug.RECEIPT).exists():
        game_debug.sign(root / "game", approved=True)
    game_debug.verify(root / "game")
    if not (root / "companion/signing.json").exists():
        signing.sign_copy(root / "companion", approved=True)
    cli._validate_launch_copy(root / "companion")
    if not (root / "activation.json").exists():
        _write(root / "activation.json", {"schema": 1, "copied_apps_signed": True,
               "proposal_sha256": sha256((root / "main-proposal.json").read_bytes()),
               "installed_game_modified": False})
    return {"copied_apps_signed": True, "game_launched": False, "progress_written": False}


def proposal():
    root, _, _ = _prepared()
    review = _read(root / "main-proposal.json")
    review["copied_apps_signed"] = (root / "activation.json").is_file()
    return review


def _inventory():
    return list(reward_probe._candidates(reward_probe._process_inventory()))


def _closed():
    if _inventory():
        _fail("CLOSE_STEAM_AND_GAME")


def _steam_ready():
    rows = _inventory()
    if (not any(steam and uid == os.getuid() for _, uid, _, steam in rows)
            or any(not steam or uid != os.getuid() for _, uid, _, steam in rows)):
        _fail("OPEN_INTENDED_STEAM")


def _target(expected, process_group):
    games = []
    for pid, uid, command, steam in _inventory():
        if uid != os.getuid():
            _fail("TARGET_CONFLICT")
        if not steam:
            if command != str(expected) or os.getpgid(pid) != process_group:
                _fail("TARGET_CONFLICT")
            games.append(pid)
    if len(games) > 1:
        _fail("TARGET_CONFLICT")
    return games[0] if games else None


def _steam_status(log):
    parent = main_account._open_directory(log.parent, os.getuid())
    try:
        descriptor = os.open(log.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(descriptor, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            _fail("PREPARATION_INVALID")
        source.seek(max(0, info.st_size - 2 * 1024 * 1024))
        text = source.read(2 * 1024 * 1024).decode("utf-8", "replace")
    failed = any(marker in text for marker in STEAM_FAILURES)
    cloud = re.search(re.escape(CLOUD_STORE) + r"True, app: True", text) is not None
    return {"initialized": STEAM_OK in text, "cloud_store_enabled_logged": cloud, "failed": failed}


def _wait_for_steam(process, executable, log, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            _fail("STEAM_STARTUP_FAILED")
        pid = _target(executable, process.pid)
        state = _steam_status(log)
        if state["failed"]:
            _fail("STEAM_STARTUP_FAILED")
        if pid is not None and state["initialized"] and state["cloud_store_enabled_logged"]:
            return pid
        time.sleep(0.25)
    _fail("STEAM_STARTUP_FAILED")


def start(*, approved=False, cloud_confirmed=False, account_confirmed=False,
          seconds=DEFAULT_SECONDS, confirm_steam=None):
    if not (approved and cloud_confirmed and account_confirmed):
        _fail("LIVE_CONFIRMATIONS_REQUIRED")
    if type(seconds) is not int or not 60 <= seconds <= MAX_SECONDS:
        _fail("PREPARATION_INVALID")
    root, home, binding = _prepared()
    if not (root / "activation.json").exists():
        _fail("ACTIVATION_REQUIRED")
    activation = _read(root / "activation.json")
    if (activation.get("schema") != 1 or activation.get("copied_apps_signed") is not True
            or activation.get("proposal_sha256") != sha256((root / "main-proposal.json").read_bytes())):
        _fail("ACTIVATION_REQUIRED")
    from .ui_update import selected_session
    companion_session = selected_session(root)
    game_debug.verify(root / "game")
    cli._validate_launch_copy(companion_session)
    _closed()
    if confirm_steam is None:
        _fail("INTERACTIVE_TERMINAL_REQUIRED")
    from . import main_companion, progress_backup
    backup = Path(tempfile.mkdtemp(prefix="progress-", dir=_private(root / "backups")))
    # The backup API requires a new destination, not an existing empty directory.
    backup.rmdir()
    try:
        backup_summary = progress_backup.create_backup(home / main_account.DATA_RELATIVE, backup)
        progress_backup.verify_backup(backup)
    except (HarnessError, OSError):
        _fail("BACKUP_FAILED")
    confirm_steam()
    _steam_ready()
    # Opening Steam can update the installed build while the owner confirms it.
    _source(home)
    game_debug.verify(root / "game")
    if selected_session(root) != companion_session:
        _fail("PREPARATION_INVALID")
    cli._validate_launch_copy(companion_session)
    try:
        progress_backup.assert_source_unchanged(home / main_account.DATA_RELATIVE, backup)
    except (HarnessError, OSError):
        _fail("PROGRESS_CHANGED")
    attempt = Path(tempfile.mkdtemp(prefix="main-", dir=_private(root / "runs")))
    (attempt / "temp").mkdir(mode=0o700)
    (attempt / "steam_appid.txt").write_text(APP_ID + "\n")
    (attempt / "steam_appid.txt").chmod(0o600)
    executable = root / "game" / game_debug.APP / game_launch.EXECUTABLE
    command = [str(executable), "--force-steam=on", "--nomods", "--windowed"]
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8",
                   "HOME": str(home), "TMPDIR": str(attempt / "temp"),
                   "SteamAppId": APP_ID, "SteamGameId": APP_ID}
    print("Verified backup complete. The copied game will now use normal Steam progress and Cloud behavior.", flush=True)
    print("Confirm your expected profile in the game before playing. Quit the game normally when finished.", flush=True)
    process = None
    try:
        log = attempt / "game.log"
        with log.open("xb") as output:
            os.chmod(log, 0o600)
            _source(home)
            process = subprocess.Popen(command, cwd=attempt, env=environment, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            pid = _wait_for_steam(process, executable, log)

            def stop_reason():
                try:
                    current = _target(executable, process.pid)
                    if current is None:
                        return "GAME_EXIT"
                    if current != pid:
                        return "TARGET_CONFLICT"
                except (HarnessError, OSError):
                    return "TARGET_CONFLICT"
                return None

            report = main_companion.run(companion_session, _private(root / "preferences"),
                       target_pid=pid, target_game=executable, expected_steam_id=binding["steam_id"],
                       expected_profile=binding["profile"], seconds=seconds, should_stop=stop_reason)
        result = {"mode": "MAIN_ACCOUNT_STEAM_PROGRESS", "backup": backup_summary,
                  "steam_initialization_observed": True, "cloud_store_enabled_logged": True,
                  "cloud_freshness": "OWNER_CONFIRMED_NOT_INDEPENDENTLY_VERIFIED",
                  "companion": report, "game_left_running": process.poll() is None,
                  "installed_game_modified": False, "save_restore_performed": False}
        _write(attempt / "summary.json", result)
        return result
    finally:
        # A diagnostic cutoff, failure or Ctrl+C is never a save-game kill switch.
        if process is not None and process.poll() is None:
            print("The copied game is still running. Quit it normally; the launcher will not kill it or restore saves.", flush=True)


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--companion-source", type=Path, required=True)
    prep.add_argument("--profile", type=int)
    sub.add_parser("proposal")
    activate_parser = sub.add_parser("activate")
    activate_parser.add_argument("--approve-main-copy-signing", action="store_true")
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--approve-main-account-launch", action="store_true")
    start_parser.add_argument("--confirm-cloud-synced", action="store_true")
    start_parser.add_argument("--confirm-steam-account", action="store_true")
    start_parser.add_argument("--minutes", type=int, default=DEFAULT_SECONDS // 60)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.companion_source, selected_profile=args.profile)
        elif args.command == "proposal":
            result = proposal()
        elif args.command == "activate":
            result = activate(approved=args.approve_main_copy_signing)
        else:
            if not sys.stdin.isatty():
                _fail("INTERACTIVE_TERMINAL_REQUIRED")

            def confirm():
                input("Backup verified. Open Steam in your intended account; wait for Cloud to be up to date. Press Return when ready: ")

            result = start(approved=args.approve_main_account_launch,
                           cloud_confirmed=args.confirm_cloud_synced, account_confirmed=args.confirm_steam_account,
                           seconds=args.minutes * 60, confirm_steam=confirm)
        print(json.dumps(result, indent=2))
        if args.command == "start":
            companion = result.get("companion", {})
            healthy = (companion.get("authenticated") is True
                       and companion.get("steam_account_verified") is True
                       and companion.get("failure_stage") == "NONE"
                       and companion.get("gateway_cleanup_complete") is True
                       and companion.get("companion_group_cleanup_complete") is True)
            return 0 if healthy else 1
        return 0
    except LauncherError as error:
        print(f"Main launcher stopped [{error.code}]: {MESSAGES[error.code]}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Main launcher interrupted. Quit any running copied game normally; saves were not restored.", file=sys.stderr)
        return 130
    except Exception:
        print("Main launcher stopped [INSPECTION_FAILED]. Private logs and account details are not shared.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
