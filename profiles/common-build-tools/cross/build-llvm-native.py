#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import sys
sys.dont_write_bytecode = True
from llvm_host import load_sdk, native
if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        native('llvm', args)
    except Exception as error:
        exit_error(error)
