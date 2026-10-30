#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted Go recipe regression.
"""Exercise real Go recipe targets and host/target environment evaluation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'bmake', 'shell', 'seed', 'pkg-admin'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    recipe = args.pkgsrc / 'lang/go127'
    with tempfile.TemporaryDirectory(prefix='go-routing-') as temporary:
        work = Path(temporary)
        source = work / 'source'
        (source / 'src').mkdir(parents=True)
        result = work / 'environment.json'
        capture = work / 'capture.py'
        keys = ('CC', 'CXX', 'CC_FOR_TARGET', 'CXX_FOR_TARGET', 'SDKROOT',
                'GOROOT_BOOTSTRAP', 'GOTOOLCHAIN', 'GOENV', 'GOMAXPROCS', 'GOOS', 'GOARCH',
                'PKG_CONFIG')
        capture.write_text('import json, os\nfrom pathlib import Path\n' +
                           f'Path({str(result)!r}).write_text(json.dumps(' +
                           f'{{key: os.environ.get(key) for key in {keys!r}}}))\n')
        base = [str(args.bmake), '-m', str(args.bmake.parent.parent / 'share/mk'),
                'SHELL=' + str(args.shell), 'MAKECONF=' + str(args.makeconf),
                'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'WRKOBJDIR=' + str(work / 'objects'),
                'WRKSRC=' + str(source), 'GOROOT_BOOTSTRAP=' + str(args.seed),
                'BASH=' + sys.executable + ' ' + str(capture), 'MAKE_JOBS=3']
        def run(argv, cwd=recipe, success=True, env=None):
            proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=env)
            assert (proc.returncode == 0) == success, (argv, proc.stdout, proc.stderr)
            return proc.stdout if success else proc.stdout + proc.stderr
        missing = 'GOROOT_BOOTSTRAP=' + str(work / 'missing-seed')
        run([*base, missing, '-V', '${PKGNAME}'])
        run([*base, missing, 'fetch', 'checksum'])
        query = run([*base, '-V', '${CC}', '-V', '${CXX}', '-V', '${OSX_SDK_PATH}'])
        cc, cxx, sdk = query.strip().splitlines()
        for target in ('do-build', 'do-test'):
            run([*base, target])
            actual = json.loads(result.read_text())
            expected = dict(CC=cc, CXX=cxx, CC_FOR_TARGET=cc, CXX_FOR_TARGET=cxx,
                            SDKROOT=sdk, GOROOT_BOOTSTRAP=str(args.seed),
                            GOTOOLCHAIN='local', GOENV='off', GOMAXPROCS='3',
                            # cmd/dist records PKG_CONFIG in zdefaultcc.go; the
                            # work-directory wrapper is gone after the build.
                            PKG_CONFIG='pkg-config')
            for key, value in expected.items():
                assert actual[key] == value, (target, key, actual[key], value)

        # Evaluate the real environment fragment with distinct cross commands.
        fixture = work / 'Makefile'
        fixture.write_text('\n'.join([
            'USE_CROSS_COMPILE=yes', 'MACHINE_GNU_PLATFORM=aarch64--netbsd',
            'CC=/cross/bin/aarch64--netbsd-clang --sysroot=/target',
            'CXX=/cross/bin/aarch64--netbsd-clang++ --sysroot=/target',
            'NATIVE_CC=host-clang -isysroot /native --ld-path=/native/ld64.lld',
            'NATIVE_CXX=host-clang++ -isysroot /native --ld-path=/native/ld64.lld',
            'GOOPT=GOOS=netbsd GOARCH=amd64 CC=stale-target',
            'GOROOT_BOOTSTRAP=' + str(args.seed), 'WRKDIR=' + str(work), 'MAKE_JOBS=3',
            '.include "' + str(recipe / 'build-env.mk') + '"',
            'capture:', '\t@/usr/bin/env PKG_CONFIG=' + str(work / '.tools/bin/pkg-config') +
            ' ${_GO_BUILD_ENV} ' + sys.executable + ' ' + str(capture), '']))
        run([str(args.bmake), '-r', '-f', str(fixture), 'capture'], cwd=work)
        actual = json.loads(result.read_text())
        assert actual['CC'] == 'host-clang -isysroot /native --ld-path=/native/ld64.lld', actual
        assert actual['CXX'] == 'host-clang++ -isysroot /native --ld-path=/native/ld64.lld', actual
        # The toolchain records these as its defaults on the target, so they
        # are command names there, not build-host paths or cross prefixes.
        assert actual['CC_FOR_TARGET'] == 'clang', actual
        assert actual['CXX_FOR_TARGET'] == 'clang++', actual
        assert actual['PKG_CONFIG'] == 'pkg-config', actual
        assert actual['GOOS'] == 'netbsd' and actual['GOARCH'] == 'amd64', actual

        # Exercise the actual cross-test branch without a native-only profile.
        failure = work / 'fail.py'
        failure.write_text('import sys\nprint(" ".join(sys.argv[1:]))\nsys.exit(1)\n')
        test_rule = 'do-test:' + (recipe / 'Makefile').read_text().split('do-test:', 1)[1].split('.include "../../mk/bsd.pkg.mk"', 1)[0]
        fixture.write_text(fixture.read_text() + '\nGO_PLATFORM=netbsd_amd64\nFAIL_MSG=' +
                           sys.executable + ' ' + str(failure) + '\n' + test_rule)
        refusal = run([str(args.bmake), '-r', '-f', str(fixture), 'do-test'], cwd=work, success=False)
        assert 'Cross-built Go tests require execution on netbsd_amd64' in refusal, refusal

        check = [str(args.shell), str(recipe / 'files/check-bootstrap.sh')]
        env = os.environ | {'GOENV': 'off', 'GOTOOLCHAIN': 'local'}
        identity = run([str(args.seed / 'bin/go'), 'env', 'GOHOSTOS', 'GOHOSTARCH'], env=env).splitlines()
        run([*check, str(args.seed), *identity, str(args.pkg_admin)])
        run([*check, str(args.seed), identity[0], 'wrong-arch', str(args.pkg_admin)], success=False)
        run([*check, str(work / 'missing-seed'), *identity, str(args.pkg_admin)], success=False)
        fake = work / 'old-seed/bin'
        fake.mkdir(parents=True)
        (fake / 'go').write_text('#!' + str(args.shell) + '\nprintf "go1.24.5\\n' +
                                 identity[0] + '\\n' + identity[1] + '\\n"\n')
        (fake / 'go').chmod(0o755)
        run([*check, str(fake.parent), *identity, str(args.pkg_admin)], success=False)
    print('PASS: seed-free source phase, native build/test, cross routing/refusal, bootstrap identity/refusals')


if __name__ == '__main__':
    main()
