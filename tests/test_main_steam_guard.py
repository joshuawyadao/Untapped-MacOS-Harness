"""Execute the original main-mode settings assertion against synthetic values."""
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path

from harness import cli, patches


class MainSteamGuardTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for guard execution")
    def test_account_and_profile_are_exact_and_events_disclose_no_values(self):
        script = textwrap.dedent(r"""
          const assert = require('node:assert/strict');
          const fs = require('node:fs');
          const vm = require('node:vm');
          const source = fs.readFileSync(process.argv[1], 'utf8');
          const start = source.indexOf('  global.__untappedHarnessMainSteamVerified = false;');
          const end = source.indexOf('  global.__untappedHarnessAssertTargetPid =', start);
          assert.ok(start >= 0 && end > start);
          const id = '76561198912345678';
          const names = [];
          function boot(env, controlled=true) {
            const global = { __untappedHarnessEvent: name => names.push(name) };
            vm.runInNewContext(source.slice(start,end), { global, process:{env}, controlled });
            return {check:global.__untappedHarnessAssertSteamSettings,canShow:global.__untappedHarnessCanShowSts2Overlay};
          }
          const env = { UNTAPPED_HARNESS_MAIN_ACCOUNT:'1',
            UNTAPPED_HARNESS_EXPECTED_STEAM_ID:id, UNTAPPED_HARNESS_EXPECTED_PROFILE:'1' };
          const {check,canShow} = boot(env);
          assert.equal(canShow(), false);
          check(null);
          assert.deepEqual(names, []);
          assert.equal(canShow(), false);
          check({ steamUserId:id, currentProfile:1, netId:null });
          assert.equal(names.pop(), 'main-steam-verified');
          assert.equal(canShow(), true);
          check(null);
          assert.equal(canShow(), false);
          for (const settings of [
            {steamUserId:'987654321',currentProfile:1},
            {steamUserId:Number(id),currentProfile:1},
            {steamUserId:id,currentProfile:0},
            {steamUserId:id,currentProfile:'1'},
            {steamUserId:id,currentProfile:1.5}, undefined
          ]) {
            assert.throws(() => check(settings), /Main harness Steam account or profile mismatch/);
            assert.equal(names.pop(), 'main-steam-mismatch');
            assert.equal(canShow(), false);
          }
          assert.throws(() => boot(env,false).check({steamUserId:id,currentProfile:1}));
          assert.throws(() => boot({...env,UNTAPPED_HARNESS_EXPECTED_PROFILE:'01'}).check({steamUserId:id,currentProfile:1}));
          const offline = boot({});
          offline.check({steamUserId:'unrelated',currentProfile:-1});
          assert.equal(offline.canShow(), true);
          assert.ok(names.every(name => ['main-steam-verified','main-steam-mismatch'].includes(name)));
          assert.ok(!JSON.stringify(names).includes(id));
        """)
        result = subprocess.run([shutil.which("node"), "-e", script,
                         str(Path(cli.__file__).with_name("bootstrap.cjs"))], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node is required for guard execution")
    def test_settings_callback_hides_an_already_visible_overlay_on_mismatch(self):
        prefix = next(new.split('      this.state.settings.set(curr);')[0]
                      for old, new in patches.CORE_PATCHES if old.startswith('      this.state.settings.set(curr);'))
        script = textwrap.dedent(r"""
          const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
          const source = fs.readFileSync(process.argv[1],'utf8');
          const start = source.indexOf('  global.__untappedHarnessMainSteamVerified = false;');
          const end = source.indexOf('  global.__untappedHarnessAssertTargetPid =',start);
          const global = {__untappedHarnessEvent:()=>{}};
          const context = {global, controlled:true,process:{env:{UNTAPPED_HARNESS_MAIN_ACCOUNT:'1',
            UNTAPPED_HARNESS_EXPECTED_STEAM_ID:'12345678901234567',UNTAPPED_HARNESS_EXPECTED_PROFILE:'1'}}};
          vm.runInNewContext(source.slice(start,end),context);
          const callback = vm.runInNewContext('(function(curr){'+process.argv[2]+'})',context);
          let visible = true;
          const receiver = {overlay:{hide:()=>{visible=false;}}};
          callback.call(receiver,{steamUserId:'12345678901234567',currentProfile:1});
          assert.equal(visible,true);
          assert.throws(()=>callback.call(receiver,{steamUserId:'987',currentProfile:1}));
          assert.equal(visible,false);
          assert.equal(global.__untappedHarnessCanShowSts2Overlay(),false);
        """)
        result = subprocess.run([shutil.which("node"), "-e", script,
                   str(Path(cli.__file__).with_name("bootstrap.cjs")), prefix], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
