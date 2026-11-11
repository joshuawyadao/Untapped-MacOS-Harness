import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import threading
import unittest

from harness.asar import HarnessError
from harness.remember_login import RememberBroker


SERVICE = 'Untapped.gg Companion'
ACCOUNT = 'person@example.test'


def password(access='access', refresh='refresh', **extra):
    return json.dumps({'globalOAuthAccessToken': {
        'accessToken': access, 'refreshToken': refresh, **extra,
    }, 'uploadToken': 'must-not-persist'})


class FakeStore:
    def __init__(self, data=None, fail=False):
        self.data = dict(data or {})
        self.fail = fail
        self.writes = []

    def load(self):
        if self.fail:
            raise HarnessError('private secret error')
        return dict(self.data)

    def save(self, data):
        if self.fail:
            raise HarnessError('private secret error')
        self.data = dict(data)
        self.writes.append(dict(data))

    def clear(self):
        if self.fail:
            raise HarnessError('private secret error')
        self.data.clear()
        self.writes.append({})


def call(broker, **request):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        client.connect(str(broker.socket_path))
        client.sendall(json.dumps({'capability': broker.capability, **request}).encode() + b'\n')
        return json.loads(client.makefile().readline())


class RememberBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.attempt = Path(self.temp.name) / 'attempt'
        self.attempt.mkdir(mode=0o700)

    def test_round_trip_rotation_single_account_and_logout(self):
        store = FakeStore()
        with RememberBroker(self.attempt, store) as broker:
            self.assertEqual(stat.S_IMODE(broker.socket_path.stat().st_mode), 0o600)
            self.assertEqual(len(broker.capability), 64)
            self.assertEqual(call(broker, op='load'), {'ok': True, 'credentials': []})
            self.assertTrue(call(broker, op='set', service=SERVICE, account=ACCOUNT,
                                 password=password())['ok'])
            self.assertTrue(call(broker, op='set', service=SERVICE, account=ACCOUNT,
                                 password=password('rotated', 'new-refresh'))['ok'])
            saved = json.loads(store.data[ACCOUNT])
            self.assertEqual(saved, {'globalOAuthAccessToken': {
                'accessToken': 'rotated', 'refreshToken': 'new-refresh'}})
            self.assertNotIn('uploadToken', store.data[ACCOUNT])
            self.assertTrue(call(broker, op='set', service=SERVICE,
                                 account='second@example.test', password=password())['ok'])
            self.assertEqual(list(store.data), ['second@example.test'])
        self.assertFalse(broker.socket_path.exists())
        with RememberBroker(self.attempt, store) as restarted:
            self.assertEqual(call(restarted, op='load')['credentials'][0]['account'],
                             'second@example.test')
            self.assertTrue(call(restarted, op='delete', service=SERVICE,
                                 account='second@example.test')['ok'])
            self.assertEqual(store.data, {})

    def test_rejects_unauthorized_service_account_and_non_token_data(self):
        store = FakeStore()
        with RememberBroker(self.attempt, store) as broker:
            bad = [
                {'op': 'set', 'service': 'Steam', 'account': ACCOUNT, 'password': password()},
                {'op': 'set', 'service': SERVICE, 'account': 'anonymous', 'password': password()},
                {'op': 'set', 'service': SERVICE, 'account': ACCOUNT, 'password': 'plain'},
                {'op': 'set', 'service': SERVICE, 'account': ACCOUNT, 'password': password(refresh='')},
                {'op': 'set', 'service': SERVICE, 'account': ACCOUNT, 'password': '\ud800'},
                {'op': 'set', 'service': SERVICE, 'account': ACCOUNT,
                 'password': password(access='\ud800')},
                {'op': 'delete', 'service': 'other', 'account': ACCOUNT},
            ]
            for request in bad:
                with self.subTest(request=request):
                    self.assertEqual(call(broker, **request), {'ok': False})
            self.assertEqual(call(broker, op='load', capability='wrong'), {'ok': False})
            self.assertEqual(call(broker, op='load', capability='é'), {'ok': False})
            self.assertEqual(store.writes, [])

    def test_invalid_token_clears_saved_login(self):
        store = FakeStore({ACCOUNT: password()})
        with RememberBroker(self.attempt, store) as broker:
            self.assertTrue(call(broker, op='set', service=SERVICE, account=ACCOUNT,
                                 password=password(isInvalid=True))['ok'])
            self.assertEqual(call(broker, op='load')['credentials'], [])
            self.assertEqual(store.data, {})

    def test_oversized_request_is_closed_without_persisting(self):
        store = FakeStore()
        with RememberBroker(self.attempt, store) as broker:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(3)
                client.connect(str(broker.socket_path))
                client.sendall(b' ' * (64 * 1024 + 1))
                self.assertEqual(client.recv(1), b'')
            self.assertEqual(store.writes, [])

    def test_close_drains_active_write_and_rejects_queued_rotation(self):
        entered = threading.Event()
        release = threading.Event()

        class SlowStore(FakeStore):
            def save(self, data):
                entered.set()
                release.wait(5)
                super().save(data)

        store = SlowStore()
        broker = RememberBroker(self.attempt, store)
        broker.__enter__()
        second_entered = threading.Event()
        original_dispatch = broker._dispatch

        def dispatch(request):
            if request.get('password') == password('new', 'new-refresh'):
                second_entered.set()
            return original_dispatch(request)

        broker._dispatch = dispatch
        results = []
        first = threading.Thread(target=lambda: results.append(call(
            broker, op='set', service=SERVICE, account=ACCOUNT, password=password())))
        first.start()
        self.assertTrue(entered.wait(2))
        second = threading.Thread(target=lambda: results.append(call(
            broker, op='set', service=SERVICE, account=ACCOUNT,
            password=password('new', 'new-refresh'))))
        second.start()
        self.assertTrue(second_entered.wait(2))
        closed = threading.Event()
        closer = threading.Thread(target=lambda: (broker.close(), closed.set()))
        closer.start()
        try:
            self.assertTrue(broker._stop.wait(2))
            self.assertFalse(closed.wait(0.05))
            release.set()
            for thread in (first, second, closer):
                thread.join(3)
            self.assertTrue(closed.is_set())
            self.assertEqual(len(store.writes), 1)
            self.assertIn({'ok': False}, results)
            broker.close()
        finally:
            release.set()
            for thread in (first, second, closer):
                thread.join(3)
            if not closed.is_set():
                broker.close()

    def test_keychain_denial_warns_without_exposing_details_and_keeps_session_memory(self):
        warnings = []
        with RememberBroker(self.attempt, FakeStore(fail=True), warnings.append) as broker:
            self.assertTrue(call(broker, op='set', service=SERVICE, account=ACCOUNT,
                                 password=password())['ok'])
            self.assertEqual(len(call(broker, op='load')['credentials']), 1)
        self.assertGreaterEqual(len(warnings), 1)
        self.assertNotIn('private secret', repr(warnings))

    def test_requires_private_attempt_directory(self):
        os.chmod(self.attempt, 0o755)
        with self.assertRaises(HarnessError):
            with RememberBroker(self.attempt, FakeStore()):
                pass


if __name__ == '__main__':
    unittest.main()
