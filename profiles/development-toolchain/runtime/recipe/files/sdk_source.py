# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; explicit SDK API1 source selection for host controllers.
"""Load the selected SDK source. Never discover ambient installed packages."""
import importlib
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True

_loaded = None


def load(source=None):
    global _loaded
    source = source or os.environ.get('EMBERBSD_SDK_SOURCE') or _loaded
    if not source:
        raise RuntimeError('Set --sdk-source or EMBERBSD_SDK_SOURCE to an SDK API1 source tree')
    root = Path(source)
    if not root.is_absolute():
        raise RuntimeError('SDK source must be an absolute path')
    root = root.resolve(strict=True)
    package = root / 'src' / 'emberbsd_sdk'
    if not (package / '__init__.py').is_file():
        raise RuntimeError('Missing SDK source package: ' + str(package))
    if _loaded is not None:
        if _loaded != root:
            raise RuntimeError('Cannot change SDK source in one process')
        return str(root)
    prior = sys.modules.get('emberbsd_sdk')
    if prior is not None and Path(prior.__file__).resolve().parent != package:
        raise RuntimeError('An ambient SDK package is already loaded')
    sys.path.insert(0, str(root / 'src'))
    sdk = importlib.import_module('emberbsd_sdk')
    if Path(sdk.__file__).resolve().parent != package or type(sdk.API_VERSION) is not int or sdk.API_VERSION != 1:
        raise RuntimeError('SDK host API1 is required')
    _loaded = root
    return str(root)


def arguments(argv):
    args = list(argv)
    source = None
    clean = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == '--sdk-source' or arg.startswith('--sdk-source='):
            if source is not None:
                raise RuntimeError('Duplicate --sdk-source')
            if '=' in arg:
                source = arg.split('=', 1)[1]
            else:
                index += 1
                if index >= len(args):
                    raise RuntimeError('Missing --sdk-source value')
                source = args[index]
            if not source:
                raise RuntimeError('Missing --sdk-source value')
        else:
            clean.append(arg)
        index += 1
    load(source)
    return clean
