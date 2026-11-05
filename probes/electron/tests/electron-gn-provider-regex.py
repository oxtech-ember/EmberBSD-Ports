#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""GN parses the actual patch and emits literal pkg-config regex anchors."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
patch=(Path(__file__).resolve().parents[1]/'patches/gn-common-provider-escaped-anchors.patch').read_text()
added=re.findall(r'^\+\s+extra_args = \[ "-v", ("[^"]+") \]$', patch, re.M)
removed=re.findall(r'^-\s+extra_args = \[ "-v", ("[^"]+") \]$', patch, re.M)
assert len(added) == len(removed) == 3
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp).resolve()
    (root/'.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n')
    (root/'BUILDCONFIG.gn').write_text('set_default_toolchain("//:host")\n')
    def run(expressions):
        (root/'BUILD.gn').write_text('toolchain("host") { tool("stamp") { command = "/usr/bin/touch {{output}}" } }\n'+
            ''.join('print('+value+')\n' for value in expressions)+'group("all") {}\n')
        return subprocess.run([sys.argv[1], 'gen', str(root/'out'), '--root='+str(root)],capture_output=True,text=True)
    old=run(removed)
    assert old.returncode != 0 and '$ at end of string' in old.stdout+old.stderr
    new=run(added)
    assert new.returncode == 0, new.stderr+new.stdout
    assert new.stdout.splitlines()[:3] == ['^-licui18n$', '^-licuuc$', '^-lre2$'], new.stdout
print('PASS: actual patch makes selected GN emit exact pkg-config regex anchors')
