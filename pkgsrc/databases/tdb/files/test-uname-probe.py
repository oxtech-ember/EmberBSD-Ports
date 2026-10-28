#!/usr/bin/env python3
"""Check Waf uname defaults and the selective TDB configuration."""
import importlib.util
from pathlib import Path
import sys

source = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(source / 'third_party/waf'), str(source / 'buildtools'),
                str(source / 'buildtools/wafsamba')]
spec = importlib.util.spec_from_file_location(
    'samba_conftests_test', source / 'buildtools/wafsamba/samba_conftests.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Probe:
    def __init__(self):
        self.fields = []

    def CHECK_CODE(self, code, **kwargs):
        self.fields.append(kwargs['define'])
        return True

full = Probe()
assert module.CHECK_UNAME(full)
assert full.fields == ['SYSTEM_UNAME_SYSNAME', 'SYSTEM_UNAME_MACHINE',
                       'SYSTEM_UNAME_RELEASE', 'SYSTEM_UNAME_VERSION']
selected = Probe()
assert module.CHECK_UNAME(selected, fields=('sysname',))
assert selected.fields == ['SYSTEM_UNAME_SYSNAME']
print('uname probe selection: PASS')
