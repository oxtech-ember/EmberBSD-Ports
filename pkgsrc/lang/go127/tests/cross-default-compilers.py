#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the compiler defaults that a cross-built Go toolchain records.

cmd/dist writes CC_FOR_TARGET, CXX_FOR_TARGET and PKG_CONFIG into
cmd/go/internal/cfg/zdefaultcc.go and cmd/cgo/zdefaultcc.go, and with
CC_FOR_TARGET set it also records the build host's CC under
gohostos/gohostarch. A cross-built toolchain then named the cross compiler,
the build host's clang and the work-directory pkg-config wrapper, which do
not exist on the target (CHECK_WRKREF stopped the package).

The recipe passes target command names (tests/native-routing.py checks
that). This test runs the patched cmd/dist from the real recipe source and
checks that it leaves the build host compiler out of zdefaultcc.go for a
cross-built toolchain, both in cmdbootstrap's host phase
(cmd/go/internal/cfg, compiled into go_bootstrap and the installed cmd/go)
and in bootstrapBuildTools (cmd/cgo), keeps an explicit CC_FOR_<host>
setting, and is unchanged for a native toolchain.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

DIST_TEST = r'''package main

import (
	"os"
	"path/filepath"
	"testing"
)

// emberZDefault computes the compiler maps for target as cmd/dist does at
// startup, then writes zdefaultcc.go while goos names phase. cmdbootstrap
// writes cmd/go/internal/cfg in its host phase (goos is the build host and
// oldgoos the target); bootstrapBuildTools writes cmd/cgo before oldgoos is
// set.
func emberZDefault(t *testing.T, target, phase, old string, env map[string]string) string {
	for _, k := range []string{"CC", "CXX", "CC_FOR_TARGET", "CXX_FOR_TARGET",
		"CC_FOR_darwin_arm64", "CXX_FOR_darwin_arm64"} {
		t.Setenv(k, "")
	}
	for k, v := range env {
		t.Setenv(k, v)
	}
	gohostos, gohostarch, goos, goarch = "darwin", "arm64", target, "arm64"
	oldgoos, oldgoarch = "", ""
	defaultcc = compilerEnv("CC", "")
	defaultcxx = compilerEnv("CXX", "")
	defaultpkgconfig = "pkg-config"
	goos = phase
	if old != "" {
		oldgoos, oldgoarch = old, "arm64"
	}
	file := filepath.Join(t.TempDir(), "go", "internal", "cfg", "zdefaultcc.go")
	if err := os.MkdirAll(filepath.Dir(file), 0o755); err != nil {
		t.Fatal(err)
	}
	mkzdefaultcc(filepath.Dir(file), file)
	data, err := os.ReadFile(file)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("EMBER_RESULT")+"."+t.Name(), data, 0o644); err != nil {
		t.Fatal(err)
	}
	return string(data)
}

var emberCross = map[string]string{
	"CC": "/build/host/bin/clang", "CXX": "/build/host/bin/clang++",
	"CC_FOR_TARGET": "clang", "CXX_FOR_TARGET": "clang++"}

func TestEmberCrossBootstrap(t *testing.T) { emberZDefault(t, "netbsd", "darwin", "netbsd", emberCross) }

func TestEmberCrossTools(t *testing.T) { emberZDefault(t, "netbsd", "netbsd", "", emberCross) }

func TestEmberExplicitHost(t *testing.T) {
	emberZDefault(t, "netbsd", "darwin", "netbsd", map[string]string{
		"CC": "/build/host/bin/clang", "CC_FOR_TARGET": "clang",
		"CC_FOR_darwin_arm64": "host-cc"})
}

func TestEmberNative(t *testing.T) {
	emberZDefault(t, "darwin", "darwin", "darwin", map[string]string{"CC": "clang", "CXX": "clang++"})
}
'''


def run(argv, **kwargs):
    proc = subprocess.run(argv, capture_output=True, text=True, **kwargs)
    if proc.returncode:
        sys.exit('FAIL: %s\n%s%s' % (' '.join(map(str, argv)), proc.stdout[-3000:], proc.stderr[-3000:]))
    return proc.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', required=True,
                        help='Ports make command for a cross build: PKGPATH, then bmake arguments')
    parser.add_argument('--go', type=Path, required=True, help='Go command for the build host')
    args = parser.parse_args()
    recipe = Path(__file__).resolve().parent.parent
    problems = []
    with tempfile.TemporaryDirectory(prefix='go-zdefaultcc-') as temporary:
        work = Path(temporary).resolve()
        # The patched cmd/dist of the real recipe source.
        make = [args.make, 'lang/go127', 'WRKOBJDIR=' + str(work / 'objects')]
        wrksrc = Path(run([*make, '-V', '${WRKSRC}']).strip())
        run([*make, 'patch'])
        dist = work / 'dist'
        dist.mkdir()
        for source in (wrksrc / 'src/cmd/dist').iterdir():
            if source.suffix in ('.go', '.s') and not source.name.endswith('_test.go'):
                shutil.copyfile(source, dist / source.name)
        (dist / 'go.mod').write_text('module dist\n\ngo 1.24\n')
        (dist / 'ember_zdefaultcc_test.go').write_text(DIST_TEST)
        prefix = work / 'zdefaultcc'
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(work), 'GOENV': 'off', 'GOTOOLCHAIN': 'local',
               'GOFLAGS': '-mod=mod', 'GOCACHE': str(work / 'cache'), 'GOPATH': str(work / 'gopath'),
               'CGO_ENABLED': '0', 'EMBER_RESULT': str(prefix)}
        run([str(args.go), 'test', '-count=1', '-run', '^TestEmber', '.'], cwd=dist, env=env)
        for phase in ('Bootstrap', 'Tools'):
            cross = Path(str(prefix) + '.TestEmberCross' + phase).read_text()
            if '/build/host' in cross or 'darwin/arm64' in cross:
                problems.append('cross toolchain (%s phase) records the build host compiler:\n%s' % (phase, cross))
            if cross.count('return "clang"') != 1 or cross.count('return "clang++"') != 1:
                problems.append('cross toolchain (%s phase) lacks the target defaults:\n%s' % (phase, cross))
        explicit = Path(str(prefix) + '.TestEmberExplicitHost').read_text()
        native = Path(str(prefix) + '.TestEmberNative').read_text()
        if 'case "darwin/arm64":\n\t\treturn "host-cc"' not in explicit or '/build/host' in explicit:
            problems.append('explicit CC_FOR_darwin_arm64 not kept:\n' + explicit)
        if 'case ' in native or native.count('return "clang"') != 1:
            problems.append('native toolchain defaults changed:\n' + native)
    if problems:
        print('FAIL: ' + '\n'.join(problems))
        return 1
    print('PASS: cross Go records clang, clang++ and pkg-config without build-host paths')
    return 0


if __name__ == '__main__':
    sys.exit(main())
