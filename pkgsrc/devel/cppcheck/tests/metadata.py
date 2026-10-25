#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Evaluate native recipe options with selected bmake and a complete environment."""
import argparse
import json
from pathlib import Path
import shlex
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
_, arguments = load_sdk()
from emberbsd_sdk.stream import capture_streamed
parser = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'makeconf', 'bmake', 'environment', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args(arguments)
environment = json.loads(a.environment.read_text())
assert isinstance(environment, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in environment.items())
assert all(a.__dict__[name].is_absolute() for name in ('pkgsrc', 'makeconf', 'bmake', 'environment', 'work'))
a.work.mkdir()
fields = ('PKGNAME', 'PKG_OPTIONS', 'CMAKE_CONFIGURE_ARGS', 'TOOL_PYTHONBIN', 'PYTHONBIN', 'TOOLBASE', 'PREFIX', 'TOOL_DEPENDS', 'DEPENDS', 'BUILDLINK_API_DEPENDS.pcre2', 'BUILD_TARGET', 'TEST_TARGET', 'BUILD_DEPENDS', 'PKG_FAIL_REASON')
records = []
for name, option in (('default', ''), ('qt6', 'qt6'), ('legacy-qt5', 'qt5')):
    argv = [str(a.bmake), '-C', str(a.pkgsrc / 'devel/cppcheck'), 'MAKECONF=' + str(a.makeconf), 'PKG_OPTIONS.cppcheck=' + option]
    for field in fields:
        argv.extend(('-V', '${' + field + '}'))
    result = capture_streamed(argv, env=environment, timeout=120, stdout_limit=4*1024*1024)
    (a.work / (name + '.stdout')).write_bytes(result.value)
    (a.work / (name + '.stderr')).write_bytes(result.stderr)
    lines = result.value.decode().splitlines()
    assert len(lines) == len(fields), (name, lines)
    values = dict(zip(fields, lines))
    assert values['PKGNAME'] == 'cppcheck-2.22.0nb2', values
    assert not values['PKG_FAIL_REASON'], values['PKG_FAIL_REASON']
    selected = values['PKG_OPTIONS'].split()
    assert ('qt6' in selected) == bool(option) and 'qt5' not in selected, values
    args = {}
    for word in shlex.split(values['CMAKE_CONFIGURE_ARGS']):
        if word.startswith('-D') and '=' in word:
            key, value = word[2:].split('=', 1)
            args[key.split(':')[0]] = value
    for key in ('BUILD_CLI', 'BUILD_TESTING', 'CPPCHK_GLIBCXX_DEBUG', 'HAVE_RULES', 'BUILD_MANPAGE', 'DISABLE_DMAKE'):
        assert args[key] == 'ON', (key, args)
    assert args['BUILD_GUI'] == ('ON' if option else 'OFF'), args
    assert args['USE_BUNDLED_TINYXML2'] == 'OFF' and args['USE_BOOST'] == 'On', args
    assert args['Python_EXECUTABLE'] == values['TOOL_PYTHONBIN'], args
    assert args['DB2MAN'].startswith(values['TOOLBASE'] + '/share/xsl/'), args
    for key in ('PKG_CONFIG_EXECUTABLE', 'LIBXML2_XMLLINT_EXECUTABLE', 'XSLTPROC'):
        assert args[key].startswith('/'), (key, args)
    for provider in ('docbook-xsl', 'libxslt', 'libxml2'):
        assert provider in values['TOOL_DEPENDS'], values
    assert args['LIBXML2_XMLLINT_EXECUTABLE'] == values['TOOLBASE'] + '/bin/xmllint', args
    assert args['XSLTPROC'] == values['TOOLBASE'] + '/bin/xsltproc', args
    assert 'pygments' in values['DEPENDS'] and 'z3' not in values['DEPENDS'], values
    assert 'simplecpp>=1.9.1nb1' in values['DEPENDS'], values
    assert 'picojson>=1.3.0.20210117' in values['BUILD_DEPENDS'], values
    assert values['BUILD_TARGET'].split() == ['all', 'man'] and values['TEST_TARGET'] == 'test', values
    records.append({'name': name, 'argv': argv, 'values': values})
# Provider and transitive-consumer metadata come from the same exported tree.
provider_fields = ('PKGNAME', 'CMAKE_CONFIGURE_ARGS', 'BUILD_DEPENDS', 'DEPENDS',
                   'TEST_TARGET', 'PKG_FAIL_REASON', 'DISTFILES', 'WRKSRC')
for package, expected in (('devel/simplecpp', 'simplecpp-1.9.1nb1'),
                          ('devel/picojson', 'picojson-1.3.0.20210117'),
                          ('security/zoneminder', 'zoneminder-1.38.4nb3')):
    name = package.replace('/', '-')
    argv = [str(a.bmake), '-C', str(a.pkgsrc / package), 'MAKECONF=' + str(a.makeconf)]
    for field in provider_fields:
        argv.extend(('-V', '${' + field + '}'))
    result = capture_streamed(argv, env=environment, timeout=120, stdout_limit=4*1024*1024)
    (a.work / (name + '.stdout')).write_bytes(result.value)
    (a.work / (name + '.stderr')).write_bytes(result.stderr)
    lines = result.value.decode().splitlines()
    assert len(lines) == len(provider_fields), (name, lines)
    values = dict(zip(provider_fields, lines))
    assert values['PKGNAME'] == expected, values
    # Fetch and checksum use the evaluated DISTFILES; each one needs a distinfo record.
    info = (a.pkgsrc / package / 'distinfo').read_text()
    for distfile in values['DISTFILES'].split():
        assert f'Size ({distfile}) = ' in info, (package, distfile)
    if package == 'devel/picojson':
        # GitHub names the archive directory after the commit.
        assert values['WRKSRC'].endswith('/picojson-111c9be5188f7350c2eac9ddaedd8cca3d7bf394'), values
    if package == 'security/zoneminder':
        assert '-DJWT_EXTERNAL_PICOJSON:BOOL=ON' in values['CMAKE_CONFIGURE_ARGS'], values
        assert 'picojson>=1.3.0.20210117' in values['BUILD_DEPENDS'], values
        # Platform admission for this application is separate from this dependency edge.
    else:
        assert not values['PKG_FAIL_REASON'], values
        assert values['TEST_TARGET'] == 'test', values
        flag = '-DBUILD_SHARED_LIBS:BOOL=ON' if package.endswith('simplecpp') else '-DBUILD_TESTING:BOOL=ON'
        assert flag in values['CMAKE_CONFIGURE_ARGS'], values
        if package.endswith('simplecpp'):
            assert '-DSIMPLECPP_GLIBCXX_DEBUG:BOOL=ON' in values['CMAKE_CONFIGURE_ARGS'], values
    records.append({'name': name, 'argv': argv, 'values': values})
(a.work / 'result.json').write_text(json.dumps({'scope': 'native metadata only; no configure, compiler or target execution', 'records': records}, indent=2) + '\n')
print('PASS: native default, Qt6 and legacy Qt5 options; shared dependencies and selected host tools')
print('PASS: SimpleCpp/PicoJSON providers and ZoneMinder external-PicoJSON dependency edge; distfiles recorded')
