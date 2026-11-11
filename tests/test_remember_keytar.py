import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

from harness import cli
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
                    const service = 'Untapped Companion native-sts2-harness';
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


    @unittest.skipUnless(shutil.which('node'), 'Node is required')
    def test_vendor_service_from_real_launcher_environment_persists_and_restores(self):
        # This is the pinned Services chunk's service expression, independent of
        # the bridge constants that previously agreed on the same wrong name.
        script = r"""
const assert = require('node:assert/strict');
const {create} = require(process.argv[1]);
const service = process.env.UC_TEST_SANDBOX_ID
  ? `Untapped Companion ${process.env.UC_TEST_SANDBOX_ID}` : 'Untapped Companion';
const account = 'person@example.test', entries = new Map();
const key = (s,a) => JSON.stringify([s,a]);
const memoryKeytar = {
 async getPassword(s,a) {return entries.get(key(s,a)) ?? null;},
 async setPassword(s,a,p) {entries.set(key(s,a),p);},
 async deletePassword(s,a) {return entries.delete(key(s,a));},
 async findCredentials(s) {return [...entries].flatMap(([k,password]) => {
   const [stored,account] = JSON.parse(k); return stored===s ? [{account,password}] : [];
 });},
 async findPassword() {return null;}
};
(async()=>{
 const proxy=create({memoryKeytar,socketPath:process.argv[2],capability:process.argv[3]});
 const phase=process.argv[4];
 if(phase==='save') {
  await proxy.setPassword('Steam',account,'unrelated');
  await proxy.setPassword('Untapped.gg Companion',account,'unrelated');
  await proxy.setPassword(service,account,JSON.stringify({globalOAuthAccessToken:{
   accessToken:'fixture-access',refreshToken:'fixture-refresh'},uploadToken:'excluded'}));
 } else {
  const saved=await proxy.findCredentials(service);
  assert.equal(saved.length,1);
  assert.equal(saved[0].account,account);
  assert.equal(JSON.parse(saved[0].password).globalOAuthAccessToken.accessToken,
    phase==='rotate'?'fixture-access':'rotated-access');
  if(phase==='rotate') await proxy.setPassword(service,account,JSON.stringify({globalOAuthAccessToken:{
   accessToken:'rotated-access',refreshToken:'rotated-refresh'}}));
  else await proxy.deletePassword(service,account);
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        store = FakeStore()
        with tempfile.TemporaryDirectory() as temp:
            for phase in ('save', 'rotate', 'delete'):
                attempt = Path(temp) / phase
                attempt.mkdir(mode=0o700)
                with RememberBroker(attempt, store) as broker:
                    result = subprocess.run([shutil.which('node'), '-e', script,
                        str(Path(__file__).resolve().parents[1] / 'harness/remember_keytar.cjs'),
                        str(broker.socket_path), broker.capability, phase],
                        env=cli.launch_environment(attempt), capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                if phase == 'delete':
                    self.assertEqual(store.data, {})
                else:
                    self.assertEqual(list(store.data), [ACCOUNT])
                    saved = json.loads(store.data[ACCOUNT])
                    self.assertEqual(set(saved), {'globalOAuthAccessToken'})
                    self.assertEqual(saved['globalOAuthAccessToken']['accessToken'],
                                     'fixture-access' if phase == 'save' else 'rotated-access')
            self.assertEqual(len(store.writes), 3)


if __name__ == '__main__':
    unittest.main()
