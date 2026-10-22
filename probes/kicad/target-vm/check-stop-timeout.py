#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Causal bounded SSH pipe control; no guest use.
import subprocess
import unittest
from stop import HaltTimeout, ssh_halt


class TimeoutTests(unittest.TestCase):
    def test_stuck_pipes_cannot_exceed_whole_deadline(self):
        class Child:
            elapsed = 0
            terminated = False
            killed = False
            timeouts = []
            def communicate(self, *, timeout):
                # The independent oracle refuses the former unbounded call.
                self.assert_timeout(timeout)
                self.timeouts.append(timeout)
                self.elapsed += timeout
                raise subprocess.TimeoutExpired(['owned-ssh'], timeout, output=b'partial ACK\n', stderr=b'diagnostic\n')
            def assert_timeout(self, timeout):
                if timeout is None or not 0 < timeout <= 45 - self.elapsed:
                    raise AssertionError('SSH pipe wait escaped the whole deadline')
            def terminate(self):
                self.terminated = True
            def kill(self):
                self.killed = True
        child = Child()
        with self.assertRaisesRegex(HaltTimeout, 'pipes did not close after kill; QEMU retained') as caught:
            ssh_halt(['owned-ssh'], 45, clock=lambda: child.elapsed, popen=lambda *a, **k: child)
        self.assertEqual(caught.exception.stdout, b'partial ACK\n')
        self.assertEqual(caught.exception.stderr, b'diagnostic\n')
        self.assertEqual(child.timeouts, [35, 5, 5])
        self.assertEqual(child.elapsed, 45)
        self.assertTrue(child.terminated and child.killed)

    def test_success_keeps_exact_status_and_bytes(self):
        class Child:
            returncode = 255
            def communicate(self, *, timeout):
                return b'ACK\n', b'connection closed\n'
            def terminate(self):
                raise AssertionError('successful SSH must not be terminated')
            kill = terminate
        self.assertEqual(ssh_halt(['owned-ssh'], 45, clock=lambda: 0, popen=lambda *a, **k: Child()),
                         (255, b'ACK\n', b'connection closed\n'))


if __name__ == '__main__':
    unittest.main()
