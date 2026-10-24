#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Port of the ncurses native regression.
"""Check native admission, then replay the qualified ncurses probe on Linux."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
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
    raise SystemExit('Use PKGSRC MAKECONF NCURSES_WORK NEW_PROFILE NEW_WORK; set absolute BMAKE')
tree, conf, original, profile = (Path(p).resolve(strict=True) for p in args[:4])
work = Path(args[4])
if not work.is_absolute():
    raise SystemExit('Use an absolute new output directory')
make = Path(os.environ['BMAKE'])
if not make.is_absolute():
    raise SystemExit('BMAKE must name the selected absolute SDK bmake')
work.mkdir()
configure = original / 'ncurses-6.6/configure'
log = (original / 'ncurses-6.6/config.log').read_text()
text = configure.read_text()
start = text.index('\tcf_save_crossed=$cross_compiling\n\tcf_save_ac_link=$ac_link\n')
finish = text.index("\nelse\n\t: ${BUILD_CC:='${CC}'}", start)
probe = text[start:finish]
assert "ac_link='$BUILD_CC -o" in probe and 'Cross-build requires two compilers.' in probe
assert '"./conftest$ac_exeext"' in probe, 'Missing upstream compile/run check'
defines_match = re.search(r'\n(#define PACKAGE "ncurses"\n.*)\n\nconfigure: exit [0-9]+\n?\Z', log, re.S)
assert defines_match and '#define NCURSES_VERSION "6.6"' in defines_match[1]
defines = defines_match[1]
config = conf.read_text()
include_pattern = r'^\.include "[^"\n]*/(?:common-build-tools/cross/mk\.conf|EMBERBSD-CROSS-MK\.CONF)"$'
assert len(re.findall(include_pattern, config, re.M)) == 1
hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
          for path in (configure, conf, profile)}
commands = []
clean_env = dict(os.environ)
for key in ('CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH',
            'GCC_EXEC_PREFIX', 'COMPILER_PATH'):
    clean_env.pop(key, None)
clean_env['LC_ALL'] = 'C'


def run(label, argv, env=None, cwd=work, expected=0):
    try:
        result = capture_streamed(argv, env={**clean_env, **(env or {})}, cwd=str(cwd),
                                  timeout=300, stdout_limit=8 * 1024 * 1024)
        code, output, errors = 0, result.value, result.stderr
        if result.stderr_truncated:
            raise SDKError('Producer stderr exceeded the capture limit')
    except CommandError as error:
        code, output, errors = error.returncode, error.stdout, error.stderr
        if error.stderr_truncated or error.stdout_truncated:
            raise SDKError('Producer failure output exceeded the capture limit') from error
    (work / (label + '.stdout')).write_bytes(output)
    (work / (label + '.stderr')).write_bytes(errors)
    commands.append({'name': label, 'argv': argv, 'cwd': str(cwd),
                     'exitstatus': code, 'expected': expected})
    (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    if expected == 'failure':
        assert code != 0, label + ': unexpectedly accepted'
    else:
        assert code == expected, label + ': ' + errors.decode('utf-8', 'replace')
    return output.decode(), errors.decode()


# Copy the selected profile and retain its prepared companion files read-only.
for sibling in profile.parent.iterdir():
    if sibling.name not in ('profile.mk', 'mk.conf'):
        (work / sibling.name).symlink_to(sibling)
(work / 'profile.mk').write_bytes(profile.read_bytes())
(work / 'mk.conf').write_text(re.sub(include_pattern,
    '.include "' + str(work / 'profile.mk') + '"', config, flags=re.M))
base = [str(make), '-C', str(tree / 'devel/ncurses'),
        'MAKECONF=' + str(work / 'mk.conf'), 'WRKOBJDIR=' + str(work / 'objects')]
# Fail at admission, before this test starts a compiler. The old system-tool
# linker failure is historical evidence, not an expected qualified-SDK failure.
for name, value, message in (
        ('EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT', '',
         'Set EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT from one qualified SDK native toolset'),
        ('EMBERBSD_CROSS_BUILD_CC', '/usr/bin/cc',
         'EMBERBSD_CROSS_BUILD_CC differs from the qualified SDK tool')):
    output, errors = run('admission-' + name, [*base, name + '=' + value,
                         '-V', '${PKG_FAIL_REASON}'], expected='failure')
    assert message in errors, (name, output, errors)

names = ['PKG_FAIL_REASON', 'NATIVE_OPSYS', 'NATIVE_CC', 'NATIVE_CXX',
         'CCPATH', 'CROSS_DESTDIR', 'CWRAPPERS_APPEND.cc', 'LDFLAGS',
         'NATIVE_CPPFLAGS', 'NATIVE_CFLAGS', 'NATIVE_CXXFLAGS', 'NATIVE_LDFLAGS',
         'EMBERBSD_CROSS_BUILD_CC', 'EMBERBSD_CROSS_BUILD_CXX',
         'EMBERBSD_NATIVE_BMAKE', 'EMBERBSD_CROSS_BUILD_PYTHON', 'CONFIG_SHELL',
         'CROSS_MACHINE_ARCH', 'TOOLDIR']
query = []
for name in names:
    query += ['-V', '${' + name + '}']
query += ['-V', '${CONFIGURE_ENV:MBUILD_CC=*}']
output, _ = run('metadata', [*base, *query])
values = output.splitlines()
assert len(values) == len(names) + 1, values
data = dict(zip(names, values))
assert not data['PKG_FAIL_REASON'], data['PKG_FAIL_REASON']
assert data['NATIVE_OPSYS'] == 'Linux', 'This native probe requires Linux'
assert Path(data['EMBERBSD_NATIVE_BMAKE']).resolve(strict=True) == make.resolve(strict=True)
assert Path(data['EMBERBSD_CROSS_BUILD_PYTHON']).resolve(strict=True) == Path(sys.executable).resolve(strict=True)
assert shlex.split(values[-1]) == ['BUILD_CC=' + data['NATIVE_CC']]
for language, flags in (('CC', 'CFLAGS'), ('CXX', 'CXXFLAGS')):
    compiler = shlex.split(data['NATIVE_' + language])
    expected = [data['EMBERBSD_CROSS_BUILD_' + language]]
    expected += shlex.split(data['NATIVE_CPPFLAGS'])
    expected += shlex.split(data['NATIVE_' + flags])
    expected += shlex.split(data['NATIVE_LDFLAGS'])
    assert compiler == expected, 'Declared native ABI command was truncated'
    output, _ = run(language + '-version', [*compiler, '-dumpfullversion'])
    assert output.strip() == '16.2.0'
    hashes[compiler[0]] = hashlib.sha256(Path(compiler[0]).read_bytes()).hexdigest()
(work / 'metadata.json').write_text(json.dumps(data, indent=2) + '\n')

# Preserve the actual upstream compile/run probe under the polluted wrapper PATH.
binary_dir = work / 'bin'
wrappers = work / 'wrapper-config'
binary_dir.mkdir()
wrappers.mkdir()
for path in (original / '.cwrapper/bin').iterdir():
    real = path.resolve(strict=True)
    hashes[str(real)] = hashlib.sha256(real.read_bytes()).hexdigest()
    (binary_dir / path.name).symlink_to(real)
for path in (original / '.cwrapper/config').iterdir():
    hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    value = re.sub(r'^worklog=.*$', 'worklog=' + str(work / 'wrapper.log'), path.read_text(), flags=re.M)
    value = re.sub(r'^wrksrc=.*$', 'wrksrc=' + str(work), value, flags=re.M)
    (wrappers / path.name).write_text(value.replace(str(original / '.cwrapper/bin'), str(binary_dir)))
recorded_path = re.search(r'^path=(.*)$', (wrappers / 'ld').read_text(), re.M)
assert recorded_path, 'Missing real linker-wrapper PATH'
env = {'PATH': str(binary_dir) + ':' + recorded_path[1],
       'CWRAPPERS_CONFIG_DIR': str(wrappers), 'BUILD_CC': data['NATIVE_CC']}
header = 'set -eu\nas_me=configure\ncross_compiling=yes\nac_link=unused\nac_ext=c\nac_objext=o\nac_exeext=\nECHO_N= ECHO_T= ECHO_C=\nBUILD_CFLAGS= BUILD_CPPFLAGS= BUILD_LDFLAGS= BUILD_LIBS=\nexec 5>config.log 6>configure.log\n'
(work / 'probe.sh').write_text(header + probe + '\n')
(work / 'confdefs.h').write_text(defines)
run('upstream-probe', [data['CONFIG_SHELL'], './probe.sh'], env)
result = (work / 'config.log').read_text()
assert 'result: yes' in result and result.count('$? = 0') == 2
assert not (work / 'wrapper.log').exists() or not (work / 'wrapper.log').read_bytes()
# Keep the selected AArch64 target compiler and verify its actual ELF route.
assert data['CROSS_MACHINE_ARCH'] == 'aarch64'
assert data['CCPATH'] == data['TOOLDIR'] + '/bin/aarch64--netbsd-gcc'
program = re.search(r'cat >"conftest\.\$ac_ext" <<_ACEOF\n(.*?)\n_ACEOF', probe, re.S)
assert program and program[1].count('${cf_cv_main_return:-return}') == 1
(work / 'target.c').write_text(program[1].replace('${cf_cv_main_return:-return}', 'return'))
run('target-link', [data['CCPATH'], '--sysroot=' + data['CROSS_DESTDIR'],
    *shlex.split(data['CWRAPPERS_APPEND.cc']), str(work / 'target.c'),
    *shlex.split(data['LDFLAGS']), '-o', str(work / 'target')])
elf = (work / 'target').read_bytes()[:20]
assert elf.startswith(b'\x7fELF\x02\x01') and int.from_bytes(elf[18:20], 'little') == 183
for path, digest in hashes.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
(work / 'result.json').write_text(json.dumps({'inputs': hashes, 'metadata': data,
    'scope': 'Native admission, actual ncurses native probe and target AArch64 link; no full package or target execution.'}, indent=2) + '\n')
print('PASS: invalid native inputs refused; qualified ncurses probe and target AArch64 route passed')
