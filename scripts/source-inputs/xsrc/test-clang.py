#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Compile the xsrc sources fixed by patches/ with the selected target Clang.

Each case is a construct that the pinned NetBSD 11.0 set rejects under the
OS build's -Werror with a current Clang. Run it against a prepared tree to
check the patches and against an unpatched tree to see the cases fail.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True, help='prepared or unpatched xsrc tree')
parser.add_argument('--clang', type=Path, required=True, help='absolute target Clang driver')
parser.add_argument('--sysroot', type=Path, required=True,
                    help='target DESTDIR holding the base and installed X11 headers')
parser.add_argument('--target', default='aarch64--netbsd')
parser.add_argument('--expect-failure', action='store_true', help='require every case to fail')
args = parser.parse_args()
root = args.source / 'external/mit'
mesa = root / 'MesaLib/dist'
x11 = args.sysroot / 'usr/X11R7/include'
common = [str(args.clang), '--target=' + args.target, '--sysroot=' + str(args.sysroot),
          # Code generation: Clang checks alias types only when it emits code.
          '-S', '-o', os.devnull, '-Werror', '-Wall']

CASES = {
    # libxcb sized the first setup read for the generic header only.
    'libxcb read_setup': (['-std=gnu11', '-DHAVE_CONFIG_H', '-I', str(root / 'libxcb/include'),
                           '-I', str(x11 / 'xcb'), '-I', str(x11),
                           str(root / 'libxcb/dist/src/xcb_conn.c')], None),
    # Mesa's ralloc C++ operators used the deprecated __has_trivial_destructor.
    'Mesa HAS_TRIVIAL_DESTRUCTOR': (['-x', 'c++', '-std=c++17', '-Wdeprecated-builtins',
                                     '-I', str(mesa / 'include'), '-I', str(mesa / 'src')],
                                    '#include "util/macros.h"\n'
                                    'struct plain { int value; };\n'
                                    'struct owner { ~owner(); };\n'
                                    'static_assert(HAS_TRIVIAL_DESTRUCTOR(plain), "trivial");\n'
                                    'static_assert(!HAS_TRIVIAL_DESTRUCTOR(owner), "not trivial");\n'),
    # Gallium called software winsys constructors through an unprototyped pointer.
    'Mesa sw_driver winsys': (['-x', 'c', '-std=gnu11', '-Wstrict-prototypes', '-Wdeprecated-non-prototype',
                               '-I', str(mesa / 'include'), '-I', str(mesa / 'src'),
                               '-I', str(mesa / 'src/gallium/include'),
                               '-I', str(mesa / 'src/gallium/auxiliary')],
                              '#include "frontend/sw_driver.h"\n'
                              'struct sw_winsys *create(const struct sw_driver_descriptor *dd,\n'
                              '                         const struct drisw_loader_funcs *lf,\n'
                              '                         struct pipe_screen *screen, int fd)\n'
                              '{\n'
                              '   return dd->winsys[0].create_winsys_dri(lf) ?\n'
                              '          dd->winsys[1].create_winsys_kms_dri(fd) :\n'
                              '          dd->winsys[2].create_winsys_null() ?\n'
                              '          dd->winsys[3].create_winsys_null() :\n'
                              '          dd->winsys[3].create_winsys_wrapped(screen);\n'
                              '}\n'),
    # GLX aliased the SGIX entry point whose attribute list is not const.
    'Mesa glXChooseFBConfigSGIX alias': (['-std=gnu11', '-pthread', '-DHAVE_PTHREAD=1',
                                          '-DHAVE_TIMESPEC_GET', '-DHAVE_FUNC_ATTRIBUTE_ALIAS=1',
                                          '-I', str(mesa / 'include'), '-I', str(mesa / 'src'),
                                          '-I', str(mesa / 'src/loader'), '-I', str(mesa / 'src/mapi'),
                                          '-I', str(mesa / 'src/mapi/glapi'), '-I', str(mesa / 'src/mesa'),
                                          '-I', str(mesa / 'src/glx'),
                                          '-I', str(root / 'MesaLib/src/mapi/glapi/gen'),
                                          '-I', str(x11), str(mesa / 'src/glx/glxcmds.c')], None),
    # GLU's NURBS varray used the C++17-removed register storage class.
    'GLU varray register': (['-x', 'c++', '-std=c++17', '-DNDEBUG', '-DLIBRARYBUILD',
                             '-I', str(root / 'glu/dist/include'),
                             '-I', str(root / 'glu/dist/src/include'),
                             '-I', str(root / 'glu/dist/src/libnurbs/internals'),
                             '-I', str(root / 'glu/dist/src/libnurbs/interface'),
                             '-I', str(root / 'glu/dist/src/libnurbs/nurbtess'), '-I', str(x11),
                             str(root / 'glu/dist/src/libnurbs/internals/varray.cc')], None),
    # xedit's regex compiler compared values of two different enumerations.
    'xedit re string list type': (['-std=gnu11', '-I', str(root / 'xedit/dist/lisp/re'),
                                   str(root / 'xedit/dist/lisp/re/re.c')], None),
    'xedit rec repetition type': (['-std=gnu11', '-I', str(root / 'xedit/dist/lisp/re'),
                                   str(root / 'xedit/dist/lisp/re/rec.c')], None),
}

failed = []
with tempfile.TemporaryDirectory() as tmp:
    for name, (words, text) in CASES.items():
        command = common + words
        if text is not None:
            case = Path(tmp) / (name.replace(' ', '-') + '.src')
            case.write_text(text)
            command.append(str(case))
        result = subprocess.run(command, capture_output=True, text=True)
        if (result.returncode != 0) != args.expect_failure:
            failed.append(name)
            sys.stderr.write(f'{name}: unexpected result {result.returncode}\n{result.stderr}')
if failed:
    raise SystemExit('xsrc clang cases: FAIL: ' + ', '.join(failed))
print('xsrc clang cases: PASS' + (' (all fail unpatched)' if args.expect_failure else ''))
