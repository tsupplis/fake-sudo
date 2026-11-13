"""Exercise the launcher with disposable passing/failing suites."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'sudo_test'


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fake sudo runner ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runner = self.root / 'sudo_test'
        self.runner.write_bytes(RUNNER.read_bytes())
        self.tests = self.root / 'tests'
        self.tests.mkdir()
        self.suite = self.tests / 'test_wrapper.py'
        self.env = dict(os.environ, PYTHON=sys.executable)

    def run_launcher(self, *args):
        return subprocess.run(['/bin/sh', str(self.runner), *args],
                              cwd='/', env=self.env, capture_output=True,
                              text=True, timeout=10)

    def test_success_outside_checkout_with_spaces(self):
        self.suite.write_text('import unittest\nclass Test(unittest.TestCase):\n'
                              '    def test_ok(self): self.assertTrue(True)\n')
        result = self.run_launcher('-q')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Ran 1 test', result.stderr)

    def test_failure_is_propagated(self):
        self.suite.write_text('import unittest\nclass Test(unittest.TestCase):\n'
                              '    def test_bad(self): self.fail("intentional fixture failure")\n')
        result = self.run_launcher()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('intentional fixture failure', result.stderr)

    def test_incomplete_checkout_fails(self):
        result = self.run_launcher()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing tests/test_wrapper.py', result.stderr)

    def test_missing_python_is_reported(self):
        self.env['PYTHON'] = str(self.root / 'missing-python')
        result = self.run_launcher()
        self.assertEqual(result.returncode, 127)
        self.assertIn('Python 3 executable not found', result.stderr)

    def test_help_does_not_need_python_or_tests(self):
        self.env['PYTHON'] = str(self.root / 'missing-python')
        result = self.run_launcher('--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('SSH smoke-test mode has been removed', result.stdout)


if __name__ == '__main__':
    unittest.main()
