#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Port of the native routing regression.
"""Exercise host-prefix native generators in the actual cross wrapper PATH."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys

sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
from sdk_source import install_signal_handlers

install_signal_handlers()
sdk, args = load_sdk()
from emberbsd_sdk.errors import CommandError, SDKError
from emberbsd_sdk.stream import PRODUCER_STREAM_API, capture_streamed

if type(PRODUCER_STREAM_API) is not int or PRODUCER_STREAM_API != 1:
    raise SDKError('SDK producer stream API 1 is required')
if len(args) != 5:
    raise SystemExit('Use PKGSRC CROSS_MAKECONF LIBX11_WORK FREETYPE_SOURCE NEW_WORK; set absolute BMAKE')
tree, conf, xwork, freetype = (Path(p).resolve(strict=True) for p in args[:4])
work = Path(args[4])
if not work.is_absolute():
    raise SystemExit('Use an absolute new work directory')
make = Path(os.environ['BMAKE'])
if not make.is_absolute():
    raise SystemExit('BMAKE must name the selected absolute SDK bmake')
work.mkdir()
profiles = Path(__file__).resolve().parents[2]
export = work / 'pkgsrc'
export.mkdir()
# Copy only the recipes under test. Other framework and source inputs stay read-only.
for path in tree.iterdir():
    (export / path.name).symlink_to(path)
for category, recipe in (('graphics', 'freetype2'), ('x11', 'libXt')):
    (export / category).unlink()
    (export / category).mkdir()
    for path in (tree / category).iterdir():
        if path.name != recipe:
            (export / category / path.name).symlink_to(path)
    shutil.copytree(profiles.parent / 'pkgsrc' / category / recipe,
                    export / category / recipe)
text = conf.read_text()
for name, source in (
        ('EMBERBSD-CROSS-MK.CONF', profiles / 'common-build-tools/cross/mk.conf'),
        ('EMBERBSD-COMMON-GRAPHICS-MK.CONF', profiles / 'common-graphics/mk.conf')):
    pattern = r'^\.include "[^"\n]*/' + re.escape(name) + '"$'
    assert len(re.findall(pattern, text, re.M)) == 1, name
    (export / name).unlink()
    shutil.copyfile(source, export / name)
    text = re.sub(pattern, '.include "' + str(export / name) + '"', text, flags=re.M)
# The new profile must verify through the matching adapter in its directory.
(export / 'prepare-native-tools.py').unlink(missing_ok=True)
shutil.copyfile(profiles / 'common-build-tools/cross/prepare-native-tools.py',
                export / 'prepare-native-tools.py')
(export / 'EMBERBSD-NATIVE-TOOLS.MK').unlink(missing_ok=True)
shutil.copyfile(profiles / 'common-build-tools/cross/native-tools.mk',
                export / 'EMBERBSD-NATIVE-TOOLS.MK')
text += '\nWRKOBJDIR=' + str(work / 'objects') + '\nPACKAGES=' + str(work / 'packages') + '\n'
(work / 'mk.conf').write_text(text)


def run(name, argv, env=None, cwd=work):
    try:
        result = capture_streamed(argv, env={**os.environ, **(env or {})}, cwd=str(cwd),
                                  timeout=300, stdout_limit=8 * 1024 * 1024)
        code, output, errors = 0, result.value, result.stderr
        if result.stderr_truncated:
            raise SDKError('Producer stderr exceeded the capture limit')
    except CommandError as error:
        code, output, errors = error.returncode, error.stdout, error.stderr
        if error.stderr_truncated or error.stdout_truncated:
            raise SDKError('Producer failure output exceeded the capture limit') from error
    (work / (name + '.stdout')).write_bytes(output)
    (work / (name + '.stderr')).write_bytes(errors)
    (work / (name + '.json')).write_text(json.dumps(
        {'argv': argv, 'exit': code, 'cwd': str(cwd), 'env': env or {}},
        indent=2) + '\n')
    assert code == 0, name + ': ' + errors.decode('utf-8', 'replace')
    return output.decode()


def query(name, package, variables, *overrides):
    argv = [str(make), '-C', str(export / package), 'MAKECONF=' + str(work / 'mk.conf'), *overrides]
    for variable in variables:
        argv += ['-V', '${' + variable + '}']
    values = run(name, argv).splitlines()
    assert len(values) == len(variables), values
    return dict(zip(variables, values))


names = ['PKG_FAIL_REASON', 'NATIVE_OPSYS', 'EMBERBSD_CROSS_BUILD_CC',
         'EMBERBSD_CROSS_BUILD_CXX', 'NATIVE_CC', 'NATIVE_CXX', 'CONFIGURE_ENV',
         'CC', 'CXX', 'CROSS_DESTDIR', 'TOOLDIR', 'NATIVE_CPPFLAGS',
         'NATIVE_CFLAGS', 'NATIVE_CXXFLAGS', 'NATIVE_LDFLAGS',
         'EMBERBSD_NATIVE_BMAKE', 'EMBERBSD_CROSS_BUILD_PYTHON', 'CONFIG_SHELL']
data = query('libX11-metadata', 'x11/libX11', names)
assert not data['PKG_FAIL_REASON'], data['PKG_FAIL_REASON']
assert data['NATIVE_OPSYS'] == 'Darwin', 'This subprocess-routing regression requires Darwin'
assert Path(data['EMBERBSD_NATIVE_BMAKE']).resolve(strict=True) == make.resolve(strict=True)
assert Path(data['EMBERBSD_CROSS_BUILD_PYTHON']).resolve(strict=True) == Path(sys.executable).resolve(strict=True)
for language, flags in (('CC', 'CFLAGS'), ('CXX', 'CXXFLAGS')):
    expected = [data['EMBERBSD_CROSS_BUILD_' + language]]
    expected += shlex.split(data['NATIVE_CPPFLAGS'])
    expected += shlex.split(data['NATIVE_' + flags])
    expected += shlex.split(data['NATIVE_LDFLAGS'])
    assert shlex.split(data['NATIVE_' + language]) == expected
    assignments = [value for value in shlex.split(data['CONFIGURE_ENV'])
                   if value.startswith(language + '_FOR_BUILD=')]
    assert assignments and all(shlex.split(value.split('=', 1)[1]) == expected for value in assignments)
# Use actual cwrapper executables and configuration. Redirect every write.
binary_dir = work / 'bin'
config = work / 'wrapper-config'
binary_dir.mkdir()
config.mkdir()
for path in (xwork / '.cwrapper/bin').iterdir():
    (binary_dir / path.name).symlink_to(path.resolve(strict=True))
for path in (xwork / '.cwrapper/config').iterdir():
    value = re.sub(r'^worklog=.*$', 'worklog=' + str(work / 'wrapper.log'), path.read_text(), flags=re.M)
    value = re.sub(r'^wrksrc=.*$', 'wrksrc=' + str(work), value, flags=re.M)
    value = value.replace(str(xwork / '.cwrapper/bin'), str(binary_dir))
    (config / path.name).write_text(value)
recorded_path = re.search(r'^path=(.*)$', (xwork / '.cwrapper/config/ld').read_text(), re.M)
assert recorded_path, 'Missing actual wrapper PATH'
env = {'PATH': str(binary_dir) + ':' + recorded_path[1], 'CWRAPPERS_CONFIG_DIR': str(config)}
(work / 'native.c').write_text('#include <stdio.h>\nint main(void) { puts("native C"); return 0; }\n')
(work / 'native.cc').write_text('#include <iostream>\nint main() { std::cout << "native C++\\n"; }\n')
provider_hashes = {data[key]: hashlib.sha256(Path(data[key]).read_bytes()).hexdigest()
                   for key in ('EMBERBSD_CROSS_BUILD_CC', 'EMBERBSD_CROSS_BUILD_CXX')}
for language, suffix, message in (('CC', '.c', 'native C\n'), ('CXX', '.cc', 'native C++\n')):
    binary = work / ('native-' + language)
    run('link-' + language, [*shlex.split(data['NATIVE_' + language]),
                            str(work / ('native' + suffix)), '-o', str(binary)], env)
    assert run('execute-' + language, [str(binary)]) == message
assert not (work / 'wrapper.log').exists() or not (work / 'wrapper.log').read_bytes()
# Compile the unchanged upstream generator. Consume its actual keysym headers.
makekeys = xwork / 'libX11-1.8.13/src/util/makekeys.c'
run('makekeys-link', [*shlex.split(data['NATIVE_CC']), str(makekeys), '-o', str(work / 'makekeys')], env)
headers = sorted((Path(data['CROSS_DESTDIR']) / 'usr/pkg/include/X11').glob('*keysym*.h'))
assert headers, 'Missing installed keysym inputs'
output = run('makekeys-execute', [str(work / 'makekeys'), *(str(path) for path in headers)])
assert 'hashString' in output and 'hashKeysym' in output
# Extract the exact native compiler/suffix probe from unchanged configure.
ft = query('freetype-metadata', 'graphics/freetype2', ['PKG_FAIL_REASON', 'CONFIGURE_ENV'])
assert not ft['PKG_FAIL_REASON'], ft['PKG_FAIL_REASON']
build_cc = [value for value in shlex.split(ft['CONFIGURE_ENV']) if value.startswith('CC_BUILD=')]
assert build_cc == ['CC_BUILD=' + data['NATIVE_CC']]
source = (freetype / 'builds/unix/configure').read_text()
start = source.index('  rm -f a.* b.* a_out.exe conftest.*')
finish = source.index('  CFLAGS_BUILD=', start)
assert '${CC_BUILD} conftest.c' in source[start:finish], 'Upstream native probe changed'
probe = 'set -eu\nas_me=configure as_lineno=0 LINENO=0\nas_fn_error() { echo "$2" >&2; exit 1; }\nexec 5>config.log 6>configure.log\n'
probe += source[start:finish] + '\n[ -z "$EXEEXT_BUILD" ]\n'
(work / 'freetype-probe').mkdir()
(work / 'freetype-probe/probe.sh').write_text(probe)
run('freetype-native-probe', [data['CONFIG_SHELL'], 'probe.sh'],
    {**env, 'CC_BUILD': build_cc[0].split('=', 1)[1]}, work / 'freetype-probe')
# libXt appends another command. Exercise the last value.
xt = query('libXt-metadata', 'x11/libXt', ['PKG_FAIL_REASON', 'CONFIGURE_ENV'])
assert not xt['PKG_FAIL_REASON'], xt['PKG_FAIL_REASON']
xt_commands = [value.split('=', 1)[1] for value in shlex.split(xt['CONFIGURE_ENV']) if value.startswith('CC_FOR_BUILD=')]
assert xt_commands and xt_commands[-1] == data['NATIVE_CC']
run('libXt-native-link', [*shlex.split(xt_commands[-1]), str(work / 'native.c'), '-o', str(work / 'libXt-native')], env)
assert run('libXt-native-execute', [str(work / 'libXt-native')]) == 'native C\n'
assert not (work / 'wrapper.log').exists() or not (work / 'wrapper.log').read_bytes()
# The unchanged target driver must still link ELF64/x86-64 through target binutils.
sysroot = data['CROSS_DESTDIR']
run('target-link', [data['CC'], '--sysroot=' + sysroot,
                    '-B' + sysroot + '/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/',
                    '-L' + sysroot + '/usr/pkg/gcc16/lib', str(work / 'native.c'), '-o', str(work / 'target')], env)
elf = (work / 'target').read_bytes()[:20]
assert elf.startswith(b'\x7fELF\x02\x01') and int.from_bytes(elf[18:20], 'little') == 62
for path, digest in provider_hashes.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
(work / 'provider-sha256.json').write_text(json.dumps(provider_hashes, indent=2) + '\n')
print('PASS: polluted-PATH native links/runs, makekeys, FreeType/libXt ABI commands and target ELF route')
