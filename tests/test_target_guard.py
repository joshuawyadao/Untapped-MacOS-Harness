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
        core_old, core_new = patches.CORE_PATCHES[-1]
        self.assertIn("new GameScryInstance", core_new)
        self.assertLess(core_new.index("__untappedHarnessAssertTargetPid"),
                        core_new.index("new GameScryInstance"))
        code = textwrap.dedent(r"""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const vm = require('node:vm');
            const bootstrap = fs.readFileSync(process.argv[1], 'utf8');
            const targetCode = process.argv[2];
            const executable = '/private/tmp/test game/SlayTheSpire2.app/Contents/MacOS/Slay the Spire 2';
            function run(env, pid, franchise='STS2', psRow='502 ' + executable) {
              let psCalls = 0, constructed = 0, disposed = 0;
              const globals = {};
              const proc = { env: { UC_TEST_SANDBOX_DIR: '/private/tmp/test-profile',
                UNTAPPED_HARNESS_OFFLINE: '1', ...env }, getuid: () => 502 };
              const electron = { app: { setPath() {}, setLoginItemSettings() {},
                setAsDefaultProtocolClient() {}, whenReady: () => Promise.resolve() },
                shell: { openExternal() {} } };
              const fsStub = { mkdirSync() {}, appendFileSync() {} };
              const child = { execFileSync: (command, args, opts) => {
                psCalls++;
                assert.equal(command, '/bin/ps');
                assert.deepEqual(Array.from(args), ['-p', String(pid), '-o', 'uid=,comm=']);
                assert.equal(opts.timeout, 2000);
                return psRow;
              } };
              const requireStub = name => ({ 'node:fs': fsStub, 'node:path': path,
                'node:module': { _load() {} }, electron, 'node:child_process': child })[name];
              vm.runInNewContext(bootstrap, { require: requireStub, process: proc,
                global: globals, Date });
              const callback = new Function('pid', 'franchise', 'global',
                'GameScryInstance', targetCode);
              const instance = { disposeScry() { disposed++; } };
              const Native = function(info) { constructed++; this.info = info; };
              let error = null;
              try { callback.call(instance, pid, franchise, globals, Native); }
              catch (caught) { error = caught; }
              return { error, psCalls, constructed, disposed, scry: instance._scry };
            }
            const target = { UNTAPPED_HARNESS_TARGET_PID: '71',
              UNTAPPED_HARNESS_TARGET_UID: '502',
              UNTAPPED_HARNESS_TARGET_EXECUTABLE: executable };
            for (const env of [{}, { ...target, UNTAPPED_HARNESS_TARGET_PID: '071' },
              { ...target, UNTAPPED_HARNESS_TARGET_UID: '0502' },
              { ...target, UNTAPPED_HARNESS_TARGET_EXECUTABLE: 'relative/game' }]) {
              const result = run(env, 71);
              assert.ok(result.error);
              assert.equal(result.constructed, 0);
              assert.equal(result.disposed, 0);
              assert.equal(result.psCalls, 0);
            }
            const wrongPid = run(target, 72);
            assert.ok(wrongPid.error);
            assert.equal(wrongPid.constructed, 0);
            assert.equal(wrongPid.psCalls, 0);
            for (const row of ['503 ' + executable, '502 /private/tmp/other',
              '', '502 ' + executable + '\n502 /private/tmp/other']) {
              const result = run(target, 71, 'STS2', row);
              assert.ok(result.error);
              assert.equal(result.constructed, 0);
              assert.equal(result.disposed, 0);
              assert.equal(result.psCalls, 1);
            }
            const match = run(target, 71);
            assert.equal(match.error, null);
            assert.equal(match.psCalls, 1);
            assert.equal(match.constructed, 1);
            assert.equal(match.disposed, 1);
            assert.equal(match.scry.info.pid, 71);
            const otherGame = run({}, 71, 'MTGA');
            assert.equal(otherGame.error, null);
            assert.equal(otherGame.constructed, 1);
            assert.equal(otherGame.psCalls, 0);
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
