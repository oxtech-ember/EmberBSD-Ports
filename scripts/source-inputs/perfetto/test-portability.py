#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check common Perfetto portability code with selected host tools."""
import argparse
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'cxx', 'python', 'build-flags-dir', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--flag', action='append', default=[])
a = p.parse_args()
for name in ('source', 'cxx', 'python', 'build_flags_dir'):
    path = getattr(a, name)
    if not path.is_absolute() or not path.exists(): p.error(name + ' must be an absolute existing path')
if not a.work.is_absolute() or a.work.exists(): p.error('work must be a new absolute path')
a.work.mkdir(parents=True)
base = [str(a.cxx), *a.flag, '-std=c++17', '-O2', '-I'+str(a.source), '-I'+str(a.source/'include'), '-I'+str(a.build_flags_dir)]
main = a.work/'murmur.cc'
main.write_text(r'''#include <cstdio>
#include "perfetto/ext/base/murmur_hash.h"
int main() {
  unsigned char bytes[32]; for (unsigned i = 0; i < 32; ++i) bytes[i] = static_cast<unsigned char>(i * 17 + 3);
  for (unsigned off = 0; off < 8; ++off) for (unsigned n = 0; n < 16; ++n)
    std::printf("%llu\n", static_cast<unsigned long long>(perfetto::base::murmur_internal::MurmurHashBytes(bytes + off, n)));
}
''')
exe = a.work/'murmur'; subprocess.run(base+[str(main), '-o', str(exe)], check=True)
actual = [int(x) for x in subprocess.check_output([str(exe)], text=True).splitlines()]
mask=(1<<64)-1; mul=0xc6a4a7935bd1e995
def reference(data):
    h=(0xe17a1465 ^ (len(data)*mul)) & mask
    for i in range(0, len(data)//8*8, 8):
        k=int.from_bytes(data[i:i+8], sys.byteorder); k=(k*mul)&mask; k^=k>>47; k=(k*mul)&mask
        h=((h^k)*mul)&mask
    tail=data[len(data)//8*8:]
    if tail: h=((h^int.from_bytes(tail,'little'))*mul)&mask
    h^=h>>47;h=(h*mul)&mask;h^=h>>47
    return h
sample=bytes((i*17+3)&255 for i in range(32))
assert actual == [reference(sample[o:o+n]) for o in range(8) for n in range(16)]
header = '#include "src/trace_processor/importers/proto/typed_proto_field.h"\n'
common = '''using namespace protozero::proto_utils;
struct Meta : FieldMetadataBase { static constexpr int kFieldId = 1; static constexpr ProtoSchemaType kProtoFieldType = TYPE; };
inline constexpr Meta field{};
auto f(const perfetto::trace_processor::TypedProtoField& p) { return p.Cast<field>(); }
'''
for name, value, success in [('supported','ProtoSchemaType::kUint32',True),('unsupported','static_cast<ProtoSchemaType>(255)',False)]:
    cpp=a.work/(name+'.cc');cpp.write_text(header+common.replace('TYPE',value))
    q=subprocess.run(base+['-c',str(cpp),'-o',str(a.work/(name+'.o'))],text=True,capture_output=True)
    assert (q.returncode==0)==success, q.stderr
    if not success: assert 'Unsupported proto schema type' in q.stderr
run=a.source/'gn/run_binary.py'; launcher=a.work/'launcher.py'; marker=a.work/'argv.txt'
launcher.write_text('import pathlib,subprocess,sys\npathlib.Path('+repr(str(marker))+').write_text(repr(sys.argv[1:]))\nsys.exit(subprocess.call(sys.argv[4:]))\n')
child=[str(a.python),'-c','import sys;sys.exit(37)']
assert subprocess.run([str(a.python),str(run),*child]).returncode==37
assert subprocess.run([str(a.python),str(run),'--runtime-launcher',str(launcher),'--runtime-view',str(a.work),'--',*child]).returncode==37
assert marker.read_text() == repr(['--runtime-view',str(a.work),'--',*child])
assert subprocess.run([str(a.python),str(run),'--runtime-launcher','x'],capture_output=True).returncode != 0
print('Murmur 0..15/alignment reference, proto rejection and default/scoped exit propagation: PASS')
