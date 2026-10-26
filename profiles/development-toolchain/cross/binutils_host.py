# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Native Binutils selection and its existing build-tree BFD inputs."""
import os
from pathlib import Path
import re
import shlex
import sys

from emberbsd_sdk.errors import SDKError
from emberbsd_sdk.native_toolset import load_host_prefix

ROLES = ('cc cxx cpp as ld ar ranlib nm strip python sh gmake bsdtar patch '
         'awk sed grep egrep expr find xargs ls cmp diff mv cp rm ln mkdir rmdir '
         'touch cat sort tr head tail wc cut uniq basename dirname pwd date uname '
         'printf echo env install perl pkg-config xz true').split()
VECTORS = {'aarch64--netbsd': 'elf64-littleaarch64',
           'x86_64--netbsd': 'elf64-x86-64',
           'armv7--netbsdelf-eabihf': 'elf32-littlearm',
           'arm-none-eabi': 'elf32-littlearm'}
SAFE = re.compile(r'[A-Za-z0-9_./+@%=:,\-]+\Z')


def require(condition, message):
    if not condition:
        raise SDKError(message)


def native_selection(prefix, family):
    require(prefix, 'Select --host-prefix or EMBERBSD_HOST_PREFIX for native Binutils')
    selected = load_host_prefix(prefix, required_roles=ROLES, compiler_family=family)
    root = Path(selected.bundle_root)
    header = root / 'include/zlib.h'
    libraries = [root / 'lib' / name for name in ('libz.a', 'libz.dylib', 'libz.so')]
    require(header.is_file() and header.resolve().is_relative_to(root) and
            any(path.is_file() and path.resolve().is_relative_to(root) for path in libraries),
            'Install the common native zlib headers and library inside --host-prefix')
    require(Path(sys.executable).resolve() == Path(selected.tool('python')).resolve(),
            'The controller interpreter differs from the selected native Python')
    for variable, role in (('HOST_CC', 'cc'), ('HOST_CXX', 'cxx'), ('GMAKE', 'gmake')):
        value = os.environ.get(variable)
        require(value is None or value == selected.tool(role),
                variable + ' differs from the selected native tool')
    env = {'PATH': selected.path, 'SHELL': selected.tool('sh'),
           'CONFIG_SHELL': selected.tool('sh'), 'MAKEINFO': selected.tool('true'),
           'SDKROOT': '',
           'PKG_CONFIG': selected.tool('pkg-config'),
           'PKG_CONFIG_LIBDIR': selected.bundle_root + '/lib/pkgconfig:' + selected.bundle_root + '/share/pkgconfig',
           'PKG_CONFIG_PATH': '', 'PKG_CONFIG_SYSROOT_DIR': ''}
    for variable, role in (('CC', 'cc'), ('CXX', 'cxx'), ('CPP', 'cpp'), ('AS', 'as'),
                           ('LD', 'ld'), ('AR', 'ar'), ('RANLIB', 'ranlib'),
                           ('NM', 'nm'), ('STRIP', 'strip'), ('AWK', 'awk'),
                           ('SED', 'sed'), ('GREP', 'grep'), ('EGREP', 'egrep'),
                           ('INSTALL', 'install'), ('PERL', 'perl')):
        env[variable] = shlex.join(selected.command(role))
    for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags'):
        flags = list(selected.abi_flags[name])
        if name == 'cppflags':
            flags.append('-I' + selected.bundle_root + '/include')
        elif name == 'ldflags':
            flags.append('-L' + selected.bundle_root + '/lib')
        env[name.upper()] = shlex.join(flags)
    return selected, env


def _libtool_archive(path, active=()):
    """Read static link inputs as data, without sourcing Libtool shell code."""
    path = path.resolve(strict=True)
    require(path not in active, 'Cyclic BFD Libtool dependency: ' + str(path))
    text = path.read_text()
    values = {}
    for name in ('old_library', 'dependency_libs'):
        matches = re.findall(r'^' + name + r"='([^'\n]*)'$", text, re.M)
        require(len(matches) == 1, 'Missing or ambiguous Libtool field: ' + name)
        values[name] = matches[0]
    installed = re.findall(r'^installed=(yes|no)$', text, re.M)
    require(len(installed) == 1, 'Invalid Libtool install state')
    values['installed'] = installed[0]
    name = values['old_library']
    require(re.fullmatch(r'lib[A-Za-z0-9_.+\-]+\.a', name), 'Missing static Libtool archive')
    require(values['installed'] in ('yes', 'no'), 'Invalid Libtool install state')
    archive = path.parent / ('.libs' if values['installed'] == 'no' else '') / name
    require(archive.is_file(), 'Missing BFD link input: ' + str(archive))
    result = [str(archive)]
    dependencies = iter(shlex.split(values['dependency_libs']))
    for word in dependencies:
        require(SAFE.fullmatch(word), 'Unsupported BFD dependency argument: ' + word)
        if word in ('-framework', '-weak_framework', '-R'):
            argument = next(dependencies, '')
            require(bool(SAFE.fullmatch(argument)), 'Missing or unsafe BFD link argument: ' + word)
            require(argument.startswith('/') if word == '-R' else
                    re.fullmatch(r'[A-Za-z][A-Za-z0-9_.+\-]*', argument),
                    'Invalid BFD link argument: ' + word)
            result.extend((word, argument))
        elif word.endswith('.la'):
            dependency = Path(word)
            if not dependency.is_absolute():
                dependency = path.parent / dependency
            result.extend(_libtool_archive(dependency, (*active, path)))
        elif word.endswith('.a'):
            dependency = Path(word)
            if not dependency.is_absolute():
                dependency = path.parent / dependency
            require(dependency.is_file(), 'Missing BFD dependency: ' + str(dependency))
            result.append(str(dependency.resolve()))
        elif word.startswith('-L'):
            require(len(word) > 2, 'Missing BFD library search directory')
            directory = Path(word[2:])
            if not directory.is_absolute():
                directory = path.parent / directory
            result.append('-L' + str(directory.resolve()))
        else:
            require(word.startswith(('-l', '-Wl,', '-R/')) or word == '-pthread',
                    'Unsupported BFD link flag: ' + word)
            result.append(word)
    return result


def write_bfd_input(work, triplet, capture, env):
    """Write ordinary make inputs for the OS consumers, not an admission record."""
    work = Path(work).resolve(strict=True)
    require(SAFE.fullmatch(str(work)), 'Unsupported BFD work path')
    source, build = work / 'src', work / 'build'
    require(triplet in VECTORS, 'Unsupported BFD target: ' + triplet)
    required = ('src/include/elf/common.h', 'src/include/elf/external.h',
                'src/include/ansidecl.h', 'src/include/symcat.h',
                'build/bfd/bfd.h', 'build/bfd/bfdver.h',
                'build/bfd/.libs/libbfd.a',
                'build/libiberty/libiberty.a')
    for relative in required:
        require((work / relative).is_file(), 'Missing common BFD input: ' + relative)
    makefile = (build / 'bfd/Makefile').read_text()
    for name, value in (('srcdir', str(source / 'bfd')), ('target_alias', triplet)):
        require(re.findall(r'^' + name + r'\s*=\s*(.*?)\s*$', makefile, re.M) == [value],
                'BFD build differs from its source or target: ' + name)
    require(re.search(r'\b2\.47\b', (build / 'bfd/bfdver.h').read_text()),
            'BFD generated header is not Binutils 2.47')
    vectors = capture([work / 'prefix/bin' / (triplet + '-objdump'), '-i'], env=env).split()
    require(VECTORS[triplet] in vectors, 'Built BFD lacks target vector ' + VECTORS[triplet])
    libraries = _libtool_archive(build / 'bfd/libbfd.la')
    iberty = str(build / 'libiberty/libiberty.a')
    if iberty not in libraries:
        libraries.append(iberty)
    fields = {
        'TRIPLET': triplet, 'SOURCE': str(source), 'BUILD': str(build),
        'CPPFLAGS': ' '.join('-I' + str(path) for path in (build / 'bfd', source / 'include')),
        'LDADD': ' '.join(libraries),
        'DPADD': ' '.join(dict.fromkeys(word for word in libraries
                                     if word.startswith('/') and word.endswith('.a'))),
    }
    for value in fields.values():
        require(all(SAFE.fullmatch(word) for word in value.split()), 'Unsupported BFD make input')
    output = '# Generated by the common Ports Binutils producer. Do not edit.\n'
    output += ''.join('EMBER_HOST_BFD_' + name + '= ' + value + '\n' for name, value in fields.items())
    temporary = work / 'host-bfd.mk.tmp'
    with temporary.open('x') as stream:
        stream.write(output)
    temporary.replace(work / 'host-bfd.mk')
