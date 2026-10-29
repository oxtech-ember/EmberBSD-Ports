#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Adapt a compatible existing native llvm-config without changing it."""
import argparse
import os
from pathlib import Path
import shlex
import sys
sys.dont_write_bytecode = True
import llvm_admission
import llvm_sdk as sdk


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', required=True)
    parser.add_argument('--target-build', required=True)
    parser.add_argument('--sysroot', required=True)
    parser.add_argument('--native-build', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--sealed-darwin-bundle')
    parser.add_argument('--relocated-installed-prefix', action='store_true')
    args = parser.parse_args(arguments)
    output = Path(args.output)
    if not output.is_absolute() or os.path.lexists(output):
        raise ValueError('output must be an absent absolute path')
    command = llvm_admission.validate(args.real, args.target_build, args.sysroot, args.native_build, sealed_darwin_bundle=args.sealed_darwin_bundle, relocated_installed_prefix=args.relocated_installed_prefix)
    output.parent.mkdir(parents=True, exist_ok=True)
    runner = ('import os,sys; env={k:v for k,v in os.environ.items() ' +
              'if not k.startswith((\"LD_\",\"DYLD_\"))}; ' +
              'os.execve(sys.argv[1],sys.argv[1:],env)')
    text = ('#!/bin/sh\n# SPDX-License-Identifier: BSD-2-Clause\nset -eu\n' +
            'unset LD_PRELOAD LD_AUDIT LD_LIBRARY_PATH DYLD_INSERT_LIBRARIES ' +
            'DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH DYLD_FALLBACK_LIBRARY_PATH ' +
            'DYLD_FALLBACK_FRAMEWORK_PATH DYLD_ROOT_PATH\nexec ' +
            shlex.join([sys.executable, '-B', '-c', runner, *command]) + ' "$@"\n')
    with output.open('x') as stream:
        stream.write(text)
    output.chmod(0o755)
    print(output)
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(main))
