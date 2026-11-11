"""Private native-launcher worker. Stdout contains only fixed UI messages."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading
from urllib.parse import parse_qsl, urlsplit

from . import main_account, main_launcher
from .asar import HarnessError


def oauth_url(value):
    if not isinstance(value, str) or len(value) > 16384 or any(ord(c) < 33 for c in value) or '#' in value:
        raise HarnessError('Invalid sign-in URL')
    u = urlsplit(value)
    if u.scheme != 'https' or u.netloc != 'accounts.untapped.gg' or u.path != '/authorize' or u.fragment:
        raise HarnessError('Invalid sign-in destination')
    fields = parse_qsl(u.query, keep_blank_values=True, strict_parsing=True)
    query = dict(fields)
    required = {'response_type': 'code', 'scope': 'companion:full-access', 'code_challenge_method': 'S256',
                'utm_source': 'uc', 'utm_medium': 'app', 'utm_campaign': 'accounts', 'utm_content': 'add-account-button'}
    nonempty = {'client_id', 'state', 'code_challenge', 'redirect_uri'}
    if len(fields) != len(query) or set(query) - (set(required) | nonempty | {'auth', 'franchise'}):
        raise HarnessError('Invalid sign-in parameters')
    if any(query.get(k) != v for k, v in required.items()) or any(not query.get(k) for k in nonempty):
        raise HarnessError('Invalid sign-in parameters')
    if any(not v for v in query.values()) or ('franchise' in query and query['franchise'] != 'STS2'):
        raise HarnessError('Invalid sign-in parameters')
    r = urlsplit(query['redirect_uri'])
    if (r.scheme != 'http' or r.hostname not in ('localhost', '127.0.0.1') or r.username or r.password
            or not r.port or not 17791 <= r.port <= 17799 or r.netloc != f'{r.hostname}:{r.port}'
            or r.path != '/' or r.query or r.fragment or '#' in query['redirect_uri']):
        raise HarnessError('Invalid sign-in callback')
    return value


def read_signin(profile):
    parent = main_account._open_directory(profile, os.getuid())
    try:
        fd = os.open('manual-sign-in-url.txt', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 16384):
            raise HarnessError('Unsafe sign-in file')
        return oauth_url(source.read(16385).decode('utf-8').strip())


@contextlib.contextmanager
def session_lock(root):
    fd = os.open(root / 'desktop-launch.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise HarnessError('Unsafe launcher lock')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise HarnessError('Another launcher session is running') from exc
        yield
    finally:
        os.close(fd)


class Controls:
    def __init__(self, output):
        self.output = output
        self.write_lock = threading.Lock()
        self.stop = threading.Event()
        self.steam = threading.Event()
        self.done = threading.Event()
        self.profile = None
        self.waiting_for_steam = False

    def emit(self, event, message=None):
        row = {'event': event}
        if message is not None:
            row['message'] = message
        with self.write_lock:
            self.output.write(json.dumps(row) + '\n')
            self.output.flush()

    def commands(self, stream):
        try:
            while not self.done.is_set():
                line = stream.readline(1025)
                if not line:
                    break
                if len(line) > 1024:
                    break
                row = json.loads(line)
                if not isinstance(row, dict) or set(row) != {'action'}:
                    break
                action = row['action']
                if action == 'stop':
                    break
                if action == 'steam_ready' and self.waiting_for_steam:
                    self.steam.set()
                elif action == 'sign_in' and self.profile is not None:
                    try:
                        url = read_signin(self.profile)
                        subprocess.run(['/usr/bin/open', url], check=True, timeout=10,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        self.emit('status', 'Click Log in inside Untapped, then try Open Untapped Sign-in again.')
                elif action not in ('steam_ready', 'sign_in'):
                    break
        except (ValueError, OSError):
            pass
        if not self.done.is_set():
            self.stop.set()

    def confirm_steam(self):
        if self.stop.is_set():
            raise KeyboardInterrupt
        self.emit('status', 'Backup verified. Opening Steam…')
        subprocess.run(['/usr/bin/open', '-a', 'Steam'], check=True, timeout=10,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.waiting_for_steam = True
        self.emit('steam_confirmation')
        try:
            while not self.steam.wait(.2):
                if self.stop.is_set():
                    raise KeyboardInterrupt
            if self.stop.is_set():
                raise KeyboardInterrupt
        finally:
            self.waiting_for_steam = False
        self.emit('status', 'Checking Steam and starting the game…')

    def companion_ready(self, attempt):
        self.profile = attempt / 'profile'
        self.emit('status', 'Game and Untapped are running. A remembered login restores automatically; otherwise click Log in in Untapped, then Open Untapped Sign-in.')
        self.emit('signin_ready')


def run_worker(stream=None, output=None, *, remember=False, forget=False, keychain_helper=None, keychain_sha256=None):
    os.umask(0o077)
    controls = Controls(output or sys.stdout)
    stream = stream or sys.stdin
    root = None
    try:
        if forget:
            # Credential deletion must still work after a game update invalidates preparation.
            _, home = main_launcher.account()
            root = main_launcher._private(home / main_launcher.WORKSPACE_RELATIVE)
        else:
            root, _, _ = main_launcher._prepared()
        with session_lock(root):
            store = None
            if remember or forget:
                from .keychain_store import KeychainStore
                controls.emit('status', 'Opening the harness login item in macOS Keychain…')
                store = KeychainStore(keychain_helper, keychain_sha256,
                    on_warning=lambda *args: controls.emit('status',
                        'Saved login is unavailable. You can sign in manually; the game can keep running.'))
                if forget:
                    store.clear()
                    controls.emit('finished', 'Saved Untapped login removed from macOS Keychain.')
                    return 0
            # Preserve private evidence without forwarding paths, URLs or vendor logs to UI.
            import tempfile
            fd, _ = tempfile.mkstemp(prefix='desktop-', suffix='.log', dir=root / 'runs')
            with os.fdopen(fd, 'w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                threading.Thread(target=controls.commands, args=(stream,), daemon=True).start()
                controls.emit('status', 'Checking the prepared apps and backing up progress…')
                result = main_launcher.start(approved=True, cloud_confirmed=True, account_confirmed=True,
                    seconds=None, confirm_steam=controls.confirm_steam,
                    should_stop=lambda: 'OWNER_STOP' if controls.stop.is_set() else None,
                    on_companion_ready=controls.companion_ready, remember_store=store)
                companion = result.get('companion', {})
                healthy = (companion.get('reason') in {'GAME_EXIT', 'COMPANION_EXITED', 'OWNER_STOP'}
                           and companion.get('failure_stage') == 'NONE'
                           and companion.get('gateway_cleanup_complete') is True
                           and companion.get('companion_group_cleanup_complete') is True
                           and result.get('game_exit_code') in (None, 0))
                if healthy:
                    controls.emit('finished', 'Companion session ended. Quit any game still running normally and let Steam Cloud sync.')
                    return 0
                controls.emit('error', 'The companion session stopped after a failed check. Private diagnostics were retained. Quit any running game normally.')
                return 1
    except main_launcher.LauncherError as exc:
        controls.emit('error', main_launcher.MESSAGES[exc.code])
    except KeyboardInterrupt:
        controls.emit('finished', 'Launcher stopped. Quit any running game normally and let Steam Cloud sync.')
        return 0
    except Exception:
        controls.emit('error', 'Launcher could not continue. Another session may be running, or the prepared setup needs inspection. Quit any game normally.')
    finally:
        controls.done.set()
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui-worker', action='store_true', required=True)
    options = parser.add_mutually_exclusive_group()
    options.add_argument('--remember-login', action='store_true')
    options.add_argument('--forget-login', action='store_true')
    parser.add_argument('--keychain-helper', type=Path)
    parser.add_argument('--keychain-sha256')
    args = parser.parse_args()
    return run_worker(remember=args.remember_login, forget=args.forget_login,
                      keychain_helper=args.keychain_helper, keychain_sha256=args.keychain_sha256)


if __name__ == '__main__':
    sys.exit(main())
