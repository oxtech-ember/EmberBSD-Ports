#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Replay actual mixed-provider cache fields, then check the recipe's bindings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import sys

sys.dont_write_bytecode = True
KEYS = ('LibArchive_INCLUDE_DIR', 'LibArchive_LIBRARY', 'LibUV_INCLUDE_DIR',
        'LibUV_LIBRARY', 'CURL_INCLUDE_DIR', 'CURL_LIBRARY_RELEASE')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cache(p):
    return {line.split(':', 1)[0]: line.split('=', 1)[1]
            for line in p.read_text().splitlines()
            if not line.startswith(('#', '//')) and ':' in line and '=' in line}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'recipe', 'baseline-cache', 'compile-commands',
                 'cmake', 'modules', 'prefix', 'cxx', 'output', 'lock-root', 'bmake'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--read-root', type=Path, action='append', required=True)
    a = cli.parse_args()
    assert sys.platform == 'darwin' and not os.path.lexists(a.output)
    for p in (a.sdk_source, a.recipe, a.baseline_cache, a.compile_commands,
              a.cmake, a.modules, a.prefix, a.cxx, a.bmake, *a.read_root):
        assert p.is_absolute() and p.exists(), str(p)
    assert not any(c.isspace() for c in str(a.prefix))
    sys.path.insert(0, str(a.sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk.process import ContextLocks
    from emberbsd_sdk.stream import capture_streamed
    from emberbsd_sdk.errors import CommandError
    assert emberbsd_sdk.API_VERSION == 1
    assert Path(emberbsd_sdk.__file__).resolve().parent == a.sdk_source / 'src/emberbsd_sdk'
    for n in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(n, lambda n, f: sys.exit(128 + n))
    with ContextLocks([str(a.output)], str(a.lock_root)), ContextLocks(
            [str(p) for p in [a.sdk_source, *a.read_root]], str(a.lock_root), shared=True):
        a.output.mkdir()
        (a.output / 'tmp').mkdir()
        env = dict(os.environ, TMPDIR=str(a.output / 'tmp'), TMP=str(a.output / 'tmp'),
                   TEMP=str(a.output / 'tmp'), PATH=str(a.prefix / 'bin') + ':/usr/bin:/bin:/usr/sbin:/sbin')
        inputs = [Path(__file__), a.recipe, a.baseline_cache, a.compile_commands]
        pins = {str(p): sha(p) for p in inputs}
        commands = []

        def run(name, argv, expected=0):
            try:
                r = capture_streamed(argv, cwd=str(a.output), env=env,
                                     stdout_limit=1024 * 1024, timeout=120)
                code, out, err = 0, r.value, r.stderr
                assert not r.stderr_truncated
            except CommandError as e:
                code, out, err = e.returncode, e.stdout, e.stderr
                assert not e.stdout_truncated and not e.stderr_truncated
            (a.output / (name + '.stdout')).write_bytes(out)
            (a.output / (name + '.stderr')).write_bytes(err)
            commands.append(dict(name=name, argv=argv, exit=code,
                                 stdout_sha256=hashlib.sha256(out).hexdigest(),
                                 stderr_sha256=hashlib.sha256(err).hexdigest()))
            assert (code != 0 if expected is None else code == expected), name
            return out, err

        recipe = a.recipe.read_text()
        block = recipe.split('.include "../../www/curl/buildlink3.mk"\n', 1)[1].split(
            '.include "../../mk/atomic64.mk"', 1)[0]
        mk = a.output / 'policy.mk'
        mk.write_text('CONFIGURE_ARGS=\n' + block)
        prefix_args = ['BUILDLINK_PREFIX.' + key + '=' + str(a.prefix)
                       for key in ('libarchive', 'libuv', 'curl')]
        positive = None
        for name, opsys, cross, builtin, count in (
                ('native', 'Darwin', 'no', 'no', 6),
                ('builtin', 'Darwin', 'no', 'yes', 0),
                ('cross', 'Darwin', 'yes', 'no', 0),
                ('netbsd', 'NetBSD', 'no', 'no', 0),
                ('linux', 'Linux', 'no', 'no', 0)):
            out, _ = run('policy-' + name, [str(a.bmake), '-f', str(mk), 'OPSYS=' + opsys,
                         'USE_CROSS_COMPILE=' + cross, *prefix_args,
                         *['USE_BUILTIN.' + k + '=' + builtin for k in ('libarchive', 'libuv', 'curl')],
                         '-v', 'CONFIGURE_ARGS'])
            args = shlex.split(out.decode())
            assert len([x for x in args if x.startswith('-D')]) == count
            if name == 'native':
                assert args[0] == '--'
                positive = args[1:]
        old = cache(a.baseline_cache)
        assert all(Path(old[k]).exists() for k in KEYS)
        entries = json.loads(a.compile_commands.read_text())
        assert len(entries) == 1
        argv = entries[0]['arguments']
        assert argv[0] == str(a.cxx)
        i, j = argv.index('-c'), argv.index('-o')
        flags = [v for k, v in enumerate(argv[1:], 1) if k not in (i, i + 1, j, j + 1)]
        project = a.output / 'project'
        project.mkdir()
        (project / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.30)\n'
            'project(ProviderProbe LANGUAGES NONE)\nfind_package(LibArchive 3.3.3 REQUIRED)\n'
            'find_package(LibUV 1.6 REQUIRED)\nfind_package(CURL REQUIRED)\n')
        source = a.output / 'consumer.cxx'
        source.write_text('#include <archive.h>\n#include <uv.h>\n#include <curl/curl.h>\n'
            '#include <cstdio>\n#include <cstring>\nint main(){\n'
            'const char* ssl=archive_openssl_version(); auto* curl=curl_version_info(CURLVERSION_NOW);\n'
            'std::printf("archive=%d uv=%s curl=%s openssl=%s\\n",archive_version_number(),'
            'uv_version_string(),curl->version,ssl?ssl:"none");\n'
            'return !(ARCHIVE_VERSION_NUMBER==archive_version_number() && UV_VERSION_HEX==uv_version()'
            ' && std::strcmp(LIBCURL_VERSION,curl->version)==0);}\n')
        for label, extra in (('before', []), ('after', positive)):
            build = a.output / label
            baseline = ['-D' + k + '=' + old[k] for k in KEYS]
            run(label + '-configure', [str(a.cmake), '-S', str(project), '-B', str(build),
                '-DCMAKE_MODULE_PATH=' + str(a.modules / 'Source/Modules') + ';' + str(a.modules / 'Modules'),
                *baseline, *extra])
            selected = cache(build / 'CMakeCache.txt')
            if label == 'after':
                assert all(Path(selected[k]).is_relative_to(a.prefix) for k in KEYS)
            exe = a.output / (label + '-consumer')
            incs = list(dict.fromkeys(selected[k] for k in KEYS if k.endswith('INCLUDE_DIR')))
            _, err = run(label + '-link', [str(a.cxx), *['-I' + x for x in incs], *flags,
                str(source), *[selected[k] for k in ('LibArchive_LIBRARY', 'LibUV_LIBRARY', 'CURL_LIBRARY_RELEASE')],
                '-o', str(exe)], None if label == 'before' else 0)
            if label == 'before':
                assert b'_archive_openssl_version' in err
            else:
                run('after-runtime', [str(exe)])
        assert all(sha(p) == h for p, h in pins.items())
        (a.output / 'result.json').write_text(json.dumps(dict(status='PASS', commands=commands,
            source_sha256=pins, limits='Replay of six actual failed-cache fields, not a new discovery baseline. '
            'Real source Find modules, GCC16 link/runtime and five extracted BSD-make policy cases. '
            'No full package, target execution, analyzer rerun or memory-safety claim.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
