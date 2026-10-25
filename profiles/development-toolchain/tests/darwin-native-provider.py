#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Finite provider source controls. Do not execute make, CMake or a compiler."""

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
import re
import unittest

PROFILE = Path(__file__).resolve().parents[1]
ROOT = PROFILE.parents[1]
GCC_SOURCE = None
RECIPE_COMPOSITION_WORK = None
sys.dont_write_bytecode = True


def check_recipe(text):
    for line in ('+DEPENDS+= lld>=23.1.4:../../devel/lld',
                 '+CC= ${EMBERBSD_GCC16_SEED_CC}', '+CXX= ${EMBERBSD_GCC16_SEED_CXX}',
                 '+CPP= ${EMBERBSD_GCC16_SEED_CPP}'):
        assert line + '\n' in text, line
    for name, tool in [('as', 'llvm-mc'), ('ld', 'ld64.lld'), ('dsymutil', 'dsymutil')]:
        assert '+CONFIGURE_ARGS+= --with-' + name + '=${LOCALBASE:Q}/bin/' + tool + '\n' in text
        key = {'as': 'AS', 'ld': 'LD', 'dsymutil': 'DSYMUTIL'}[name]
        assert '+CONFIGURE_ENV+= ' + key + '_FOR_TARGET=${LOCALBASE:Q}/bin/' + tool + '\n' in text
    # libgcc creates libgcc_s with LIPO_FOR_TARGET; the default bare lipo is not a Ports tool.
    assert '+CONFIGURE_ENV+= LIPO_FOR_TARGET=${LOCALBASE:Q}/bin/llvm-lipo\n' in text
    # libstdc++ scripts/make_exports.pl runs a bare "c++filt -_" on Darwin.
    assert '+TOOLS_CREATE+= c++filt\n+TOOLS_PATH.c++filt= ${LOCALBASE}/bin/llvm-cxxfilt\n' in text
    # ld64.lld does not implement -r, which libtool's master-object route needs.
    assert '+MAKE_ENV+= lt_cv_apple_cc_single_mod=yes\n' in text
    assert '+CONFIGURE_ARGS+= --with-darwin-assembler=llvm-mc\n' in text
    # Selected LLVM strip keeps Mach-O section addresses; bootstrap-debug cannot pass.
    assert '+CONFIGURE_ARGS+= --without-build-config\n' in text
    assert '--with-build-config' not in ''.join(line for line in text.split('\n') if line.startswith('+'))
    # Stage 1 has checking GC defaults; GC timing changes stage 2/3 DWARF.
    assert '+GCC16_DARWIN_BOOT_CFLAGS= -g -O2 --param ggc-min-expand=100 --param ggc-min-heapsize=131072\n' in text
    assert '+MAKE_FLAGS+= BOOT_CFLAGS=${GCC16_DARWIN_BOOT_CFLAGS:Q}\n' in text
    # pkg_add must prefer gcc16-libs for the {gcc16,gcc16-libs} dependency.
    revisions = {}
    for section in text.split('\n--- a/')[1:]:
        name = section.split('\n', 1)[0]
        for line in section.split('\n'):
            if line.startswith('+PKGREVISION=\t'):
                revisions[name] = int(line.split('\t', 1)[1])
    assert revisions['lang/gcc16-libs/Makefile'] > revisions['lang/gcc16/Makefile'], revisions
    # libSystem has the stack protector; libssp would tie every user to GCC16.
    assert '+.elif ${OPSYS} == "Darwin"\n' in text
    assert '+CONFIGURE_ARGS+=\t--disable-libssp\n .else\n CONFIGURE_ARGS+=\t--enable-libssp\n' in text
    # Keep the selected strip through configure and every recursive build.
    assert '+CONFIGURE_ENV+= GCC_COMPARE_DEBUG_STRIP=${STRIP:Q}\n' in text
    assert '+MAKE_ENV+= GCC_COMPARE_DEBUG_STRIP=${STRIP:Q}\n' in text
    for environment in ('CONFIGURE_ENV', 'MAKE_ENV'):
        for name, tool in [('OBJDUMP', 'objdump'), ('OBJCOPY', 'objcopy')]:
            assert '+' + environment + '+= GCC_COMPARE_DEBUG_' + name + '=${LOCALBASE:Q}/bin/llvm-' + tool + '\n' in text
    assert '--enable-stage1-checking=release' not in text
    assert '+CONFIGURE_ARGS+= --with-darwin-sdk-version=${EMBERBSD_GCC16_DARWIN_SDK_VERSION:Q}\n' in text
    assert '.if ${OPSYS} == "Darwin"\n' in text
    assert '--disable-bootstrap' not in ''.join(line for line in text.split('\n') if line.startswith('+'))
    assert ('+.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} != "yes"\n'
            '+BUILDLINK_TRANSFORM+=\trm:-nodefaultrpaths\n+.endif\n') in text
    # The pkgsrc LINK_LIBGCC_SPEC passes a missing tooldir -L to every Darwin link.
    # Drop it in the same vars pass; a separate class can run before vars.
    libgcc = "+SUBST_SED.vars+= -e '/-DLINK_LIBGCC_SPEC=/d'\n"
    assert libgcc in text
    assert 'darwin-libgcc' not in text
    assert -1 < text.find(' BUILD_DEFS+=\t\tGCC_TARGET_MACHINE\n') < text.index(libgcc)


def check_cmake(fragment, patch):
    assert '.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} == "yes"\n' in fragment
    assert '_EMBERBSD_CMAKE_TOOL_PAIRS+= LIBTOOL EMBERBSD_DARWIN_LIBTOOL\n' in fragment
    assert '.for _ember_cmake_language in C CXX\n' in fragment
    assert '_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_${_ember_cmake_language}_LINKER_LAUNCHER:STRING=${EMBERBSD_DARWIN_CMAKE_LINKER_LAUNCHER:Q}\n' in fragment
    assert 'CMAKE_LIBTOOL' in patch and 'CMAKE_C_LINKER_LAUNCHER CMAKE_CXX_LINKER_LAUNCHER' in patch
    # Both source-file and project try_compile children receive these names.
    assert 'list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES' in patch
    assert 'CMAKE_TRY_COMPILE_NO_PLATFORM_VARIABLES' in patch


def check_specs(root):
    arm = (root / 'gcc/config/aarch64/darwin.h').read_text()
    driver = (root / 'gcc/gcc.cc').read_text()
    darwin = (root / 'gcc/config/darwin.h').read_text()
    collect = (root / 'gcc/collect2.cc').read_text()
    assert '#ifdef DARWIN_LLVM_MC\n#define ASM_SPEC' in arm
    for word in ('--filetype=obj', '--triple=arm64-apple-macosx%*', '--mcpu=apple-m1',
                 '%<asm_macosx_version_min=*', 'DARWIN_LLVM_MC_SELF_SPECS'):
        assert word in arm, word
    assert '-platform_version macos %*' in darwin and 'DARWIN_LLVM_SDK_VERSION' in darwin
    assert '#define LLD_NAME "ld64.lld"' in collect or '# define LLD_NAME "ld64.lld"' in collect
    for name, macro in [('as', 'ASSEMBLER'), ('ld', 'LINKER')]:
        expression = f'! strcmp (name, "{name}") && access (DEFAULT_{macro}, X_OK) == 0'
        assert expression in driver and f'return xstrdup (DEFAULT_{macro});' in driver
    assert 'case OPT_fuse_ld_lld:' not in driver  # No implicit print-prog-name suffix.
    assert 'ld_file_name == 0 && access (DEFAULT_LINKER, X_OK) == 0' in collect
    assert 'ld_file_name = DEFAULT_LINKER;' in collect
    assert 'DARWIN_PLATFORM_ID' in darwin[darwin.index('#define LINK_COMMAND_SPEC'):]
    options = (root / 'gcc/config/darwin.opt').read_text()
    check_runpaths(darwin, options)


def check_runpaths(darwin, options):
    assert 'nodefaultrpaths\nDriver RejectNegative\n' in options
    for name in ('DARWIN_RPATH_LINK', 'DARWIN_EXTRA_RPATH'):
        body = darwin.split('# define ' + name, 1)[1].split('#else', 1)[0]
        assert '%{!nodefaultrpaths:' in body, name
    assert '%<nodefaultrpaths' in darwin


def compose_recipe(work):
    """Apply the real GCC recipe series with the existing source-test adapter."""
    assert work.is_absolute() and not work.exists() and not work.is_symlink()
    assert not work.is_relative_to(ROOT) and not ROOT.is_relative_to(work)
    assert not os.environ.get('FAKE_ARCHIVE'), 'Use the actual pinned pkgsrc source'
    work.mkdir()
    adapter_path = ROOT / 'scripts/tests/export-fixture.py'
    spec = importlib.util.spec_from_file_location('ports_source_test_adapter', adapter_path)
    adapter = importlib.util.module_from_spec(spec)
    exec(compile(adapter_path.read_bytes(), str(adapter_path), 'exec'), adapter.__dict__)
    selection, run = adapter.TestSelection(), adapter.test_runner
    exporter = adapter.load_exporter(ROOT)
    recipes, series, _, _ = exporter.configuration(ROOT)
    selected = {'lang/gcc16', 'lang/gcc16-libs', 'lang/gcc16-libjit'}
    assert not selected & {name for name, source in recipes}, 'Review new GCC recipe overlays'
    rows = run([*selection.command('git'), '-C', str(ROOT), 'ls-files', '--stage', '--', 'upstream/pkgsrc']).splitlines()
    assert len(rows) == 1 and rows[0].startswith(b'160000 ')
    pin = rows[0].split()[1].decode('ascii')
    actual = run([*selection.command('git'), '-C', str(ROOT / 'upstream/pkgsrc'), 'rev-parse', 'HEAD'])
    assert actual.strip().decode('ascii') == pin, 'Initialize the exact pinned pkgsrc submodule'
    archive, tree = work / 'base.tar', work / 'recipe'
    run([*selection.command('git'), '-C', str(ROOT / 'upstream/pkgsrc'), 'archive', '--format=tar',
         '--output=' + str(archive), pin, *sorted(selected)])
    tree.mkdir()
    exporter.extract_archive(archive, tree)
    applied = []
    darwin = PROFILE / 'patches/gcc-darwin-host.patch'
    for method, path, recipe, name in series:
        assert method == 'patch', 'Review a new non-patch operation before the Darwin recipe'
        chunks = []
        for section in re.split(r'(?m)(?=^--- )', path.read_text()):
            if not section.startswith('--- '):
                continue
            lines = section.splitlines()
            assert len(lines) > 1 and lines[1].startswith('+++ '), str(path)
            names = [line.split()[1] for line in lines[:2] if line.split()[1] != '/dev/null']
            names = [name[2:] for name in names]
            hits = [name.split('/')[:2] for name in names]
            relevant = ['/'.join(parts) in selected for parts in hits]
            assert not any(relevant) or all(relevant), 'A patch moves a file outside the finite recipe set'
            if relevant and all(relevant):
                chunks.append(section)
        if chunks:
            delta = ''.join(chunks).encode()
            args = [*selection.command('patch'), '-f', '-E', '-d', str(tree), '-p1', '-F', '0', '-V', 'none']
            try:
                output = run(args, input=delta)
            except Exception as error:
                (work / 'patch-failure.stdout').write_bytes(getattr(error, 'stdout', b'') or b'')
                (work / 'patch-failure.stderr').write_bytes(getattr(error, 'stderr', b'') or b'')
                raise
            (work / (str(len(applied)).zfill(2) + '-' + path.stem + '.stdout')).write_bytes(output)
            assert b'fuzz' not in output.lower(), 'Source composition used fuzz'
            applied.append(str(path.relative_to(ROOT)))
        if path == darwin:
            break
    assert applied and applied[-1] == str(darwin.relative_to(ROOT))
    assert not list(tree.rglob('*.rej'))
    makefile = (tree / 'lang/gcc16/Makefile').read_text()
    common = (tree / 'lang/gcc16/Makefile.common').read_text()
    assert 'GCC16_TARGET_LDFLAGS=\t${LDFLAGS:M-Wl,-z*}\n' in makefile
    assert 'LDFLAGS_FOR_TARGET=${GCC16_TARGET_LDFLAGS:Q}' in makefile
    assert r'CFLAGS_FOR_TARGET=-g\ ' in makefile and r'CXXFLAGS_FOR_TARGET=-g\ ' in makefile
    assert 'MAKE_ENV+= lt_cv_apple_cc_single_mod=yes\n' in common
    (work / 'composition.json').write_text(json.dumps(dict(pkgsrc_revision=pin, patches=applied,
        recipes=sorted(selected), patch_options=['-f', '-E', '-p1', '-F', '0', '-V', 'none'],
        scope='Actual ordered GCC recipe source composition only; no compiler or provider qualification'),
        indent=2, sort_keys=True) + '\n')


class ProviderSourceTests(unittest.TestCase):
    def test_actual_ordered_recipe_composition(self):
        if RECIPE_COMPOSITION_WORK is None:
            self.skipTest('Pass --recipe-composition-work for real pinned source composition')
        compose_recipe(RECIPE_COMPOSITION_WORK)

    def test_gcc_final_tools_and_seed_compilers_are_separate(self):
        text = (PROFILE / 'patches/gcc-darwin-host.patch').read_text()
        check_recipe(text)
        for mutant in (text.replace('+DEPENDS+= lld>=23.1.4:../../devel/lld\n', ''),
                       text.replace('--with-ld=${LOCALBASE:Q}/bin/ld64.lld', '--with-ld=${EMBERBSD_GCC16_LD64_LLD:Q}'),
                       text.replace('+CXX= ${EMBERBSD_GCC16_SEED_CXX}', '+CXX= /usr/bin/clang++'),
                       text.replace('+.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} != "yes"',
                                    '+.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} == "yes"'),
                       text.replace('+BUILDLINK_TRANSFORM+=\trm:-nodefaultrpaths\n', ''),
                       text.replace('+MAKE_ENV+= GCC_COMPARE_DEBUG_STRIP=${STRIP:Q}\n', ''),
                       text.replace('+CONFIGURE_ENV+= GCC_COMPARE_DEBUG_STRIP=${STRIP:Q}\n', ''),
                       text + '+CONFIGURE_ARGS+= --enable-stage1-checking=release\n',
                       text.replace('+MAKE_FLAGS+= BOOT_CFLAGS=${GCC16_DARWIN_BOOT_CFLAGS:Q}\n', ''),
                       text.replace('+CONFIGURE_ARGS+=\t--disable-libssp\n', ''),
                       text.replace("+SUBST_SED.vars+= -e '/-DLINK_LIBGCC_SPEC=/d'\n", ''),
                       text.replace('+SUBST_SED.vars+=', '+SUBST_CLASSES+= darwin-libgcc\n+SUBST_SED.darwin-libgcc+='),
                       text.replace("-e '/-DLINK_LIBGCC_SPEC=/d'", "-e '/-DLINK_LIBGCC_SPEC=/p'"),
                       text.replace(' BUILD_DEFS+=\t\tGCC_TARGET_MACHINE\n', ' BUILD_DEFS+=\t\tGCC_TARGET_MACHINE_X\n')):
            with self.assertRaises(AssertionError):
                check_recipe(mutant)

    def test_cmake_try_compile_keeps_archive_and_shared_launcher(self):
        fragment = (ROOT / 'profiles/common-build-tools/cmake-binutils.mk').read_text()
        patch = (ROOT / 'profiles/common-build-tools/patches/cmake-darwin-tapi-kind.patch').read_text()
        check_cmake(fragment, patch)
        for first, second in ((fragment.replace('_EMBERBSD_CMAKE_TOOL_PAIRS+= LIBTOOL EMBERBSD_DARWIN_LIBTOOL\n', ''), patch),
                              (fragment, patch.replace('CMAKE_C_LINKER_LAUNCHER CMAKE_CXX_LINKER_LAUNCHER', ''))):
            with self.assertRaises(AssertionError):
                check_cmake(first, second)
        forwarding = (ROOT / 'profiles/common-build-tools/patches/pkgsrc-cmake-binutils.patch').read_text()
        self.assertIn('+CONFIGURE_ARGS+= -- ${_EMBERBSD_CMAKE_BINUTILS_ARGS}', forwarding)

    def test_changed_patch_hunks_have_exact_counts(self):
        paths = [PROFILE / 'patches/gcc-darwin-host.patch',
                 PROFILE / 'patches/gcc-darwin-compare-debug.patch',
                 ROOT / 'profiles/common-build-tools/patches/cmake-darwin-tapi-kind.patch']
        for path in paths:
            lines = path.read_text().split('\n')
            found = 0
            for i, line in enumerate(lines):
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if not match:
                    continue
                old = new = 0
                for body in lines[i + 1:]:
                    if body.startswith(('@@ ', '--- ')) or not body:
                        break
                    if body[0] in ' -':
                        old += 1
                    if body[0] in ' +':
                        new += 1
                self.assertEqual((old, new), (int(match[2] or 1), int(match[4] or 1)), str(path))
                found += 1
            self.assertGreater(found, 0)

    def test_runtime_policy_is_link_only_in_the_native_producer_profile(self):
        text = (PROFILE / 'darwin-bootstrap.mk.conf').read_text()
        self.assertIn('LDFLAGS+= -static-libstdc++ -static-libgcc -nodefaultrpaths\n', text)
        for name in ('CC', 'CXX', 'CPP'):
            self.assertIn(name + '= ${EMBERBSD_GCC16_SEED_' + name + '}\n', text)
        self.assertNotRegex(text, r'(?:CFLAGS|CXXFLAGS)\s*[+:?]?=.*-static-lib')
        self.assertIn('Parallel CMake bootstrap requires the accepted SDK link launcher list', text)

    def test_default_runpath_guards_are_required(self):
        options = 'nodefaultrpaths\nDriver RejectNegative\n'
        specs = ('# define DARWIN_RPATH_LINK "%{!nodefaultrpaths:paths}"\n#else\n'
                 '# define DARWIN_EXTRA_RPATH "%{!nodefaultrpaths:extra}"\n#else\n'
                 'spec "%<nodefaultrpaths"\n')
        check_runpaths(specs, options)
        for mutated, declaration in ((specs.replace('%{!nodefaultrpaths:', '%{rpaths:', 1), options),
                                     (specs.replace('%<nodefaultrpaths', ''), options),
                                     (specs, options.replace('Driver RejectNegative', 'Target'))):
            with self.assertRaises(AssertionError):
                check_runpaths(mutated, declaration)

    def test_actual_configured_driver_specs_need_no_external_override(self):
        if GCC_SOURCE is None:
            self.skipTest('Pass --gcc-source for exact patched-source inspection')
        check_specs(GCC_SOURCE)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gcc-source', type=Path)
    parser.add_argument('--recipe-composition-work', type=Path,
                        help='new absolute source-test directory; requires EXPORT_TEST_GIT and EXPORT_TEST_PATCH')
    args, extra = parser.parse_known_args()
    GCC_SOURCE = args.gcc_source
    RECIPE_COMPOSITION_WORK = args.recipe_composition_work
    unittest.main(argv=[__file__, *extra])
