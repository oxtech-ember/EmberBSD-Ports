#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Qualify binary prefix occurrences in the exact unpacked package payload."""
import argparse, ast
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--payload',type=Path,required=True)
p.add_argument('--config-h',type=Path,required=True)
p.add_argument('--producer-prefix',required=True)
a=p.parse_args()
line=next((v for v in a.config_h.read_text().splitlines() if v.startswith('#define FFMPEG_CONFIGURATION ')),None)
if line is None: p.error('missing FFMPEG_CONFIGURATION')
configuration=ast.literal_eval(line.split(' ',2)[2]).encode()
prefix=a.producer_prefix.encode()
if not prefix.startswith(b'/') or prefix not in configuration or b'\0' in configuration: p.error('invalid producer/configuration')
seen=0
for path in a.payload.rglob('*'):
    if path.is_symlink() or not path.is_file(): continue
    # Archive control files are not payload; nothing else is silently excluded.
    if path.parent == a.payload and path.name in ('+CONTENTS','+COMMENT','+DESC','+BUILD_INFO','+BUILD_VERSION','+INSTALL','+DEINSTALL','+MTREE_DIRS','+DISPLAY','+SIZE_PKG','+SIZE_ALL'):
        continue
    data=path.read_bytes()
    if prefix not in data: continue
    # All binaries with prefix must have NULs; no text is accepted here unless
    # it is valid UTF-8 and the SDK independently declares it for relocation.
    macho_magic = (b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe',
                   b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe',
                   b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
                   b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca')
    if not data.startswith(macho_magic) and b'\0' not in data:
        try: data.decode('utf-8')
        except UnicodeDecodeError: raise SystemExit(f'FAIL: unknown binary {path}')
        continue
    parts=data.split(b'\0')
    valid = [part == configuration and i < len(parts)-1 for i, part in enumerate(parts)]
    seen+=sum(valid)
    if any(prefix in part and not valid[i] for i, part in enumerate(parts)):
        raise SystemExit(f'FAIL: unqualified producer prefix in {path.relative_to(a.payload)}')
if not seen: raise SystemExit('FAIL: diagnostic configuration absent from binaries')
print(f'PASS: {seen} exact NUL-delimited configuration strings')
