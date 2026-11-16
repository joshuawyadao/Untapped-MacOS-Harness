"""Check that the required CI gate covers portable and macOS validation."""

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CINativeTests(unittest.TestCase):
    def test_required_gate_rejects_failed_cancelled_and_skipped_jobs(self):
        script = ROOT / 'scripts/check_ci_results.sh'
        for job in ('PORTABLE', 'NATIVE'):
            for result in ('failure', 'cancelled', 'skipped'):
                with self.subTest(job=job, result=result):
                    environment = dict(os.environ, PORTABLE_RESULT='success', NATIVE_RESULT='success')
                    environment[f'{job}_RESULT'] = result
                    completed = subprocess.run([str(script)], env=environment, capture_output=True, text=True)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(f'{job} check result: {result}', completed.stderr)

        environment = dict(os.environ, PORTABLE_RESULT='success', NATIVE_RESULT='success')
        self.assertEqual(subprocess.run([str(script)], env=environment).returncode, 0)

    def test_workflow_runs_native_sources_and_native_seam_before_required_gate(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assertIn('name: CI Verify', workflow)
        self.assertIn('needs: [portable, native]', workflow)
        self.assertIn('if: always()', workflow)
        self.assertIn('run: ./scripts/check_native_ci.sh', workflow)
        self.assertIn('run: python3 -m unittest discover -s tests -p test_launcher_native.py -v', workflow)
        self.assertIn('PORTABLE_RESULT: ${{ needs.portable.result }}', workflow)
        self.assertIn('NATIVE_RESULT: ${{ needs.native.result }}', workflow)
        self.assertIn('run: ./scripts/check_ci_results.sh', workflow)
        aggregate = workflow.split('\n  verify:\n', 1)[1]
        checkout = aggregate.index('uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1')
        gate = aggregate.index('run: ./scripts/check_ci_results.sh')
        self.assertLess(checkout, gate)
        self.assertIn('persist-credentials: false', aggregate[:gate])


if __name__ == '__main__':
    unittest.main()
