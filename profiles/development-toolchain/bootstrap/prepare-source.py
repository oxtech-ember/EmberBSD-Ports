#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; explicit SDK API1 source preparation entry point.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime/recipe/files'))
import sdk_source
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    try:
        sdk_source.install_signal_handlers()
        args = sdk_source.arguments(sys.argv[1:])
        from host import build_path, prepare_source, require
        require(len(args) == 3, 'Usage: prepare-source.py PKGSRC ARCHIVE NEW_SOURCE --sdk-source SOURCE')
        prepare_source(*(build_path(arg) for arg in args))
    except Exception as error:
        print(str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
