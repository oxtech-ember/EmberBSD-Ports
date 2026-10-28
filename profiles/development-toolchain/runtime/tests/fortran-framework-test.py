#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; actual BSD make fragments, no package framework bootstrap.
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
sys.dont_write_bytecode = True

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True, type=Path)
parser.add_argument('--bmake', required=True, type=Path)
parser.add_argument('--pkg-admin', required=True, type=Path)
parser.add_argument('--pkgsrc-source', required=True, type=Path)
parser.add_argument('new_result', type=Path)
a = parser.parse_args()
root = Path(__file__).resolve().parents[4]
# The selected SDK is explicit. No installed Python package is discovered.
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk import API_VERSION, inventory, jsonio, paths
from emberbsd_sdk.process import sanitized_environment
from emberbsd_sdk.stream import capture_streamed
from emberbsd_sdk.errors import CommandError, SDKError
if type(API_VERSION) is not int or API_VERSION != 1: raise SDKError('SDK API1 required')
if paths.entry(a.new_result) is not None: raise SDKError('Result already exists')
a.new_result.mkdir()
result = Path(paths.canonical_existing(a.new_result))
source = a.pkgsrc_source
for name in ('mk/bsd.pkg.use.mk', 'mk/compiler.mk'):
    output = result / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((source / name).read_bytes())
patch = root / 'profiles/common-build-tools/patches/pkgsrc-cross-fortran.patch'
commands = []

def run(argv, cwd=result, env=None, input=None, status=0):
    environment = sanitized_environment()
    environment.update(env or {})
    try:
        value = capture_streamed(list(map(str, argv)), cwd=cwd, env=environment, input=input,
                                 stdout_limit=1024*1024, stderr_limit=1024*1024, timeout=30)
        if value.stderr_truncated: raise SDKError('Truncated metadata stderr')
        stdout, stderr, code = value.value, value.stderr, 0
    except CommandError as error:
        if error.stdout_truncated or error.stderr_truncated: raise SDKError('Truncated matcher output')
        stdout, stderr, code = error.stdout, error.stderr, error.returncode
    if code != status: raise SDKError('Unexpected command status: ' + str(code))
    commands.append({'argv': list(map(str, argv)), 'status': code,
                     'stdout': stdout.decode(), 'stderr': stderr.decode(),
                     'selected_environment':env or {}, 'input':input.decode() if input is not None else None})
    return stdout.decode()

run(['/usr/bin/patch', '-f', '-F', '0', '-p1', '-i', patch])
patched = (result / 'mk/bsd.pkg.use.mk').read_text()
start = patched.index('.if defined(USE_LANGUAGES) && !empty(USE_LANGUAGES:Mfortran)')
end = patched.index('# PKGSRC_USE_MKTOOLS.', start)
fragment = patched[start:end]
old = (source / 'mk/bsd.pkg.use.mk').read_text()
old = old[old.index('.if defined(USE_LANGUAGES) && !empty(USE_LANGUAGES:Mfortran)'):]
old = old[:old.index('# PKGSRC_USE_MKTOOLS.')]
records = []

# pkg_match treats a literal package name as an exact version pin. A single
# equals sign is not a Dewey operator and cannot match the installed name.
role_pins = (
    ('gcc16-runtime', '16.2.0nb7', '16.2.0nb6', '16.2.0nb8'),
    ('gcc16-fortran-runtime', '16.2.0nb1', '16.2.0', '16.2.0nb2'),
    ('gcc16-fortran-devel', '16.2.0nb1', '16.2.0', '16.2.0nb2'),
)
pin_sources = (
    ('pkgsrc/lang/gcc16-fortran-runtime/Makefile',
     ('gcc16-runtime-16.2.0nb7:', 'gcc16-fortran-runtime-16.2.0nb1:')),
    ('pkgsrc/lang/gcc16-fortran-runtime/buildlink3.mk',
     ('gcc16-fortran-runtime-16.2.0nb1',)),
    ('pkgsrc/lang/gcc16-fortran-devel/buildlink3.mk',
     ('gcc16-fortran-devel-16.2.0nb1',)),
    ('profiles/common-build-tools/cross/fortran.mk',
     ('gcc16-fortran-runtime-16.2.0nb1:', 'gcc16-fortran-devel-16.2.0nb1:')),
)
for relative, pins in pin_sources:
    text = (root / relative).read_text()
    for pin in pins:
        if pin not in text: raise SDKError('Missing exact package pin in ' + relative)
    if re.search(r'gcc16(?:-fortran)?-(?:runtime|devel)=[0-9]', text):
        raise SDKError('Invalid equals package pattern in ' + relative)
for name, version, older, newer in role_pins:
    pin = name + '-' + version
    old_pin = name + '=' + version
    candidates = (pin, name+'-'+older, name+'-'+newer,
                  name+'-16.2.1', 'other-'+version)
    for package in candidates:
        old_output = run([a.pkg_admin, 'pmatch', old_pin, package], status=1)
        code = 0 if package == pin else 1
        output = run([a.pkg_admin, 'pmatch', pin, package], status=code)
        if old_output or output: raise SDKError('Package matcher emitted unexpected stdout')
        records.append({'real_pkg_match':{'old_pattern':old_pin,'pattern':pin,
                        'package':package,'old_status':1,'status':code},
                        'package_database_accessed':False})

def make(text, fields):
    path = result / 'fixture.mk'
    path.write_text(text)
    return run([a.bmake, '-r', '-f', path] + [v for field in fields for v in ('-v',field)]).splitlines()

for cross in ('yes', 'no'):
    for target in ('NetBSD-11.0-x86_64','NetBSD-11.0-aarch64'):
        for lang in ('c','c fortran','c fortran77'):
            prefix = f'USE_LANGUAGES={lang}\nUSE_CROSS_COMPILE={cross}\nUSE_LIBTOOL=yes\nTOOLBASE=/native\nMACHINE_PLATFORM={target}\nLIBTOOL_REQD=2.6.2\n'
            fields=['PKG_LIBTOOL','PKG_SHLIBTOOL','TOOL_DEPENDS','PKG_FAIL_REASON']
            after = make(prefix + fragment, fields)
            before = make(prefix + old, fields)
            fortran = 'fortran' in lang
            if not fortran or cross == 'no':
                if after != before: raise SDKError('Native/non-Fortran policy changed')
            else:
                if after[0] != '/native/cross-' + target + '/bin/libtool-fortran': raise SDKError('Wrong target dispatcher')
                if 'cross-libtool-fortran-' + target + '>=' not in after[2]: raise SDKError('No real Fortran provider dependency')
                if not before[3] or after[3]: raise SDKError('NYI control did not detect the implemented routing change')
            records.append({'cross':cross,'target':target,'languages':lang,'before':before,'after':after})

compiler = (result / 'mk/compiler.mk').read_text()
start = compiler.index('.if !empty(TOOLS_USE_CROSS_COMPILE:M[yY][eE][sS])', compiler.index('# Add sysroot'))
end = compiler.index('.endif',start)+len('.endif')
for cross in ('yes','no'):
    output = make(f'TOOLS_USE_CROSS_COMPILE={cross}\nTOOLS_CROSS_DESTDIR=/target/sysroot\n'+compiler[start:end],
                  ['CWRAPPERS_PREPEND.cc','CWRAPPERS_PREPEND.cxx','CWRAPPERS_PREPEND.ld','CWRAPPERS_PREPEND.f77'])
    expected = '--sysroot=/target/sysroot' if cross == 'yes' else ''
    if output != [expected]*4: raise SDKError('Actual sysroot wrapper routing mismatch')
    records.append({'sysroot_cross':cross,'actual':output})

# A normal native GCC prefix can select the versioned native gfortran via
# the existing GCC_VERSION_SUFFIX contract. These are path fixtures only.
gcc = (source / 'mk/compiler/gcc.mk').read_text()
start = gcc.index('.if exists(${_GCCBINDIR}/${_GCC_BIN_PREFIX}gfortran${GCC_VERSION_SUFFIX})')
end = gcc.index('.endif',start)+len('.endif')
(native := result / 'native16/bin').mkdir(parents=True)
(native / 'gfortran-16').write_text('source-only fixture; never executed')
output = make(f'_GCCBINDIR={native}\n_GCC_DIR=/work/.gcc\n_GCC_BIN_PREFIX=\nGCC_VERSION_SUFFIX=-16\n'+gcc[start:end], ['FCPATH','F77PATH','PKG_FC'])
if output != [str(native/'gfortran-16')]*2+['/work/.gcc/bin/gfortran-16']: raise SDKError('Native GCC16 suffix provider route failed')
records.append({'native_suffix_fixture':output,'compiler_executed':False})
# The common policy is read from mk.conf before FFTW's options.mk appends
# fortran77. Compare that old early evaluation with the actual new late hook.
policy = root / 'profiles/common-build-tools/cross/fortran.mk'
hook_start = compiler.index('# Optional compiler policy runs after package options')
hook_end = compiler.index('_COMPILER_STRIP_VARS=',hook_start)
hook = compiler[hook_start:hook_end]
fields = ['FC','DEPENDS','BUILD_DEPENDS','CWRAPPERS_APPEND.f77','PKG_FAIL_REASON']
# The GCC profile selects GCC16 gfortran. The default Clang profile selects
# Flang and must never fall back to GCC16 or its Fortran packages.
for family in ('gcc', 'clang'):
  for target, triplet in (('amd64','x86_64--netbsd'),('aarch64','aarch64--netbsd')):
    for lang, cross, tools_cross in (('fortran77','yes','yes'),('fortran','yes','yes'),
                                     ('c','yes','yes'),('fortran','no','no'),
                                     ('fortran','no','yes')):
        prefix = (f'USE_LANGUAGES=c\nUSE_CROSS_COMPILE={cross}\nTOOLS_USE_CROSS_COMPILE={tools_cross}\n'
                  f'EMBERBSD_CROSS_COMPILER_FAMILY={family}\nPKGSRC_COMPILER={family}\n'
                  f'EMBERBSD_CROSS_TARGET={target}\n_EMBER_CROSS_TRIPLET={triplet}\n'
                  'TOOLDIR=/fixture-missing-compiler\nCROSS_DESTDIR=/fixture-missing-sysroot\n')
        late = 'USE_LANGUAGES+=' + lang + '\n'
        before = make(prefix + f'.include "{policy}"\n' + late, fields)
        after = make(prefix + late + f'PKGSRC_COMPILER_PRE_CONFIG_MK={policy}\n' + hook, fields)
        active = lang != 'c' and tools_cross == 'yes'
        if active and family == 'clang':
            if before != ['']*5: raise SDKError('Early-policy causal witness unexpectedly saw a late language')
            if 'gcc' in ' '.join(after[:4]): raise SDKError('Clang profile selected a GCC Fortran provider')
            if 'EMBERBSD_FLANG' not in after[4]: raise SDKError('Clang late missing-Flang guard did not run')
        elif active:
            if before != ['']*5: raise SDKError('Early-policy causal witness unexpectedly saw a late language')
            if after[0] != '/fixture-missing-compiler/bin/'+triplet+'-gfortran': raise SDKError('Late hook did not select FC')
            if 'Fortran frontend' not in after[4] or 'SDK roles' not in after[4]: raise SDKError('Late missing-input guards did not run')
            if cross == 'yes':
                if 'gcc16-fortran-runtime-16.2.0nb1:' not in after[1] or 'gcc16-fortran-devel-16.2.0nb1:' not in after[2]: raise SDKError('Late target package dependencies absent')
            elif after[1] or after[2]: raise SDKError('Fake-cross host package acquired target DB dependencies')
        elif after != before or any(after): raise SDKError('Native/non-Fortran metadata changed')
        records.append({'family':family,'late_language':lang,'target':target,'cross':cross,'tools_cross':tools_cross,
                        'before_early_policy':before,'after_real_late_hook':after})

# The normal pkgsrc PLIST expander would re-add the separate runtime DSOs
# from a development .la. Exercise that exact source script before/after.
prefix = result / 'plist-prefix'
lib = prefix / 'gcc16/lib'
lib.mkdir(parents=True)
(lib / 'libgfortran.la').write_text("# libgfortran.la - a libtool library file\n"
    "library_names='libgfortran.so.5.0 libgfortran.so.5 libgfortran.so'\n"
    "old_library='libgfortran.a'\ninstalled=yes\n")
for name in ('libgfortran.so.5.0','libgfortran.so.5','libgfortran.so','libgfortran.a'):
    (lib / name).write_bytes(b'source-only PLIST fixture')
plist = b'gcc16/lib/libgfortran.la\ngcc16/lib/libgfortran.a\ngcc16/lib/libgfortran.so\n'
recipe = (root / 'pkgsrc/lang/gcc16-fortran-runtime/Makefile').read_text()
selected = re.findall(r'^LIBTOOLIZE_PLIST=\s*(\w+)\s*$', recipe,re.M)
if selected != ['no']: raise SDKError('The exact role recipe must retain its verified inventory')
outputs = {}
for expand in ('yes',selected[0]):
    env = {'LIBTOOLIZE_PLIST':expand, 'PREFIX':str(prefix), 'SHLIB_TYPE':'ELF',
           'LIBTOOL_EXPAND':'/bin/sh '+str(source/'mk/plist/libtool-expand')}
    argv = ['/usr/bin/awk','-f',source/'mk/plist/plist-functions.awk',
            '-f',source/'mk/plist/plist-libtool.awk','-f',source/'mk/plist/plist-default.awk']
    outputs[expand] = run(argv,env=env,input=plist).splitlines()
if set(outputs['no']) != set(plist.decode().splitlines()): raise SDKError('The verified role inventory changed')
if not {'gcc16/lib/libgfortran.so.5','gcc16/lib/libgfortran.so.5.0'} <= set(outputs['yes'])-set(outputs['no']):
    raise SDKError('The default-expansion cross-role witness did not reproduce')
records.append({'real_pkgsrc_PLIST_expansion':outputs, 'producer_or_ELF_executed':False})

jsonio.write_json(result/'commands.json',commands,exclusive=True)
jsonio.write_json(result/'result.json',{'status':'PASS','cases':records,
 'patch_sha256':inventory.sha256_file(patch), 'commands_sha256':inventory.sha256_file(result/'commands.json'),
 'scope':'Actual patch F0 and BSD make fragment evaluation; path fixtures only. No compiler, normal pkgsrc metadata, SDK/prefix/package DB or runtime acceptance.'},exclusive=True)
print(json.dumps({'status':'PASS','cases':len(records),'result':str(result/'result.json')}))
