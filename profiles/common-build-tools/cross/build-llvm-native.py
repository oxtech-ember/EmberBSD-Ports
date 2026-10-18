#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import signal
import sys
sys.dont_write_bytecode = True
from llvm_host import load_sdk, native
if __name__ == '__main__':
    def terminated(signum, frame):
        raise KeyboardInterrupt('Native generator build interrupted')
    signal.signal(signal.SIGTERM, terminated)
    try:
        _, args = load_sdk()
        native('llvm', args)
    except Exception as error:
        sys.exit(f'FAIL: {error}')
