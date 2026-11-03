"""Preflight gates app startup, budgets time and preserves diagnostic privacy."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from harness import controlled
from harness.asar import HarnessError


def passing_preflight():
    return {'passed':True, 'requests_attempted':2, 'maximum_requests':2,
            'results':[{'route':'accounts_account','status':401,'response_kind':'JSON','body_bytes':85,'json_object':True},
                       {'route':'oauth_token','status':401,'response_kind':'JSON','body_bytes':27,'json_object':True}]}


class FakeGateway:
    def __init__(self, result=None):
        self.result = passing_preflight() if result is None else result
        self.counts = {}
        self.failure_details = []
        self.failure_overflow = 0
        self.cleanup_complete = True
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def preflight(self):
        self.counts = {('accounts_account',401):1, ('oauth_token',401):1}
        if not self.result.get('passed'):
            self.counts = {('error',502):1}
            self.failure_details = [{'route':'accounts_account','stage':'UPSTREAM_TRANSPORT',
                'transport_error':'TLS_CERTIFICATE_ERROR','elapsed_ms':10,'message':'secret-token'}]
        return self.result


class ControlledPreflightTests(unittest.TestCase):
    def run_fixture(self, session, home, gateway, launch, *, elapsed=2.4):
        with patch.object(controlled.game_launch,'test_identity',return_value=('sts2test',home,Path('/protected'))), \
             patch.object(controlled,'proposal',return_value={}), \
             patch.object(controlled.reward_probe,'_process_inventory',return_value=''), \
             patch.object(controlled.cli,'_validate_launch_copy',return_value=(session,{},session/'Companion.app')) as validate, \
             patch.object(controlled,'Gateway',return_value=gateway), \
             patch.object(controlled.cli,'launch_outer',launch), \
             patch.object(controlled.cli,'load_events',return_value=[{'event':'authenticated'}]), \
             patch.object(controlled.time,'monotonic',side_effect=[100,100+elapsed]), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            result = controlled.run(session,approved=True)
        validate.assert_called_once_with(session)
        self.assertTrue(gateway.closed)
        diagnostic = next(line.removeprefix('Diagnostic file: ') for line in output.getvalue().splitlines() if line.startswith('Diagnostic file: '))
        self.assertEqual(json.loads(Path(diagnostic).read_text()),result)
        Path(diagnostic).unlink()
        return result

    def session(self, home):
        session = home/'companion'; session.mkdir(mode=0o700)
        (session/'signing.json').write_text('{}')
        return session

    def test_pass_opens_app_with_remaining_budget_and_separate_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve(); session=self.session(home); gateway=FakeGateway()
            def launched(*args,**kwargs):
                self.assertEqual(args,(session,297))
                self.assertEqual(kwargs,{'approved':True,'_controlled':gateway})
                gateway.counts[('oauth_token',200)]=1
                return {'startup':'ELECTRON_READY','launch':{'exit_code':0},'attempt_dir':str(session/'attempt')}
            launch=Mock(side_effect=launched)
            result=self.run_fixture(session,home,gateway,launch)
            self.assertTrue(result['preflight']['passed'])
            self.assertEqual(result['gateway_counts'],[{'route':'oauth_token','status':200,'count':1}])
            self.assertEqual(len(result['preflight_gateway_counts']),2)
            self.assertTrue(result['report']['launch']['app_started'])
            self.assertEqual(result['gateway_failures'],[])
            self.assertEqual(result['events'],[{'event':'authenticated'}])

    def test_failed_preflight_never_opens_app_and_exports_only_fixed_failure_fields(self):
        failure={'passed':False,'requests_attempted':1,'results':[{'route':'accounts_account','status':502,'response_kind':'TEXT','body_bytes':14,'secret':'secret-token'}]}
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve(); session=self.session(home); gateway=FakeGateway(failure); launch=Mock()
            result=self.run_fixture(session,home,gateway,launch)
        launch.assert_not_called()
        self.assertEqual(result['report']['startup'],'NOT_ATTEMPTED_PREFLIGHT_FAILED')
        self.assertFalse(result['report']['launch']['app_started'])
        self.assertEqual(result['gateway_counts'],[])
        self.assertEqual(result['gateway_failures'][0]['phase'],'preflight')
        self.assertEqual(result['gateway_failures'][0]['transport_error'],'TLS_CERTIFICATE_ERROR')
        self.assertEqual(result['events'],[])
        self.assertNotIn('secret-token',json.dumps(result))

    def test_expired_total_budget_never_opens_app_after_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve(); session=self.session(home); launch=Mock()
            result=self.run_fixture(session,home,FakeGateway(),launch,elapsed=301)
        launch.assert_not_called()
        self.assertTrue(result['preflight']['passed'])
        self.assertEqual(result['report']['startup'],'NOT_ATTEMPTED_TIME_BUDGET')

    def test_export_sanitizers_drop_arbitrary_values_and_require_two_expected_results(self):
        raw=passing_preflight(); raw['account']='secret-token'; raw['results'][0]['url']='secret-token'
        self.assertNotIn('secret-token',json.dumps(controlled.sanitized_preflight(raw)))
        raw['results'].append({'route':'private@example.test'})
        self.assertFalse(controlled.sanitized_preflight(raw)['passed'])
        raw['results'][0]['route']=['secret-token']
        self.assertFalse(controlled.sanitized_preflight(raw)['passed'])
        rows=[{'route':'private@example.test','stage':['secret-token'],'transport_error':['secret-token'],
               'os_errno':'secret-token','message':'secret-token','elapsed_ms':100}]*40
        safe=controlled.sanitized_failures(rows,1)
        self.assertEqual(len(safe),32)
        self.assertNotIn('secret-token',json.dumps(safe))
        self.assertNotIn('private@',json.dumps(safe))
        self.assertEqual(safe[0]['phase'],'preflight')
        self.assertEqual(safe[1]['phase'],'companion')
        raw=passing_preflight();raw['results'][0]['json_object']=False
        self.assertFalse(controlled.sanitized_preflight(raw)['passed'])

    def test_invalid_signed_copy_stops_before_gateway_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve();session=self.session(home)
            with patch.object(controlled.game_launch,'test_identity',return_value=('sts2test',home,Path('/protected'))), \
                 patch.object(controlled,'proposal',return_value={}), \
                 patch.object(controlled.reward_probe,'_process_inventory',return_value=''), \
                 patch.object(controlled.cli,'_validate_launch_copy',side_effect=HarnessError('invalid signature')), \
                 patch.object(controlled,'Gateway') as gateway:
                with self.assertRaisesRegex(HarnessError,'invalid signature'):
                    controlled.run(session,approved=True)
            gateway.assert_not_called()

    def test_late_error_after_failed_preflight_remains_preflight(self):
        class LateGateway(FakeGateway):
            def __exit__(self,*args):
                self.counts[('error',502)]=2
                self.failure_details.append({'route':'accounts_account','stage':'LOCAL_RESPONSE',
                    'transport_error':'CONNECTION_CLOSED','elapsed_ms':15000})
                return super().__exit__(*args)
        failure={'passed':False,'requests_attempted':1,'results':[{'route':'accounts_account','status':502,'response_kind':'OTHER','body_bytes':14}]}
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve();session=self.session(home);launch=Mock()
            result=self.run_fixture(session,home,LateGateway(failure),launch)
        launch.assert_not_called()
        self.assertEqual(result['gateway_counts'],[])
        self.assertEqual(result['preflight_gateway_counts'],[{'route':'error','status':502,'count':2}])
        self.assertEqual([x['phase'] for x in result['gateway_failures']],['preflight','preflight'])

    def test_cleanup_failure_never_produces_a_clean_export(self):
        failure={'passed':False,'requests_attempted':0,'results':[]}
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve(); session=self.session(home); gateway=FakeGateway(failure);gateway.cleanup_complete=False
            with patch.object(controlled.game_launch,'test_identity',return_value=('sts2test',home,Path('/protected'))), \
                 patch.object(controlled,'proposal',return_value={}), \
                 patch.object(controlled.reward_probe,'_process_inventory',return_value=''), \
                 patch.object(controlled.cli,'_validate_launch_copy'), \
                 patch.object(controlled,'Gateway',return_value=gateway), \
                 patch.object(controlled.tempfile,'NamedTemporaryFile') as output, \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(HarnessError,'cleanup'):
                    controlled.run(session,approved=True)
            output.assert_not_called()


if __name__=='__main__':
    unittest.main()
