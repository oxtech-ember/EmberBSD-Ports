#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Select the installed native Wayland scanner through the shared SDK API."""
import argparse
import importlib.util
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'host-prefix', 'scanner', 'pkg-config'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    loader = Path(__file__).resolve().parents[3]/'lang/llvm/files/sdk_source.py'
    spec = importlib.util.spec_from_file_location('wayland_sdk_source', loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_sdk(['--sdk-source', str(args.sdk_source)])
    from emberbsd_sdk.native_toolset import load_host_prefix
    from emberbsd_sdk.process import capture, sanitized_environment
    from emberbsd_sdk.errors import SDKError
    native = load_host_prefix(args.host_prefix,
                              required_roles=('python', 'wayland-scanner', 'pkg-config'))
    for path, role in ((Path(sys.executable), 'python'), (args.scanner, 'wayland-scanner'),
                       (args.pkg_config, 'pkg-config')):
        if not path.is_absolute() or path != Path(native.tool(role)):
            raise SDKError('The selected '+role+' differs from the native Ports prefix')
    environment = sanitized_environment()
    environment['PATH'] = native.path
    result = capture(native.command('wayland-scanner')+('--version',), env=environment)
    if (result.stdout+result.stderr).decode().strip() != 'wayland-scanner 1.26.0':
        raise SDKError('The native wayland-scanner must report exactly 1.26.0')
    print('Native Wayland scanner selected from '+native.bundle_root)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Wayland scanner selection failed: '+str(error), file=sys.stderr)
        raise SystemExit(1)
