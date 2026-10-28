"""Bounded cleanup of a child owned by the PTY test."""
import os
import signal
import time


def cleanup(pid, *, waitpid=os.waitpid, send=os.kill, clock=time.monotonic,
            sleep=time.sleep, grace=1.0):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            send(pid, sig)
        except ProcessLookupError:
            pass
        deadline = clock() + grace
        while clock() < deadline:
            try:
                ended, status = waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                return True
            if ended:
                return True
            sleep(min(0.05, max(0.0, deadline - clock())))
    return False
