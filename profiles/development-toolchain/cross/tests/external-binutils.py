#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; external-toolchain Binutils contract, prepared with AI assistance.
"""The installed prefix must contain every tool bsd.own.mk selects."""
from pathlib import Path
import sys
import tempfile
sys.dont_write_bytecode = True
PROFILE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
sdk_source.arguments(sys.argv[1:])
sys.path.insert(0, str(PROFILE))
import host
from emberbsd_sdk.errors import SDKError


def executable(path):
    path.write_text('#!/bin/sh\nexit 0\n')
    path.chmod(0o755)


def main():
    triplet = 'aarch64--netbsd'
    with tempfile.TemporaryDirectory(prefix='ember-external-binutils-') as temporary:
        prefix = Path(temporary) / 'toolchain'
        bindir = prefix / 'bin'
        bindir.mkdir(parents=True)
        for name in host.BINUTILS:
            if name != 'size':
                executable(bindir / (triplet + '-' + name))
        try:
            host.require_tools(prefix, triplet, host.BINUTILS)
        except SDKError as error:
            message = str(error)
        else:
            raise SystemExit('A prefix without size was accepted')
        if 'Missing required external toolchain tools: size' not in message:
            raise SystemExit('Missing size was not named: ' + message)
        if 'Required:' not in message or 'elfedit' not in message or 'strings' not in message:
            raise SystemExit('Required tool list was omitted: ' + message)
        executable(bindir / (triplet + '-size'))
        host.require_tools(prefix, triplet, host.BINUTILS)
        # addr2line and c++filt are outside the EXTERNAL_TOOLCHAIN contract.
        for extra in ('addr2line', 'c++filt'):
            if extra in host.BINUTILS:
                raise SystemExit(extra + ' is not selected by bsd.own.mk EXTERNAL_TOOLCHAIN')
    print('PASS: installed toolchain rejects a missing size and accepts the external Binutils set')


if __name__ == '__main__':
    try:
        sdk_source.install_signal_handlers()
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
