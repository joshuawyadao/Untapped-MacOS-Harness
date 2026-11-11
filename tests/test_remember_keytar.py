import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

from harness.remember_login import RememberBroker
from tests.test_remember_login import ACCOUNT, FakeStore, SERVICE, password


class RememberKeytarTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required')
    def test_hydrates_once_updates_memory_and_survives_unavailable_broker(self):
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / 'attempt'
            attempt.mkdir(mode=0o700)
            store = FakeStore({ACCOUNT: password()})
            with RememberBroker(attempt, store) as broker:
                script = textwrap.dedent(r'''
                    const assert = require('node:assert/strict');
                    const { create } = require(process.argv[1]);
                    const service = 'Untapped.gg Companion';
                    const entries = new Map();
                    const key = (s, a) => JSON.stringify([s, a]);
                    const memoryKeytar = {
                      async getPassword(s, a) { return entries.get(key(s, a)) ?? null; },
                      async setPassword(s, a, p) { entries.set(key(s, a), p); },
                      async deletePassword(s, a) { return entries.delete(key(s, a)); },
                      async findCredentials(s) { return [...entries].flatMap(([k, p]) => {
                        const [storedService, account] = JSON.parse(k);
                        return storedService === s ? [{account, password:p}] : [];
                      }); },
                      async findPassword() { return null; },
                    };
                    (async () => {
                      const proxy = create({memoryKeytar, socketPath:process.argv[2], capability:process.argv[3]});
                      const saved = await proxy.findCredentials(service);
                      assert.equal(saved.length, 1);
                      assert.equal(saved[0].account, process.argv[4]);
                      assert.equal(await proxy.findPassword(service), saved[0].password);
                      await proxy.setPassword('Steam', 'somebody', 'unrelated');
                      assert.equal(await proxy.getPassword('Steam', 'somebody'), 'unrelated');
                      await proxy.setPassword(service, process.argv[4], process.argv[5]);
                      assert.equal(await proxy.getPassword(service, process.argv[4]), process.argv[5]);
                      await proxy.deletePassword(service, process.argv[4]);
                      assert.equal(await proxy.getPassword(service, process.argv[4]), null);
                      const offline = create({memoryKeytar, socketPath:'/missing/socket', capability:'x'});
                      await offline.setPassword(service, process.argv[4], 'memory-only');
                      assert.equal(await offline.getPassword(service, process.argv[4]), 'memory-only');
                    })().catch(e => { console.error(e); process.exitCode = 1; });
                ''')
                result = subprocess.run([
                    shutil.which('node'), '-e', script,
                    str(Path(__file__).resolve().parents[1] / 'harness' / 'remember_keytar.cjs'),
                    str(broker.socket_path), broker.capability, ACCOUNT,
                    password('rotated', 'new-refresh'),
                ], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(store.data, {})


if __name__ == '__main__':
    unittest.main()
