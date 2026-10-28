#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise extracted V8 stack-bound functions against mocked BSD APIs."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--clang', type=Path, required=True)
a = parser.parse_args()
text = (a.source / 'src/base/platform/platform-posix.cc').read_text()
start = text.index('#if !defined(V8_OS_FREEBSD) && !defined(V8_OS_DARWIN) && !defined(_AIX)', text.index('// pthread_getattr_np used below'))
end = text.index('// static\nvoid Stack::SetCurrentThreadStackBounds', start)
section = text[start:end]
assert 'V8_OS_LINUX && !V8_LIBC_GLIBC && !V8_LIBC_BIONIC && !V8_LIBC_UCLIBC' in section
prefix = '''#include <cstdint>
#include <cstddef>
#if DEBUG
#define DCHECK(x) do { if (!(x)) __builtin_trap(); } while (0)
#else
#define DCHECK(x) do {} while (0)
#endif
#define CHECK(x) do { if (!(x)) __builtin_trap(); } while (0)
using pthread_t = int;
struct pthread_attr_t {};
struct stack_t { void* ss_sp; size_t ss_size; };
char memory[512];
int pthread_self() { return 1; }
int pthread_stackseg_np(int, stack_t* s) { s->ss_sp=memory+300; s->ss_size=200; return 0; }
int pthread_getattr_np(int, pthread_attr_t*) { return 0; }
int pthread_attr_getstack(pthread_attr_t*, void** base, size_t* size) { *base=memory+100; *size=200; return 0; }
int pthread_attr_destroy(pthread_attr_t*) { return 0; }
struct OS { static int GetCurrentThreadId() { return 1; } };
struct Stack { using StackSlot=void*; static StackSlot ObtainCurrentThreadStackStart(); static StackSlot ObtainCurrentThreadStackReservedLimit(); };
'''
main = '''
int main() {
  return Stack::ObtainCurrentThreadStackStart() != memory + 300 ||
         Stack::ObtainCurrentThreadStackReservedLimit() != memory + 100;
}
'''
with tempfile.TemporaryDirectory(prefix='v8-stack-bounds-') as td:
    td = Path(td)
    for platform in ('OPENBSD', 'NETBSD'):
        for debug in (0, 1):
            binary = td / (platform + str(debug))
            result = subprocess.run([str(a.clang), '-std=c++20', '-DV8_OS_' + platform,
                                     '-DDEBUG=' + str(debug), '-x', 'c++', '-', '-o', str(binary)],
                                    input=prefix + section + main, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert result.returncode == 0, (platform, debug, result.stderr)
            assert subprocess.run([str(binary)]).returncode == 0, (platform, debug)
    for platform in ('DARWIN', 'FREEBSD'):
        result = subprocess.run([str(a.clang), '-E', '-P', '-DV8_OS_' + platform,
                                 '-DDEBUG=1', '-x', 'c++', '-'], input=section, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode == 0, result.stderr
        assert 'Stack::ObtainCurrentThreadStackStart' not in result.stdout
        assert 'Stack::ObtainCurrentThreadStackReservedLimit' not in result.stdout
print('BSD mocked stack bounds, debug/release and Darwin/FreeBSD exclusion: PASS')

freebsd = (a.source / 'src/base/platform/platform-freebsd.cc').read_text()
darwin = (a.source / 'src/base/platform/platform-darwin.cc').read_text()
for target in (freebsd, darwin):
    for function in ('ObtainCurrentThreadStackStart', 'ObtainCurrentThreadStackReservedLimit'):
        assert len(re.findall(r'Stack::StackSlot Stack::' + function + r'\(', target)) == 1
match = re.search(r'(Stack::StackSlot Stack::ObtainCurrentThreadStackReservedLimit\(\) \{.*?\n\})', freebsd, re.S)
assert match and len(re.findall(r'Stack::StackSlot Stack::ObtainCurrentThreadStackReservedLimit\(', freebsd)) == 1
assert 'Stack::ObtainCurrentThreadStackStart' not in (a.source / 'src/base/platform/platform-openbsd.cc').read_text()
assert 'Stack::ObtainCurrentThreadStackReservedLimit' not in (a.source / 'src/base/platform/platform-openbsd.cc').read_text()
freebsd_stub = '''#include <cstddef>
using pthread_t = int;
struct pthread_attr_t {};
char memory[512];
int mode=0, destroyed=0;
int pthread_self() { return 1; }
int pthread_attr_init(pthread_attr_t*) { return mode==1 ? 1 : 0; }
int pthread_attr_get_np(int, pthread_attr_t*) { return mode==2 ? 1 : 0; }
int pthread_attr_getstack(pthread_attr_t*, void** base, size_t* size) { if (mode==3) return 1; *base=memory+100; *size=200; return 0; }
int pthread_attr_destroy(pthread_attr_t*) { ++destroyed; return 0; }
struct Stack { using StackSlot=void*; static StackSlot ObtainCurrentThreadStackReservedLimit(); };
'''
freebsd_main = '''
int main() {
  for (mode=0; mode<4; ++mode) {
    destroyed=0; void* result=Stack::ObtainCurrentThreadStackReservedLimit();
    if (result != (mode==0 ? memory+100 : nullptr)) return 1;
    if (destroyed != (mode==1 ? 0 : 1)) return 2;
  }
}
'''
with tempfile.TemporaryDirectory(prefix='v8-freebsd-stack-') as td:
    for debug in (0, 1):
        binary = Path(td) / str(debug)
        result = subprocess.run([str(a.clang), '-std=c++20', '-DDEBUG=' + str(debug),
                                 '-x', 'c++', '-', '-o', str(binary)],
                                input=freebsd_stub + match.group(1) + freebsd_main,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode == 0, result.stderr
        assert subprocess.run([str(binary)]).returncode == 0
print('FreeBSD mocked stack limit and pthread error lifecycle: PASS')
