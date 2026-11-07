"""Offline regression tests; these never connect to Packet Tracer."""

import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import pt_client
import verify_audit_remediation as verifier


class ClientTests(unittest.TestCase):
    def test_nested_qt_arrays_and_ordinary_objects(self):
        value = {'result': {'length': 2, '0': {'length': 0}, '1': {'length': 8, 'name': 'PC0'}}}
        self.assertEqual(pt_client.normalize(value), {'result': [[], {'length': 8, 'name': 'PC0'}]})

    def test_malformed_arrays_fail_without_silent_data_loss(self):
        for value in [
            {'length': -1}, {'length': True}, {'length': '1'},
            {'length': 2, '0': 1}, {'length': 1, '0': 1, '1': 2},
            {'length': 1, '01': 1},
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                pt_client.normalize(value)

    def test_call_unwraps_payload_and_closes_response(self):
        response = io.BytesIO(json.dumps({'code': 0, 'result': {'length': 1, '0': 'ok'}}).encode())
        with patch.object(pt_client.urllib.request, 'urlopen', return_value=response) as open_url:
            self.assertEqual(pt_client.call('getDevices'), ['ok'])
        self.assertTrue(response.closed)
        self.assertEqual(open_url.call_args.kwargs['timeout'], 60)

    def test_output_must_stay_inside_evidence(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pt_client, 'BASE', Path(directory)):
            self.assertEqual(pt_client.evidence_path('run/result.json'), Path(directory) / 'evidence/run/result.json')
            for name in ['../README.md', '.', str(Path(directory) / 'outside.json')]:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    pt_client.evidence_path(name)


class CheckpointTests(unittest.TestCase):
    def test_verifier_rejects_paths_outside_evidence(self):
        with self.assertRaisesRegex(ValueError, 'inside project evidence'):
            verifier.verify(SCRIPTS)

    def test_failed_checkpoint_is_rejected_even_in_optimized_python(self):
        code = """
from unittest.mock import patch
import verify_audit_remediation as verifier
progress = {'currentCheckpoint': {'iteration': 5}, 'iterations': {'5': 'failed'}}
with patch.object(verifier, 'read_json', return_value=progress):
    verifier.verify(verifier.DEFAULT_RUN)
"""
        result = subprocess.run(
            [sys.executable, '-O', '-c', code], cwd=SCRIPTS,
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ValueError: Checkpoint validation failed', result.stderr)
        self.assertNotIn('KeyError', result.stderr)


if __name__ == '__main__':
    unittest.main()
