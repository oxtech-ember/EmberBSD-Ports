#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Exercise actual patched LLVM parser using bounded provider fixtures.
import argparse
from pathlib import Path
import subprocess
import tempfile
p=argparse.ArgumentParser(); p.add_argument('--source',type=Path,required=True); p.add_argument('--cxx',type=Path,required=True); p.add_argument('--work',type=Path,required=True); a=p.parse_args()
a.work.mkdir(parents=True,exist_ok=True)
s=(a.source/'libunwind/src/EHHeaderParser.hpp').read_text(); cursor=(a.source/'libunwind/src/UnwindCursor.hpp').read_text(); assert '(!indexPresent || sects.dwarf_section_length != SIZE_MAX)' in cursor and cursor.index('DwarfFDECache<A>::template findFDE<R>(sects.dso_base, pc)') < cursor.index('(!indexPresent || sects.dwarf_section_length != SIZE_MAX)') and 'findOtherFDE<R>(pc, fde)' in cursor; start=s.index('template <typename A> class EHHeaderParser'); end=s.rindex('\n}')
with tempfile.TemporaryDirectory(dir=a.work) as d:
 root=Path(d); (root/'unwind-index-body.inc').write_text(s[start:end]); binary=root/'test'
 subprocess.run([str(a.cxx),'-std=c++17','-Wall','-Wextra','-Werror','-I'+str(root),str(Path(__file__).with_name('unwind-index-fixture.cpp')),'-o',str(binary)],check=True)
 subprocess.run([str(binary)],check=True)
