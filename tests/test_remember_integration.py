"""Exercise opt-in bootstrap validation and launcher propagation without credentials."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from harness import main_companion, remember_patch
from harness.asar import HarnessError, sha256


class RememberLaunchTests(unittest.TestCase):
    def test_optional_helper_is_pinned_and_default_launch_remains_memory_only(self):
        for enabled in (False, True, 'bad-hash'):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve(); (root / 'profile').mkdir(mode=0o700)
                helper = Path(main_companion.__file__).with_name('remember_keytar.cjs').read_bytes()
                adapter = Path(main_companion.__file__).with_name('controlled_network.cjs').read_bytes()
                (root / 'manifest.json').write_text(json.dumps({
                    'controlled_network_sha256': sha256(adapter), 'remember_login_version': 1,
                    'remember_login_helper_sha256': 'wrong' if enabled == 'bad-hash' else sha256(helper)}))
                broker = SimpleNamespace(environment={'UNTAPPED_HARNESS_LOGIN_SOCKET': str(root / 'remember.sock'),
                                                       'UNTAPPED_HARNESS_LOGIN_CAPABILITY': 'a'*64})
                with patch.object(main_companion.cli, 'launch_environment', return_value={}), \
                     patch.object(main_companion.cli, 'sandbox_profile', return_value='existing-policy'), \
                     patch.object(main_companion.process_identity, 'prepare_identity_probe', return_value={'sha256': 'probe'}), \
                     patch.object(main_companion.subprocess, 'Popen') as start:
                    if enabled == 'bad-hash':
                        with self.assertRaises(HarnessError):
                            main_companion._launch(root, SimpleNamespace(url='local', key='cap'), {}, '123', 0, broker)
                        start.assert_not_called()
                        continue
                    main_companion._launch(root, SimpleNamespace(url='local', key='cap'), {}, '123', 0,
                                           broker if enabled else None)
                    env = start.call_args.kwargs['env']
                    target = root / 'profile/remember-keytar.cjs'
                    if enabled:
                        self.assertEqual(env['UNTAPPED_HARNESS_REMEMBER_LOGIN'], '1')
                        self.assertEqual(env['UNTAPPED_HARNESS_LOGIN_HELPER_SHA256'], sha256(helper))
                        self.assertEqual(target.read_bytes(), helper)
                        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
                    else:
                        self.assertNotIn('UNTAPPED_HARNESS_REMEMBER_LOGIN', env)
                        self.assertFalse(target.exists())

    @unittest.skipUnless(shutil.which('node'), 'Node is required')
    def test_real_bootstrap_hook_requires_opt_in_and_validated_private_helper(self):
        hook = Path(remember_patch.__file__).with_name('remember_bootstrap.cjs').read_text()
        script = r'''
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const assert = require('node:assert/strict');
const root = process.argv[1], hook = process.argv[2], profile = path.join(root, 'profile');
fs.mkdirSync(profile, {mode:0o700});
const helper = path.join(profile, 'remember-keytar.cjs');
fs.writeFileSync(helper, 'exports.create = () => ({restored:true});', {mode:0o600});
const digest = crypto.createHash('sha256').update(fs.readFileSync(helper)).digest('hex');
const env = {UNTAPPED_HARNESS_MAIN_ACCOUNT:'1', UNTAPPED_HARNESS_REMEMBER_LOGIN:'1',
  UNTAPPED_HARNESS_LOGIN_SOCKET:path.join(root,'remember.sock'),
  UNTAPPED_HARNESS_LOGIN_CAPABILITY:'a'.repeat(64), UNTAPPED_HARNESS_LOGIN_HELPER_SHA256:digest};
const run = new Function('controlled','process','profile','path','fs','require','memoryKeytar',
  hook + '\nreturn harnessRememberKeytar;');
const invoke = (changes={}, controlled=true) => run(controlled,
  {env:{...env,...changes}, getuid:process.getuid}, profile,path,fs,require,{});
assert.equal(invoke().restored,true);
assert.equal(invoke({UNTAPPED_HARNESS_REMEMBER_LOGIN:'0'}),null);
assert.equal(invoke({UNTAPPED_HARNESS_MAIN_ACCOUNT:'0'}),null);
assert.equal(invoke({},false),null);
for(const changes of [{UNTAPPED_HARNESS_LOGIN_HELPER_SHA256:'b'.repeat(64)},
 {UNTAPPED_HARNESS_LOGIN_SOCKET:'/wrong'}, {UNTAPPED_HARNESS_LOGIN_CAPABILITY:'bad'}]) {
 assert.throws(()=>invoke(changes), /failed validation/);
}
fs.chmodSync(helper,0o644); assert.throws(()=>invoke(),/failed validation/);
fs.chmodSync(helper,0o600); fs.renameSync(helper,helper+'.real'); fs.symlinkSync(helper+'.real',helper);
assert.throws(()=>invoke(),/failed validation/);
'''
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([shutil.which('node'), '-e', script, str(Path(temp).resolve()), hook],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
