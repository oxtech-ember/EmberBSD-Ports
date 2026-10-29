#!/usr/bin/env python3
"""Check LLVM consumer RPATH selection with real pkgsrc makefiles."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('bmake', 'pkgsrc', 'baseline-pkgsrc', 'stage-makeconf', 'native-makeconf', 'cross-makeconf', 'prefix'):
    p.add_argument('--'+name, type=Path, required=True)
a = p.parse_args()
def query(tree, package, conf, *extra, cross=False):
    cmd = [str(a.bmake), '-C', str(tree/package), 'MAKECONF='+str(conf),
           *([] if cross else ['EMBERBSD_DARWIN_BOOTSTRAP=yes']), '_PKGSRC_BARRIER=yes',
           *extra, '-V', '${CMAKE_CONFIGURE_ARGS}', '-V', '${CMAKE_CONFIGURE_ARGS.Darwin}']
    return [word for line in subprocess.check_output(cmd, text=True).splitlines()
            for word in shlex.split(line) if word.startswith(('-DCMAKE_INSTALL_RPATH=', '-DCMAKE_INSTALL_RPATH:'))]
def variables(tree, package, conf, *names, cross=False, extra=()):
    cmd = [str(a.bmake), '-C', str(tree/package), 'MAKECONF='+str(conf),
           *([] if cross else ['EMBERBSD_DARWIN_BOOTSTRAP=yes']), '_PKGSRC_BARRIER=yes', *extra]
    for name in names:
        cmd += ['-V', '${'+name+'}']
    return subprocess.check_output(cmd, text=True).splitlines()

for package, revision in (('lang/clang', 'clang-23.1.4nb12'),
                          ('devel/lld', 'lld-23.1.4nb7'),
                          ('devel/lldb', 'lldb-23.1.4nb5')):
    assert variables(a.pkgsrc, package, a.stage_makeconf, 'PKGNAME') == [revision]
    assert variables(a.pkgsrc, package, a.native_makeconf, 'PKGNAME', extra=('EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=',)) == variables(a.baseline_pkgsrc, package, a.native_makeconf, 'PKGNAME', extra=('EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=',))
    assert variables(a.pkgsrc, package, a.cross_makeconf, 'PKGNAME', cross=True) == variables(a.baseline_pkgsrc, package, a.cross_makeconf, 'PKGNAME', cross=True)
assert 'lld>=23.1.4nb7:' in variables(a.pkgsrc, 'lang/clang', a.stage_makeconf, 'DEPENDS')[0]
assert 'clang>=23.1.4nb12:' in variables(a.pkgsrc, 'devel/lldb', a.stage_makeconf, 'DEPENDS')[0]
bindings_deps = variables(a.pkgsrc, 'lang/clang-python-bindings', a.stage_makeconf, 'DEPENDS')[0]
assert 'clang-23.1.4{,nb*}:' in bindings_deps, bindings_deps
assert 'clang>=23.1.4nb12:' in bindings_deps, bindings_deps
assert variables(a.pkgsrc, 'lang/clang-python-bindings', a.stage_makeconf, 'PKGNAME') == ['clang-python-bindings-23.1.4nb1']
assert 'clang>=23.1.4nb12:' in variables(a.pkgsrc, 'devel/rust-bindgen', a.stage_makeconf, 'DEPENDS')[0]
assert variables(a.pkgsrc, 'devel/rust-bindgen', a.stage_makeconf, 'PKGNAME') == ['rust-bindgen-0.73.2nb3']
assert 'clang>=23.1.4nb12<23.2:' in variables(a.pkgsrc, 'parallel/spirv-llvm-translator', a.stage_makeconf, 'BUILD_DEPENDS')[0]
for package in ('lang/clang-python-bindings', 'devel/rust-bindgen', 'parallel/spirv-llvm-translator'):
    for conf, cross, extra in ((a.native_makeconf, False, ('EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=',)),
                               (a.cross_makeconf, True, ())):
        assert variables(a.pkgsrc, package, conf, 'PKGNAME', cross=cross, extra=extra) == variables(a.baseline_pkgsrc, package, conf, 'PKGNAME', cross=cross, extra=extra)
expected = '-DCMAKE_INSTALL_RPATH:STRING=@loader_path/../lib;'+str(a.prefix/'lib')
for package in ('lang/clang', 'devel/lld', 'devel/lldb'):
    values = query(a.pkgsrc, package, a.stage_makeconf)
    assert values == [expected], (package, values)
    with tempfile.TemporaryDirectory() as temporary:
        conf = Path(temporary) / 'mk.conf'
        conf.write_text('.include "'+str(a.stage_makeconf)+'"\n'
                        'CMAKE_CONFIGURE_ARGS+= -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=FALSE\n')
        values = query(a.pkgsrc, package, conf)
        assert values == [expected], (package, values)
    for override in ('-DCMAKE_INSTALL_RPATH:STRING=/chosen/one;/chosen/two',
                     '-DCMAKE_INSTALL_RPATH=/chosen/one;/chosen/two'):
        values = query(a.pkgsrc, package, a.stage_makeconf, 'CMAKE_CONFIGURE_ARGS='+override)
        assert values == [override], (package, values)
    assert query(a.pkgsrc, package, a.native_makeconf) == query(a.baseline_pkgsrc, package, a.native_makeconf)
    assert query(a.pkgsrc, package, a.cross_makeconf, cross=True) == query(a.baseline_pkgsrc, package, a.cross_makeconf, cross=True)
# An unrelated LLVM buildlink consumer does not opt into LLVM's setup policy.
assert query(a.pkgsrc, 'lang/compiler-rt', a.stage_makeconf) == query(a.baseline_pkgsrc, 'lang/compiler-rt', a.stage_makeconf)
print('PASS: LLVM stage RPATH, explicit override, unrelated/native/cross behavior')
