#!/usr/bin/env python3
"""Exercise cleanup deadlines without starting or signalling a process."""
import signal
import unittest
from pty_cleanup import cleanup


class Fake:
    def __init__(self, finish=False):
        self.now = 0.0
        self.signals = []
        self.finish = finish

    def clock(self):
        return self.now

    def sleep(self, duration):
        self.now += duration

    def send(self, pid, sig):
        self.signals.append((pid, sig))

    def waitpid(self, pid, flags):
        return (pid, 0) if self.finish else (0, 0)


class CleanupTest(unittest.TestCase):
    def test_unresponsive_is_bounded(self):
        f = Fake()
        self.assertFalse(cleanup(123, waitpid=f.waitpid, send=f.send,
                                 clock=f.clock, sleep=f.sleep, grace=1.0))
        self.assertEqual(f.signals, [(123, signal.SIGTERM), (123, signal.SIGKILL)])
        self.assertLessEqual(f.now, 2.0)

    def test_reaped_after_term(self):
        f = Fake(finish=True)
        self.assertTrue(cleanup(123, waitpid=f.waitpid, send=f.send,
                                clock=f.clock, sleep=f.sleep, grace=1.0))
        self.assertEqual(f.signals, [(123, signal.SIGTERM)])


if __name__ == '__main__':
    unittest.main()
