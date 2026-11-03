"""Synthetic PID identity tests; the native game and vendor code never execute."""
import json
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path

from harness.asar import HarnessError
from harness import patches


class TargetGuardTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for bootstrap execution")
    def test_target_identity_blocks_reader_construction_before_native_connection(self):
        core_old, core_new = next(pair for pair in patches.CORE_PATCHES if "new GameScryInstance" in pair[0])
        self.assertIn("new GameScryInstance", core_new)
        self.assertLess(core_new.index("__untappedHarnessAssertTargetPid"),
                        core_new.index("new GameScryInstance"))
        code = textwrap.dedent(r"""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const vm = require('node:vm');
            const crypto = require('node:crypto');
            const probeBytes = Buffer.from('synthetic original identity helper');
            const probeHash = crypto.createHash('sha256').update(probeBytes).digest('hex');
            const bootstrap = fs.readFileSync(process.argv[1], 'utf8');
            const targetCode = process.argv[2];
            const executable = '/private/tmp/test game/SlayTheSpire2.app/Contents/MacOS/Slay the Spire 2';
            function run(env, pid, franchise='STS2', identityRow='502 ' + executable, probeOverrides={}) {
              let probeCalls = 0, constructed = 0, disposed = 0;
              const globals = {};
              const proc = { env: { UC_TEST_SANDBOX_DIR: '/private/tmp/test-profile',
                UNTAPPED_HARNESS_OFFLINE: '1', ...env }, getuid: () => 502 };
              const electron = { app: { setPath() {}, setLoginItemSettings() {},
                setAsDefaultProtocolClient() {}, whenReady: () => Promise.resolve() },
                shell: { openExternal() {} } };
              const fsStub = { mkdirSync() {}, appendFileSync() {},
                lstatSync: () => ({ isFile: () => probeOverrides.isFile ?? true,
                  uid: probeOverrides.uid ?? 502, nlink: probeOverrides.nlink ?? 1,
                  mode: probeOverrides.mode ?? 0o100700 }),
                readFileSync: () => probeOverrides.bytes ?? probeBytes,
              };
              const child = { execFileSync: (command, args, opts) => {
                probeCalls++;
                assert.equal(command, '/private/tmp/test-profile/target-identity');
                assert.deepEqual(Array.from(args), [String(pid)]);
                assert.equal(opts.timeout, 2000);
                return identityRow;
              } };
              const requireStub = name => ({ 'node:fs': fsStub, 'node:path': path,
                'node:module': { _load() {} }, electron, 'node:child_process': child, 'node:crypto': crypto })[name];
              vm.runInNewContext(bootstrap, { require: requireStub, process: proc,
                global: globals, Date });
              const callback = new Function('pid', 'franchise', 'global',
                'GameScryInstance', targetCode);
              const instance = { disposeScry() { disposed++; } };
              const Native = function(info) { constructed++; this.info = info; };
              let error = null;
              try { callback.call(instance, pid, franchise, globals, Native); }
              catch (caught) { error = caught; }
              return { error, probeCalls, constructed, disposed, scry: instance._scry };
            }
            const target = { UNTAPPED_HARNESS_TARGET_PID: '71',
              UNTAPPED_HARNESS_TARGET_UID: '502',
              UNTAPPED_HARNESS_TARGET_EXECUTABLE: executable,
              UNTAPPED_HARNESS_IDENTITY_SHA256: probeHash };
            for (const env of [{}, { ...target, UNTAPPED_HARNESS_TARGET_PID: '071' },
              { ...target, UNTAPPED_HARNESS_TARGET_UID: '0502' },
              { ...target, UNTAPPED_HARNESS_TARGET_EXECUTABLE: 'relative/game' },
              { ...target, UNTAPPED_HARNESS_IDENTITY_SHA256: 'bad' },
              { ...target, UNTAPPED_HARNESS_IDENTITY_SHA256: undefined }]) {
              const result = run(env, 71);
              assert.ok(result.error);
              assert.equal(result.constructed, 0);
              assert.equal(result.disposed, 0);
              assert.equal(result.probeCalls, 0);
            }
            const wrongPid = run(target, 72);
            assert.ok(wrongPid.error);
            assert.equal(wrongPid.constructed, 0);
            assert.equal(wrongPid.probeCalls, 0);
            for (const row of ['503 ' + executable, '502 /private/tmp/other',
              '', '502 ' + executable + '\n502 /private/tmp/other']) {
              const result = run(target, 71, 'STS2', row);
              assert.ok(result.error);
              assert.equal(result.constructed, 0);
              assert.equal(result.disposed, 0);
              assert.equal(result.probeCalls, 1);
            }
            for (const probe of [{uid:503}, {mode:0o100755}, {nlink:2},
              {isFile:false}, {bytes:Buffer.from('tampered')}]) {
              const result = run(target, 71, 'STS2', '502 ' + executable, probe);
              assert.ok(result.error);
              assert.equal(result.constructed, 0);
              assert.equal(result.probeCalls, 0);
            }
            const match = run(target, 71);
            assert.equal(match.error, null);
            assert.equal(match.probeCalls, 1);
            assert.equal(match.constructed, 1);
            assert.equal(match.disposed, 1);
            assert.equal(match.scry.info.pid, 71);
            const otherGame = run({}, 71, 'MTGA');
            assert.equal(otherGame.error, null);
            assert.equal(otherGame.constructed, 1);
            assert.equal(otherGame.probeCalls, 0);
        """)
        result = subprocess.run(
            [shutil.which("node"), "-e", code,
             str(Path(patches.__file__).with_name("bootstrap.cjs")), core_new],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exact_target_anchor_must_occur_once(self):
        old, new = patches.CORE_PATCHES[-1]
        self.assertEqual(patches.replace_once(old, old, new), new)
        for source in ("no native construction", old + "\n" + old):
            with self.subTest(source=source[:30]), self.assertRaises(HarnessError):
                patches.replace_once(source, old, new)


if __name__ == "__main__":
    unittest.main()
