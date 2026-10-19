# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Load only the explicitly selected SDK API. Import itself has no effects."""
import importlib
import os
from pathlib import Path
import sys

# prepare-tools.py imports the GCC16 host.py with only this module on the
# path, and host.py imports this name.  Keep the value equal to the GCC16
# runtime sdk_source.py; tests/prepare-tools-target.py compares them.
PRODUCER_QUARANTINE = '.producer-ownership-unproven.json'


def load_sdk(arguments=None):
    args = sys.argv[1:] if arguments is None else list(arguments)
    source = os.environ.get('EMBERBSD_SDK_SOURCE')
    if '--sdk-source' in args:
        index = args.index('--sdk-source')
        if index + 1 == len(args) or args.count('--sdk-source') != 1:
            raise ValueError('--sdk-source requires one source directory')
        source = args[index + 1]
        del args[index:index + 2]
    if not source or not os.path.isabs(source):
        raise ValueError('Use --sdk-source or EMBERBSD_SDK_SOURCE with an absolute SDK source')
    root = Path(source).resolve(strict=True)
    package = root / 'src' / 'emberbsd_sdk'
    if not (package / '__init__.py').is_file():
        raise ValueError('SDK source has no emberbsd_sdk API')
    loaded = sys.modules.get('emberbsd_sdk')
    if loaded is not None and Path(loaded.__file__).resolve().parent != package:
        raise ValueError('A different SDK API is already loaded')
    sys.path.insert(0, str(root / 'src'))
    sdk = importlib.import_module('emberbsd_sdk')
    if type(sdk.API_VERSION) is not int or sdk.API_VERSION != 1 or Path(sdk.__file__).resolve().parent != package:
        raise ValueError('The selected SDK must provide API version 1')
    return str(root), args


def install_signal_handlers():
    """Set entrypoint policy. Library imports do not change signal handlers."""
    import signal

    def interrupted(number, frame):
        raise SystemExit(128 + number)

    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, interrupted)


def exit_error(error, prefix='FAIL: '):
    """Preserve completed producer status after explicit SDK selection."""
    errors = sys.modules.get('emberbsd_sdk.errors')
    status = 1
    if errors is not None and isinstance(error, errors.CommandError):
        status = error.returncode if error.returncode >= 0 else 128 - error.returncode
    print(prefix + str(error), file=sys.stderr)
    raise SystemExit(status)
