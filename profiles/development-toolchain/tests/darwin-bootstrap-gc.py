#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check that Darwin GCC16 stage 2 and stage 3 use the same GC parameters.

GCC's variable-location debug information depends on when its garbage
collector runs. The stage 1 compiler is built with checking, so its collection
defaults (ggc-min-expand=30, ggc-min-heapsize=4096) differ from the release
defaults of the stage 2 compiler. Stage 2 and stage 3 objects then get other
__debug_loc, __debug_info or __debug_line bytes from the same code, and the
stage 2/3 comparison fails. The recipe must pass the same --param values
through BOOT_CFLAGS. The recipe check needs no compiler:

  python3 -B darwin-bootstrap-gc.py --recipe-only

The Mach-O check compiles libcody/buffer.cc from a GCC 16.2 source tree with
both default sets, without and with the recipe parameters. It uses the same
selected inputs as darwin-build-config.py:

  SDK_PYTHON -B darwin-bootstrap-gc.py --sdk-source SDK_SOURCE \\
      --descriptor JSON --descriptor-sha256 SHA256 \\
      --producer-receipt JSON --producer-receipt-sha256 SHA256 \\
      --tools-bin SDK_BIN --gcc-source SRC --work NEW_WORK
"""

import argparse
import importlib.util
import os
from pathlib import Path
import shlex
import struct
import sys

sys.dont_write_bytecode = True
TESTS = Path(__file__).resolve().parent
PROFILE = TESTS.parent
RECIPE = PROFILE / 'patches/gcc-darwin-host.patch'
# GCC's own defaults: checking builds use 30/4096. Release builds derive the
# values from RAM; 100/131072 is their upper bound.
STAGE_DEFAULTS = (('stage1-checking', '30', '4096'), ('release', '100', '131072'))
SOURCE = 'libcody/buffer.cc'
# The libcody configure result that matters to buffer.cc.
CONFIG_H = '#define NMS_CHECKING 0\n'


def load_build_config():
    spec = importlib.util.spec_from_file_location('darwin_build_config', TESTS / 'darwin-build-config.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recipe_boot_cflags():
    """Return the BOOT_CFLAGS words the Darwin recipe passes to make."""
    values = {}
    for line in RECIPE.read_text().splitlines():
        if line.startswith('+GCC16_DARWIN_BOOT_CFLAGS='):
            values['flags'] = line.split('=', 1)[1].split()
        if line.startswith('+MAKE_FLAGS+=') and 'BOOT_CFLAGS=' in line:
            values['make'] = line.split('+=', 1)[1].strip()
    assert values.get('make') == 'BOOT_CFLAGS=${GCC16_DARWIN_BOOT_CFLAGS:Q}', \
        'the recipe does not pass BOOT_CFLAGS to the bootstrap: %r' % values.get('make')
    flags = values.get('flags', [])
    assert flags[:2] == ['-g', '-O2'], 'BOOT_CFLAGS must keep the GCC default -g -O2: %r' % flags
    params = dict(flags[i + 1].split('=', 1) for i, w in enumerate(flags) if w == '--param')
    assert set(params) == {'ggc-min-expand', 'ggc-min-heapsize'}, params
    assert all(v.isdigit() for v in params.values()), params
    return flags[2:]


def mach_o_sections(path):
    """Map (segment, section) to bytes for a 64-bit Mach-O object."""
    data = path.read_bytes()
    magic, _, _, _, ncmds, _, _, _ = struct.unpack_from('<8I', data)
    assert magic == 0xfeedfacf, 'not a 64-bit Mach-O object'
    offset, table = 32, {}
    for _ in range(ncmds):
        cmd, size = struct.unpack_from('<2I', data, offset)
        if cmd == 0x19:
            nsects = struct.unpack_from('<I', data, offset + 64)[0]
            for i in range(nsects):
                base = offset + 72 + 80 * i
                sect, seg = (data[base + o:base + o + 16].rstrip(b'\0').decode() for o in (0, 16))
                length, start = struct.unpack_from('<QI', data, base + 40)
                table[(seg, sect)] = data[start:start + length] if start else b''
        offset += size
    return table


def experiment(cxx, env, gcc_source, work, recipe_params, run):
    """Compile one bootstrap source with both default sets; return objects."""
    (work / 'config.h').write_text(CONFIG_H)
    # Recording switches would make the object differ by command line only.
    base = cxx + ['-g', '-O2', '-gno-record-gcc-switches', '-fno-exceptions', '-fno-rtti',
                  '-include', 'config.h', '-I' + str(gcc_source / 'libcody'), '-c',
                  str(gcc_source / SOURCE)]
    objects = {}
    for label, params in (('unpinned', []), ('recipe', recipe_params)):
        for stage, expand, heap in STAGE_DEFAULTS:
            out = work / ('%s-%s.o' % (label, stage))
            run(base + ['--param', 'ggc-min-expand=' + expand, '--param', 'ggc-min-heapsize=' + heap]
                + params + ['-o', str(out)], work, env)
            objects[label, stage] = out
    return objects


def check(objects):
    stages = [stage for stage, _, _ in STAGE_DEFAULTS]
    a, b = (mach_o_sections(objects['unpinned', s]) for s in stages)
    assert set(a) == set(b), (sorted(a), sorted(b))
    changed = sorted(k for k in a if a[k] != b[k])
    print('sections that differ without the recipe parameters:', changed)
    assert changed, 'the GC defaults no longer change the objects; revisit BOOT_CFLAGS'
    assert all(seg == '__DWARF' for seg, _ in changed), 'code differs, not only debug information'
    pinned = [objects['recipe', s].read_bytes() for s in stages]
    assert pinned[0] == pinned[1], 'objects still differ with the recipe BOOT_CFLAGS parameters'
    print('PASS: identical objects with the recipe BOOT_CFLAGS parameters')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['--recipe-only']:
        print('recipe BOOT_CFLAGS parameters:', recipe_boot_cflags())
        return
    build_config = load_build_config()
    sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
    import sdk_source
    arguments = sdk_source.arguments(argv)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('gcc-source', 'tools-bin', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('descriptor', 'descriptor-sha256', 'producer-receipt', 'producer-receipt-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(arguments)
    params = recipe_boot_cflags()
    selected, env = build_config.selected_inputs(args)
    for path in (args.gcc_source, args.work):
        assert path.is_absolute(), path
    assert os.uname().sysname == 'Darwin', 'needs real Mach-O objects'
    args.work.mkdir()
    cxx = [selected.tool('cxx'), *selected.abi_flags['cppflags'], *selected.abi_flags['cxxflags']]
    print('compiler:', shlex.join(cxx))
    check(experiment(cxx, env, args.gcc_source, args.work, params, build_config.run))


if __name__ == '__main__':
    main()
