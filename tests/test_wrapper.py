"""Regression tests with a recording doas stub; never elevate privileges."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'sudo').read_text()
SHELL = os.environ.get('FAKE_SUDO_TEST_SHELL', '/bin/sh')
ARGS = ['', 'a\x1fb', 'space name', 'line\nbreak\n', '*.gz', '-rf', "quote'\\", '']


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fake-sudo-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.output = self.root / 'argv.json'
        self.probe = self.bin / 'probe'
        self.probe.write_text('#!' + sys.executable + '\nimport json,os,sys\n'
                              'with open(os.environ["PROBE_OUTPUT"], "w") as f: json.dump(sys.argv[1:], f)\n')
        self.probe.chmod(0o700)
        self.identity = self.bin / 'id'
        self.identity.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_IDENTITY"\n')
        self.identity.chmod(0o700)

    def run_wrapper(self, args, backend=False, user='tester'):
        # This changes discovery in a temporary copy only; tests cannot call
        # a real doas even if one is installed on the host.
        source = SOURCE.replace('DOAS_SAFE_PATH="$(get_doas_safe_path)"',
                                'DOAS_SAFE_PATH=' + shlex.quote(str(self.bin) + ':/usr/bin:/bin'))
        if backend:
            stub = self.bin / 'doas'
            stub.write_bytes(self.probe.read_bytes())
            stub.chmod(0o700)
        else:
            source = source.replace('if PATH="$DOAS_SAFE_PATH" command -v doas >/dev/null 2>&1; then',
                                    'if false; then')
        wrapper = self.root / 'sudo'
        wrapper.write_text(source)
        env = dict(os.environ, PROBE_OUTPUT=str(self.output), TEST_IDENTITY=user,
                   SHELL=str(self.probe))
        return subprocess.run([SHELL, str(wrapper), *args], env=env,
                              capture_output=True, text=True, timeout=10)

    def recorded(self):
        return json.loads(self.output.read_text())

    def test_fallback_arguments(self):
        result = self.run_wrapper([str(self.probe), *ARGS])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), ARGS)

    def test_end_of_options(self):
        result = self.run_wrapper(['--', str(self.probe), *ARGS])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), ARGS)

    def test_doas_arguments(self):
        result = self.run_wrapper(['-n', '-u', 'nobody', str(self.probe), *ARGS], backend=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), ['-u', 'nobody', '-n', '--', str(self.probe), *ARGS])

    def test_reject_root_privilege_drop_without_backend(self):
        result = self.run_wrapper(['-u', 'nobody', str(self.probe)], user='root')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('refusing execution', result.stderr)
        self.assertFalse(self.output.exists())

    def test_reject_explicit_root_for_unprivileged_caller(self):
        result = self.run_wrapper(['--user=root', str(self.probe)])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_allow_explicit_current_user(self):
        result = self.run_wrapper(['-u', 'tester', str(self.probe), *ARGS])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), ARGS)

    def test_reject_shell_and_background_identity_switch(self):
        for mode in ('-s', '-i', '-b'):
            with self.subTest(mode=mode):
                result = self.run_wrapper(['-u', 'nobody', mode, str(self.probe)], user='root')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())

    def test_identity_lookup_failure(self):
        self.identity.write_text('#!/bin/sh\nexit 1\n')
        result = self.run_wrapper(['-u', 'tester', str(self.probe)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cannot determine current user', result.stderr)
        self.assertFalse(self.output.exists())

    def test_missing_command(self):
        result = self.run_wrapper(['--'])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
