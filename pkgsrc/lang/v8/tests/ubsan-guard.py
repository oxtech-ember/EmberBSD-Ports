#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Ensure V8 retains its sanitizer-aware behavior on BSD targets."""
import argparse
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--clang', type=Path, required=True)
a = parser.parse_args()
text = (a.source / 'src/base/macros.h').read_text()
match = re.search(r'(#if defined\(__has_feature\)\n#if __has_feature\(undefined_behavior_sanitizer\).*?\n#endif\n#endif)', text, re.S)
assert match, 'missing V8 undefined behavior sanitizer detection'
probe = match.group(1) + '\n#ifdef V8_USE_UNDEFINED_BEHAVIOR_SANITIZER\nENABLED\n#else\nDISABLED\n#endif\n'
for platform in ('NETBSD', 'OPENBSD', 'FREEBSD', 'DRAGONFLYBSD', 'DARWIN'):
    for sanitizer, expected in ((True, 'ENABLED'), (False, 'DISABLED')):
        command = [str(a.clang), '-E', '-P', '-x', 'c++', '-DV8_OS_BSD', '-DV8_OS_' + platform]
        if sanitizer:
            command.append('-fsanitize=undefined')
        result = subprocess.run(command + ['-'], input=probe, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode == 0 and result.stdout.strip() == expected, (platform, sanitizer, result.stderr)
print('V8 UBSan detection retained on NetBSD, OpenBSD, FreeBSD, DragonFly, and Darwin')
