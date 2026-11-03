"""Execute the synthetic vendor seams under controlled and ordinary offline modes."""

import pathlib
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_offline_auth import SERVICES_SOURCE, fixture_archive  # noqa: E402
from harness import patches  # noqa: E402


@unittest.skipUnless(shutil.which("node"), "Node is required for synthetic JS execution")
class ControlledAuthTests(unittest.TestCase):
    def run_node(self, source, script):
        result = subprocess.run(
            [shutil.which("node"), "-e", script], input=source,
            text=True, capture_output=True, check=False, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_services_auth_upload_and_metrics_boundaries(self):
        archive = fixture_archive(SERVICES_SOURCE)
        source = patches.patched_entries(archive)[patches.SERVICES].decode()
        self.run_node(source, r"""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const vm = require('node:vm');
            const source = fs.readFileSync(0, 'utf8');
            function setup(env) {
              const events = [];
              const context = vm.createContext({ process: {env},
                __untappedHarnessEvent(name) { events.push(name); } });
              context.global = context;
              vm.runInContext(source + '\nglobalThis.Auth = AuthenticationManager; globalThis.Extra = ExtraServicesFixture;', context);
              const auth = new context.Auth();
              const calls = {load: 0, fetch: 0, store: 0};
              const credentials = {authenticatedCredentials: {player: {token: 'owned-test-token'}},
                anonymousCredentials: {token: 'anonymous-test-token'}};
              auth.loadLocalCredentials = async () => {calls.load++; return credentials;};
              auth.fetchAnonymousUploadToken = async () => {calls.fetch++; return 'fetched';};
              auth.localCredentialsManager = {storeAnonymousCredentials: async () => {calls.store++;}};
              const extra = new context.Extra();
              extra.emit = (name, error) => events.push([name, error]);
              extra.ensureLocalCredentials = async () => {calls.load++; return credentials;};
              extra.ensureUploadToken = async () => {calls.store++;};
              return {auth, extra, calls, events};
            }
            (async () => {
              const controlled = setup({UNTAPPED_HARNESS_OFFLINE: '1', UNTAPPED_HARNESS_CONTROLLED_ACCESS: '1'});
              const found = await controlled.auth.ensureLocalCredentials();
              assert.equal(found.anonymousCredentials, null);
              assert.deepEqual(JSON.parse(JSON.stringify(found.authenticatedCredentials)),
                {player: {token: 'owned-test-token'}});
              assert.deepEqual(controlled.calls, {load: 1, fetch: 0, store: 0});
              await controlled.extra.unrelatedUpload('player');
              assert.deepEqual(controlled.calls, {load: 1, fetch: 0, store: 0});
              controlled.extra.finish(null);
              controlled.extra.finish(new Error('failed'));
              assert.equal(controlled.events.filter(x => x === 'authenticated').length, 1);
              assert.equal(controlled.events.filter(x => Array.isArray(x) && x[0] === 'authorizationWorkflowComplete').length, 2);
              assert.equal(await controlled.extra.constructor.init('token'), undefined);
              assert.equal(await controlled.extra.constructor.sendInflux('metric'), undefined);
              assert.equal(controlled.extra.constructor.sendMixpanel('metric'), undefined);

              const offline = setup({UNTAPPED_HARNESS_OFFLINE: '1'});
              const empty = await offline.auth.ensureLocalCredentials();
              assert.deepEqual(JSON.parse(JSON.stringify(empty)), {authenticatedCredentials: {}, anonymousCredentials: null});
              assert.deepEqual(offline.calls, {load: 0, fetch: 0, store: 0});
              await offline.extra.unrelatedUpload('player');
              assert.deepEqual(offline.calls, {load: 1, fetch: 0, store: 1});
              offline.extra.finish(null);
              assert.equal(offline.events.filter(x => x === 'authenticated').length, 0);
              assert.equal(await offline.extra.constructor.init('token'), 'original');
              assert.equal(await offline.extra.constructor.sendInflux('metric'), 'original');
              assert.equal(offline.extra.constructor.sendMixpanel('metric'), 'original');

              const normal = setup({});
              const original = await normal.auth.loadLocalCredentials();
              assert.equal(await normal.auth.ensureLocalCredentials(), original);
              assert.equal(normal.calls.fetch, 0);
            })().catch(error => {console.error(error); process.exitCode = 1;});
        """)

    def test_core_upload_and_logwatcher_guards_execute(self):
        archive = fixture_archive()
        core = patches.patched_entries(archive)[patches.CORE].decode()
        self.run_node(core, r"""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const source = fs.readFileSync(0, 'utf8');
            const guard = 'process.env.UNTAPPED_HARNESS_CONTROLLED_ACCESS === "1"';
            const callbackLine = source.split('\n').find(line => line.includes('this.logWatcher.on("runComplete"'));
            assert(callbackLine && callbackLine.includes(guard));
            const callback = new Function('process', 'this.onRunComplete = () => {}; this.logWatcher = {on: (name) => this.calls.push(name)}; ' + callbackLine);
            const controlled = {calls: []};
            callback.call(controlled, {env: {UNTAPPED_HARNESS_CONTROLLED_ACCESS: '1'}});
            assert.deepEqual(controlled.calls, []);
            const normal = {calls: []};
            callback.call(normal, {env: {}});
            assert.deepEqual(normal.calls, ['runComplete']);
            for (const method of ['maybeStartLogWatcher', 'maybeUploadHistoricRuns']) {
              const line = source.split('\n').find(line => line.includes(method + '() {'));
              const next = source.split('\n')[source.split('\n').indexOf(line) + 1];
              assert.equal(next.trim(), 'if (' + guard + ') return;');
              const executable = new Function('process', next + ' return "original";');
              assert.equal(executable({env: {UNTAPPED_HARNESS_CONTROLLED_ACCESS: '1'}}), undefined);
              assert.equal(executable({env: {}}), 'original');
            }
            for (const name of ['uploadRun', 'uploadHistoricRun']) {
              const line = source.split('\n').find(line => line.includes('async function ' + name + '('));
              const next = source.split('\n')[source.split('\n').indexOf(line) + 1];
              assert(next.includes('throw new Error("Controlled harness blocks'));
              const executable = new Function('process', next + ' return "original";');
              assert.throws(() => executable({env: {UNTAPPED_HARNESS_CONTROLLED_ACCESS: '1'}}),
                /Controlled harness blocks/);
              assert.equal(executable({env: {}}), 'original');
            }
        """)


if __name__ == "__main__":
    unittest.main()
