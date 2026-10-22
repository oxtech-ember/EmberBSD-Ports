# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; shared GCC16 Ports producer policy, SDK API1 mechanisms.
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile

from emberbsd_sdk import inventory, jsonio, paths, process
from emberbsd_sdk.errors import SDKError, CommandError, ProcessOwnershipError
from emberbsd_sdk.stream import PRODUCER_STREAM_API, PRODUCER_INPUT_API, capture_streamed
from sdk_source import PRODUCER_QUARANTINE

PROFILE = Path(__file__).resolve().parent
VERSION = '16.2.0'
TARGETS = {'aarch64': ('aarch64--netbsd', 183, '__aarch64__', '-O2'), 'amd64': ('x86_64--netbsd', 62, '__x86_64__', '-O2 -march=nocona -mtune=nocona -mfpmath=sse')}
TOOLS = 'ar as ld nm objcopy objdump ranlib readelf strip'.split()
BINUTILS = 'ar as elfedit ld nm objcopy objdump ranlib readelf size strings strip'.split()
CACHE = {'ac_cv_func_clock_gettime': 'yes', 'ac_cv_func_gethostbyname_r': 'no', 'ac_cv_func_freelocale': 'no', 'ac_cv_func_newlocale': 'no', 'ac_cv_func_uselocale': 'no'}
sha = inventory.sha256_file
QUARANTINE = PRODUCER_QUARANTINE


def require(condition, message):
    if not condition:
        raise SDKError(message)


def build_path(value):
    require(Path(value).is_absolute(), 'Absolute paths required')
    return Path(paths.build_path(value))


def new_path(value):
    require(paths.entry(value) is None, 'NEW_WORK already exists')
    path = build_path(value)
    require(paths.entry(path) is None, 'NEW_WORK already exists')
    return path


def jobs(default=None):
    value = os.environ.get('CROSS_JOBS', str(default if default else os.cpu_count() or ''))
    require(re.fullmatch(r'[0-9]+', value) and int(value) > 0, 'CROSS_JOBS must be positive')
    return str(int(value))


def environment(values=None):
    env = process.sanitized_environment()
    env.pop('CONFIG_SITE', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if platform.system() == 'Darwin' and 'SDKROOT' in os.environ:
        env['SDKROOT'] = os.environ['SDKROOT']
    env.update(values or {})
    if platform.system() == 'Darwin' and env.get('SDKROOT'):
        sdk = Path(env['SDKROOT'])
        require(sdk.is_absolute() and sdk.is_dir(), 'SDKROOT must name an existing absolute directory')
    return env


def capture(argv, env=None, cwd=None, input=None):
    require(type(PRODUCER_STREAM_API) is int and PRODUCER_STREAM_API == 1 and
            type(PRODUCER_INPUT_API) is int and PRODUCER_INPUT_API == 1,
            'SDK producer stream and input API1 are required')
    try:
        result = capture_streamed([str(arg) for arg in argv], env=environment(env),
                                  cwd=cwd, input=input, stdout_limit=16 * 1024 * 1024,
                                  stderr_limit=1024 * 1024, timeout=120)
    except CommandError as error:
        require(not error.stdout_truncated, 'Host query stdout exceeds the capture limit')
        require(not error.stderr_truncated, 'Host query stderr exceeds the capture limit')
        raise
    require(not result.stderr_truncated, 'Host query stderr exceeds the capture limit')
    return result.value.decode('utf-8')


def assert_recoverable(work):
    marker = Path(work) / QUARANTINE
    require(paths.entry(marker) is None, 'Producer shutdown is unproven. Recover this work explicitly before reuse: ' + str(marker))


def logged(argv, log, env=None, cwd=None, append=False, quarantine=None):
    log = Path(log)
    if quarantine is not None:
        assert_recoverable(quarantine)
    if not append and paths.entry(log) is not None:
        paths.regular_file(log)
        descriptor, previous = tempfile.mkstemp(prefix=log.name + '.previous.', dir=log.parent)
        os.close(descriptor)
        log.replace(previous)
    try:
        return process.run_logged([str(arg) for arg in argv], log, cwd=cwd, env=environment(env), append=append)
    except ProcessOwnershipError as error:
        if quarantine is not None:
            marker = Path(quarantine) / QUARANTINE
            try:
                jsonio.write_json(marker, {'schema': 1, 'state': 'producer-ownership-unproven', 'work': str(quarantine), 'log': str(log), 'argv': [str(arg) for arg in argv], 'error': str(error), 'session': error.sid, 'reason': error.reason})
            except Exception as marker_error:
                raise SDKError('Producer shutdown is unproven. Cannot persist the reuse refusal at ' + str(marker) + ': ' + str(marker_error)) from error
        raise


def policy_sources():
    import sdk_source
    return [Path(__file__), Path(sdk_source.__file__)] + sorted((Path(sdk_source.load()) / 'src/emberbsd_sdk').glob('*.py'))


def digest_rows(files):
    return ''.join(sha(Path(path).resolve(strict=True)) + '  ' + str(path) + '\n' for path in files)


def source_row(name, version, manifests=None):
    found = []
    for manifest in manifests or [PROFILE / 'sources.tsv']:
        for line in Path(manifest).read_text().splitlines():
            fields = line.split('\t')
            if fields[:2] == [name, version]:
                found.append(fields)
    require(len(found) == 1, 'Missing or ambiguous pinned source: ' + name)
    return found[0]


def audit_patches(recipe, exclude_isl=True):
    recipe = Path(recipe)
    entries = re.findall(r'^SHA1 \((patch-.+)\) = ([0-9a-f]{40})$', (recipe / 'distinfo').read_text(), re.M)
    entries = [(name, digest) for name, digest in entries if not exclude_isl or name != 'patch-isl_configure']
    require(entries and len({name for name, _ in entries}) == len(entries), 'No recipe patches or duplicate patch identity')
    for name, digest in entries:
        require(re.fullmatch(r'patch-[A-Za-z0-9_.+\-]+', name), 'Invalid patch name')
        patch = recipe / 'patches' / name
        paths.regular_file(patch)
        filtered = b''.join(line for line in patch.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)
        require(hashlib.sha1(filtered).hexdigest() == digest, 'Patch SHA1 mismatch: ' + name)
    return [name for name, _ in entries]


def audit_source(pkgsrc, archive, runtime=True):
    recipe = Path(pkgsrc) / 'lang/gcc16'
    expected = source_row('gcc', VERSION)[3]
    require(sha(archive) == expected, 'GCC archive SHA256 mismatch or missing archive')
    patches = audit_patches(recipe)
    require('patch-gcc_cp_module.cc' in patches, 'The repaired GCC16 modules recipe is required')
    if runtime:
        make = (recipe / 'Makefile').read_text()
        require('s,libtool_VERSION=6:,libtool_VERSION=7:,g' in make and '--disable-libssp' in make, 'Unsupported NetBSD runtime ABI recipe')
    return expected, patches


def prepare_source(pkgsrc, archive, source, runtime=True, quarantine=None, output=None):
    source = new_path(source)
    _, patches = audit_source(pkgsrc, archive, runtime)
    source.mkdir()
    extract_log = source.parent / (source.name + '-extract.log')
    require(paths.entry(extract_log) is None, 'Source extraction log already exists')
    logged(['tar', '-xpf', archive, '--strip-components=1', '-C', source], extract_log, quarantine=quarantine)
    for name in patches:
        if name != 'patch-gcc_Makefile.in':
            patch_log = source.parent / (source.name + '-' + name + '.log')
            require(paths.entry(patch_log) is None, 'Source patch log already exists')
            logged(['patch', '-f', '-N', '-F', '0', '-p0', '-d', source, '-i', Path(pkgsrc) / 'lang/gcc16/patches' / name], patch_log, quarantine=quarantine)
            (output if output is not None else sys.stdout.buffer).write(patch_log.read_bytes())
    if runtime:
        configure = source / 'libstdc++-v3/configure'
        data = configure.read_bytes()
        require(len(re.findall(rb'^libtool_VERSION=6:', data, re.M)) == 1, 'Unexpected upstream libstdc++ ABI selection')
        configure.write_bytes(data.replace(b'libtool_VERSION=6:', b'libtool_VERSION=7:'))


def check_math(math):
    math = build_path(math)
    macros = {'gmp': {'__GNU_MP_VERSION': '6', '__GNU_MP_VERSION_MINOR': '3', '__GNU_MP_VERSION_PATCHLEVEL': '0'}, 'mpfr': {'MPFR_VERSION_MAJOR': '4', 'MPFR_VERSION_MINOR': '2', 'MPFR_VERSION_PATCHLEVEL': '2'}, 'mpc': {'MPC_VERSION_MAJOR': '1', 'MPC_VERSION_MINOR': '4', 'MPC_VERSION_PATCHLEVEL': '1'}}
    for library, definitions in macros.items():
        paths.regular_file(math / 'lib' / ('lib' + library + '.a'))
        header = (math / 'include' / (library + '.h')).read_text()
        for name, version in definitions.items():
            require(re.findall(r'^#define\s+' + name + r'\s+(\S+)\s*$', header, re.M) == [version], 'Host ' + library + ' version mismatch; use host-math.py')
    return math


def host_compilers(native_clang=False):
    cc, cxx = os.environ.get('HOST_CC', 'gcc-16'), os.environ.get('HOST_CXX', 'g++-16')
    for compiler in (cc, cxx):
        require(shutil.which(compiler), 'Host compiler missing: ' + compiler)
        if native_clang:
            require(re.search(r'^(Apple )?clang version [0-9]+', capture([compiler, '--version']), re.M), 'Native Clang required in host-only mode')
            target = capture([compiler, '-dumpmachine']).strip()
            host = platform.system(), platform.machine()
            allowed = ((host == ('Darwin', 'arm64') and re.fullmatch(r'(?:arm64|aarch64)-apple-darwin.*', target)) or (host == ('Darwin', 'x86_64') and re.fullmatch(r'x86_64-apple-darwin.*', target)) or (host[0] == 'Linux' and host[1] in ('aarch64', 'x86_64') and re.fullmatch(re.escape(host[1]) + r'-.*-linux-gnu', target) and platform.libc_ver()[0] == 'glibc'))
            require(allowed, 'Host-only Clang target differs from development host')
        else:
            require(capture([compiler, '-dumpfullversion']).startswith('16.'), 'GCC 16 host compiler required: ' + compiler)
    return cc, cxx


def check_compilers(prefix, target):
    triplet, _, arch, _ = TARGETS[target]
    tools = {name: Path(prefix) / 'bin' / (triplet + '-' + name) for name in ['gcc', 'g++'] + TOOLS}
    for name, path in tools.items():
        require(os.access(path, os.X_OK), 'Missing host cross tool: ' + name)
    for name in ('gcc', 'g++'):
        require(capture([tools[name], '-dumpmachine']).strip() == triplet, 'Compiler target mismatch')
        require(capture([tools[name], '-dumpfullversion']).strip() == VERSION, 'GCC 16.2.0 is required')
    macros = capture([tools['gcc'], '-dM', '-E', '-x', 'c', '-'], input=b'\n').splitlines()
    require(all('#define ' + value in macros for value in ['__GNUC__ 16', '__NetBSD__ 1', '__SIZEOF_POINTER__ 8', arch + ' 1']), 'Compiler target ABI mismatch')
    return tools


def target_tools(prefix, target):
    triplet = TARGETS[target][0]
    env = {'PATH': str(prefix) + '/bin:' + os.environ.get('PATH', '')}
    for name in TOOLS:
        executable = Path(prefix) / 'bin' / (triplet + '-' + name)
        require(os.access(executable, os.X_OK), 'Missing target binutils tool: ' + name)
        version = capture([executable, '--version'])
        require(re.search(r'^GNU ' + ('assembler' if name == 'as' else name) + r'[ (]', version, re.M), 'Target ' + name + ' is not selected GNU binutils')
        require(name != 'as' or 'target of ' in version and triplet in version, 'GNU assembler target mismatch')
        env[name.upper() + '_FOR_TARGET'] = str(executable)
    return env


def manifests(root, output):
    tree = inventory.snapshot_tree(root)
    output = Path(output)
    (output / 'stage.sha256').write_text(''.join(sorted(record['sha256'] + '  ./' + name + '\n' for name, record in tree.items() if record['kind'] == 'file')))
    (output / 'stage.symlinks').write_text(''.join('./' + name + '\t' + record['target'] + '\n' for name, record in tree.items() if record['kind'] == 'link'))
