"""Controlled supervision and shared-diagnostic privacy, without vendor execution."""
import contextlib
import io
import json
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from harness import cli, controlled
from harness.asar import HarnessError


class ControlledTests(unittest.TestCase):
    def test_no_approval_and_bad_limits_stop_before_account_or_gateway(self):
        with patch.object(controlled.game_launch, 'test_identity') as identity, patch.object(controlled, 'Gateway') as gateway:
            with self.assertRaisesRegex(HarnessError, 'approval'):
                controlled.run('/absent')
            for seconds in (0, 301, True):
                with self.assertRaises(HarnessError):
                    controlled.run('/absent', approved=True, seconds=seconds)
            identity.assert_not_called()
            gateway.assert_not_called()

    def test_sanitized_events_never_copy_unknown_fields_or_auth_values(self):
        raw = [{'event':'authenticated','email':'private@example.test','token':'secret','time':'secret'},
               {'event':'unexpected','token':'secret'},
               {'event':'reward','url':'secret','cards':[{'id':'HAZE','upgradeLevel':0,'cx':0.3,'cy':0.5,
                'width':0.1,'height':0.2,'scaleX':0.8,'scaleY':0.8,'token':'secret'}]}]
        exported = controlled.sanitized_events(raw)
        self.assertEqual(exported[0], {'event':'authenticated'})
        self.assertNotIn('secret', json.dumps(exported))
        self.assertNotIn('private@', json.dumps(exported))
        self.assertEqual(exported[1]['cards'][0]['scaleX'],0.8)
        raw[-1]['cards'][0]['id']='private@example.test'
        with self.assertRaises(HarnessError):
            controlled.sanitized_events(raw)

    def test_proposal_refuses_gateway_or_adapter_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp).resolve()
            manifest={'controlled_access_version':1,
                      'controlled_gateway_sha256':cli.sha256((cli.ROOT/'harness/gateway.py').read_bytes()),
                      'controlled_network_sha256':cli.sha256((cli.ROOT/'harness/controlled_network.cjs').read_bytes())}
            (session/'manifest.json').write_text(json.dumps(manifest))
            proposed=controlled.proposal(session)
            self.assertEqual(proposed['scope'],'MANUAL_OAUTH_AND_PUBLIC_DATA_ONLY')
            self.assertEqual(proposed['outbound_user_agent'], 'node-fetch/1.0 (+https://github.com/bitinn/node-fetch)')
            for key in ('controlled_gateway_sha256','controlled_network_sha256'):
                changed={**manifest,key:'0'*64};(session/'manifest.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(HarnessError,'changed since preparation'):
                    controlled.proposal(session)

    def test_report_export_excludes_future_account_fields_and_raw_errors(self):
        report = {'startup':'ELECTRON_READY','email':'private@example.test',
                  'startup_blockers':['token=secret'], 'launch':{'seconds_limit':300,'token':'secret',
                  'exit_code':'secret','network':'private@example.test'}}
        safe=controlled.sanitized_report(report)
        self.assertEqual(safe['startup_blocker_count'],1)
        self.assertNotIn('secret',json.dumps(safe))
        self.assertNotIn('private@',json.dumps(safe))
        self.assertEqual(safe['launch'],{'seconds_limit':300})

    @unittest.skipUnless(shutil.which('node'), 'Node required for original-bootstrap execution')
    def test_bootstrap_controlled_memory_keytar_and_helper_integrity(self):
        source = Path(cli.ROOT/'harness/bootstrap.cjs')
        code = r"""
        const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path');
        const vm=require('node:vm'), crypto=require('node:crypto'), os=require('node:os');
        const profile=fs.mkdtempSync(path.join(os.tmpdir(),'controlled-fixture-'));
        fs.chmodSync(profile,0o700);
        const helper=path.join(profile,'controlled-network.cjs'); fs.writeFileSync(helper,'original stub',{mode:0o600});
        const hash=crypto.createHash('sha256').update(fs.readFileSync(helper)).digest('hex');
        let loads=0;
        function boot() {
          const mod={_load:()=>{throw Error('native credential module must not load');}};
          const electron={app:{setPath(){},whenReady(){return Promise.resolve()},setLoginItemSettings(){},setAsDefaultProtocolClient(){}},shell:{openExternal(){}}};
          const globals={};
          function req(name){
            if(name===helper)return {install(options){loads++;assert.equal(options.gatewayKey,'k'.repeat(40));return {loadFetch(){return 'wrapped'}};}};
            return {'node:fs':fs,'node:path':path,'node:module':mod,'node:crypto':crypto,electron}[name];
          }
          vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{require:req,global:globals,process:{getuid:process.getuid,env:{
            UC_TEST_SANDBOX_DIR:profile,UNTAPPED_HARNESS_OFFLINE:'1',UNTAPPED_HARNESS_CONTROLLED_ACCESS:'1',
            UNTAPPED_HARNESS_NETWORK_SHA256:hash,UNTAPPED_HARNESS_GATEWAY_URL:'http://127.0.0.1:1234/fetch',UNTAPPED_HARNESS_GATEWAY_KEY:'k'.repeat(40)}}});
          return mod;
        }
        (async()=>{try {
          const mod=boot(), keytar=mod._load('keytar');
          await keytar.setPassword('Untapped.gg Companion','test@example.invalid','fixture-token');
          await keytar.setPassword('another-service','other','must-not-enumerate');
          const credentials=await keytar.findCredentials('Untapped.gg Companion');
          assert.equal(credentials.length,1);assert.equal(credentials[0].password,'fixture-token');
          assert.equal(mod._load('node-fetch'),'wrapped');
          const next=boot();assert.equal((await next._load('keytar').findCredentials('Untapped.gg Companion')).length,0);
          fs.writeFileSync(helper,'changed');assert.throws(boot,/missing or changed/);assert.equal(loads,2);
        }finally{fs.rmSync(profile,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1});
        """
        result=subprocess.run([shutil.which('node'),'-e',code,str(source)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_cli_requires_real_auth_event_not_only_startup_or_timeout(self):
        for events, status in (([],1),([{'event':'authenticated'}],0)):
            result={'events':events,'preflight':{'passed':True},'report':{'startup':'ELECTRON_READY','startup_blocker_count':0,'launch':{}}}
            with patch.object(controlled,'run',return_value=result),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(controlled.main(['/unused','--approve-controlled-access']),status)

    def test_cli_errors_do_not_echo_vendor_credentials(self):
        with patch.object(controlled,'run',side_effect=HarnessError('token=secret email=private@example.test')), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(controlled.main(['/unused','--approve-controlled-access']),2)
        self.assertNotIn('secret',output.getvalue())
        self.assertNotIn('private@',output.getvalue())

    def test_controlled_launcher_keeps_outer_policy_and_cleans_up_on_monitor_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp).resolve();app=session/'Companion.app';app.mkdir()
            (session/'signing.json').write_text('{}')
            manifest={'schema':1,'controlled_access_version':1,'controlled_network_sha256':cli.sha256((cli.ROOT/'harness/controlled_network.cjs').read_bytes())}
            gateway=SimpleNamespace(url='http://127.0.0.1:1234/fetch',key='k'*40)
            process=Mock(pid=1234);process.poll.return_value=None
            process.wait.side_effect=subprocess.TimeoutExpired('fixture',0.5)
            with patch.object(cli,'_validate_launch_copy',return_value=(session,manifest,app)), \
                 patch.object(cli.subprocess,'Popen',return_value=process) as spawn, \
                 patch.object(cli,'stop_probe') as stop, \
                 patch.object(cli,'load_events',side_effect=OSError('private failure')), \
                 contextlib.redirect_stdout(io.StringIO()) as instructions:
                with self.assertRaises(OSError):
                    cli.launch_outer(session,300,approved=True,_controlled=gateway)
            stop.assert_called_once_with(process)
            _,options=spawn.call_args
            environment=options['env'];profile=Path(environment['UC_TEST_SANDBOX_DIR'])
            self.assertIn('After Sign In, run in another Terminal: cat ',instructions.getvalue())
            self.assertIn(str(profile/'manual-sign-in-url.txt'),instructions.getvalue())
            self.assertNotIn(gateway.key,instructions.getvalue())
            self.assertEqual(environment['UNTAPPED_HARNESS_CONTROLLED_ACCESS'],'1')
            self.assertEqual(environment['UNTAPPED_HARNESS_GATEWAY_KEY'],gateway.key)
            self.assertEqual(environment['UNTAPPED_HARNESS_NETWORK_SHA256'],cli.sha256((profile/'controlled-network.cjs').read_bytes()))
            self.assertEqual((profile/'controlled-network.cjs').stat().st_mode&0o777,0o600)
            policy=(profile.parent/'offline.sb').read_text()
            self.assertIn('(deny network*)',policy)
            self.assertNotIn('api.accounts',policy)
            report=json.loads((profile.parent/'launch.json').read_text())
            self.assertNotIn(gateway.key,json.dumps(report))

    def test_controlled_deadline_stops_after_auth_and_never_exports_gateway_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp).resolve();app=session/'Companion.app';app.mkdir()
            (session/'signing.json').write_text('{}')
            process=Mock(pid=1234);process.poll.return_value=None
            process.wait.side_effect=subprocess.TimeoutExpired('fixture',0.5)
            gateway=SimpleNamespace(url='http://127.0.0.1:1234/fetch',key='k'*40)
            with patch.object(cli,'_validate_launch_copy',return_value=(session,{'controlled_access_version':1,'controlled_network_sha256':cli.sha256((cli.ROOT/'harness/controlled_network.cjs').read_bytes())},app)), \
                 patch.object(cli.subprocess,'Popen',return_value=process),patch.object(cli,'stop_probe') as stop, \
                 patch.object(cli,'load_events',return_value=[{'event':'authenticated'}]), \
                 patch.object(cli.time,'monotonic',side_effect=[0,10,56]), \
                 contextlib.redirect_stdout(io.StringIO()):
                report=cli.launch_outer(session,300,approved=True,_controlled=gateway)
            self.assertTrue(report['launch']['authenticated_event_observed'])
            self.assertTrue(report['launch']['time_limit_reached'])
            stop.assert_called_once_with(process)

    def test_controlled_poll_exit_retains_failure_after_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp).resolve();app=session/'Companion.app';app.mkdir()
            (session/'signing.json').write_text('{}')
            process=Mock(pid=1234);process.poll.side_effect=[None,-5]
            process.wait.side_effect=subprocess.TimeoutExpired('fixture',0.5)
            manifest={'controlled_access_version':1,'controlled_network_sha256':cli.sha256((cli.ROOT/'harness/controlled_network.cjs').read_bytes())}
            with patch.object(cli,'_validate_launch_copy',return_value=(session,manifest,app)), \
                 patch.object(cli.subprocess,'Popen',return_value=process),patch.object(cli,'stop_probe') as stop, \
                 patch.object(cli,'load_events',return_value=[{'event':'authenticated'}]),contextlib.redirect_stdout(io.StringIO()):
                report=cli.launch_outer(session,300,approved=True,_controlled=SimpleNamespace(url='http://127.0.0.1:1234/fetch',key='k'*40))
            self.assertEqual(report['launch']['exit_code'],-5)
            self.assertTrue(report['launch']['authenticated_event_observed'])
            stop.assert_called_once_with(process)
            safe={'events':[{'event':'authenticated'}],'preflight':{'passed':True},'report':{'startup':'ELECTRON_READY','launch':{'exit_code':-5}}}
            with patch.object(controlled,'run',return_value=safe),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(controlled.main(['/unused','--approve-controlled-access']),1)

    def test_login_only_refuses_running_game_before_gateway(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve();session=home/'companion';session.mkdir(mode=0o700)
            with patch.object(controlled.game_launch,'test_identity',return_value=('sts2test',home,Path('/protected'))), \
                 patch.object(controlled,'proposal',return_value={}), \
                 patch.object(controlled.reward_probe,'_process_inventory',return_value='42 502 /another/Slay the Spire 2\n'), \
                 patch.object(controlled,'Gateway') as gateway:
                with self.assertRaisesRegex(HarnessError,'Close Steam'):
                    controlled.run(session,approved=True)
                gateway.assert_not_called()
