"""Check that the required CI gate covers portable and macOS validation."""

import os
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CINativeTests(unittest.TestCase):
    def test_required_gate_accepts_only_explicit_success_for_both_jobs(self):
        script = ROOT / 'scripts/check_ci_results.sh'
        for job in ('PORTABLE', 'NATIVE'):
            for result in ('failure', 'cancelled', 'skipped', None, '', 'unknown'):
                with self.subTest(job=job, result=result):
                    environment = dict(os.environ, PORTABLE_RESULT='success', NATIVE_RESULT='success')
                    if result is None:
                        environment.pop(f'{job}_RESULT')
                    else:
                        environment[f'{job}_RESULT'] = result
                    completed = subprocess.run([str(script)], env=environment, capture_output=True, text=True)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(f'{job} check result: {result or "missing"}', completed.stderr)

        environment = dict(os.environ, PORTABLE_RESULT='success', NATIVE_RESULT='success')
        self.assertEqual(subprocess.run([str(script)], env=environment).returncode, 0)

    def test_workflow_runs_native_sources_and_native_seam_before_required_gate(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        def job_config(name):
            match = re.search(rf'(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [\w-]+:\n|\Z)', workflow)
            self.assertIsNotNone(match, f'Missing workflow job: {name}')
            return match.group(1)

        native = job_config('native')
        self.assertIn('runs-on: macos-15', native)
        self.assertIn('run: ./scripts/check_native_ci.sh', native)
        self.assertIn('run: python3 -m unittest discover -s tests -p test_launcher_native.py -v', native)
        self.assertIn('run: python3 -m unittest discover -s tests -p test_live_inventory.py -v', native)
        aggregate = job_config('verify')
        self.assertIn('name: CI Verify', aggregate)
        self.assertIn('needs: [portable, native]', aggregate)
        self.assertIn('if: always()', aggregate)
        self.assertIn('PORTABLE_RESULT: ${{ needs.portable.result }}', aggregate)
        self.assertIn('NATIVE_RESULT: ${{ needs.native.result }}', aggregate)
        checkout = aggregate.index('uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1')
        gate = aggregate.index('run: ./scripts/check_ci_results.sh')
        self.assertLess(checkout, gate)
        self.assertIn('persist-credentials: false', aggregate[:gate])


if __name__ == '__main__':
    unittest.main()
