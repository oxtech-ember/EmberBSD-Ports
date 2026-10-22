#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual macOS-to-NetBSD CUPS build.
"""Validate target GSSAPI selection where the Mac host has GSS.framework."""

import argparse
from pathlib import Path
import re
import subprocess


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('sysroot', type=Path)
    parser.add_argument('readelf')
    parser.add_argument('--kerberos-config', required=True, type=Path)
    parser.add_argument('--gss-library', help='Required GSSAPI ELF SONAME')
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    sysroot = args.sysroot.resolve(strict=True)
    provider = args.kerberos_config.resolve(strict=True)
    require(provider.is_relative_to(sysroot), 'Kerberos config is outside the target sysroot')
    require(Path('/System/Library/Frameworks/GSS.framework').is_dir(), 'Regression requires a Mac host with GSS.framework')
    log = (source / 'config.log').read_text()
    require(re.search(r"^build_os='darwin", log, re.M), 'CUPS was not configured on Darwin')
    require(re.search(r"^host_os='netbsd", log, re.M), 'CUPS target is not NetBSD')
    require(f"KRB5CONFIG='{args.kerberos_config}'" in log.splitlines(), 'Configured Kerberos provider differs from the selected script')
    config = (source / 'config.h').read_text().splitlines()
    require('#define HAVE_GSSAPI 1' in config, 'GSSAPI was disabled')
    require('#define HAVE_GSSAPI_GSSAPI_H 1' in config, 'Target GSSAPI header was not found')
    require('#define HAVE_GSS_GSSAPI_H 1' not in config, 'Host GSS framework header entered the target configuration')
    for line in (source / 'Makedefs').read_text().splitlines():
        key, separator, value = line.partition('=')
        if separator and key.strip() in {'LIBGSSAPI', 'LIBS', 'DSOFLAGS', 'LDFLAGS'}:
            require('framework' not in value and 'search_paths_first' not in value, 'Host framework linker flags entered the target build')
    library = source / 'cups/libcups.so.2'
    header = subprocess.run([str(args.readelf), '-h', str(library)], check=True, capture_output=True, text=True).stdout
    require(re.search(r'Machine:\s+AArch64', header), 'CUPS library is not AArch64 ELF')
    if args.gss_library:
        dynamic = subprocess.run([str(args.readelf), '-d', str(library)], check=True, capture_output=True, text=True).stdout
        require(f'[{args.gss_library}]' in dynamic, 'CUPS library does not link the selected GSSAPI provider')
    print('PASS: actual CUPS target GSS headers, sysroot provider and ELF shared library')


if __name__ == '__main__':
    main()
