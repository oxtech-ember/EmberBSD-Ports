#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check that a prepared pkgsrc export satisfies its own dependency patterns.

For each selected package, bmake reports its PKGNAME and the expanded
DEPENDS, BUILD_DEPENDS, TEST_DEPENDS, TOOL_DEPENDS and BOOTSTRAP_DEPENDS
entries. Buildlink API patterns are part of these entries. Each pattern must
match the PKGNAME of the provider directory in the same export, as native
pkg_admin pmatch decides. An empty package database is used, so installed
packages cannot hide a gap. Any unsatisfied pattern, missing provider or
failed query is a finding, and the check exits 1.
"""
import argparse
import concurrent.futures
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

SAME_ROLE = ('DEPENDS', 'BUILD_DEPENDS', 'TEST_DEPENDS')
HOST_ROLE = ('TOOL_DEPENDS', 'BOOTSTRAP_DEPENDS')
QUERY = ('PKGNAME',) + SAME_ROLE + HOST_ROLE + ('PKG_FAIL_REASON', 'PKG_SKIP_REASON',
                                                 'CROSSTARGETSETTINGS')
HOST_FACT = re.compile(r'(OSX|NATIVE)_[A-Z0-9_]+=')
NOT_PACKAGES = {'bootstrap', 'doc', 'licenses', 'mk', 'regress', 'templates', 'wip'}


def sort_key(node):
    return node[0], node[1], node[2] or '', node[3]


class Checker:
    def __init__(self, args):
        self.root = args.pkgsrc.resolve(strict=True)
        self.makeconf = args.makeconf.resolve(strict=True)
        self.bmake = args.bmake.resolve(strict=True)
        self.pkg_admin = args.pkg_admin.resolve(strict=True)
        self.work = args.work
        self.timeout = args.timeout
        self.cross = args.mode == 'cross'
        self.pkgdb = self.work / 'empty-pkgdb'
        self.pkgdb.mkdir()
        # Ambient make and compiler variables must not change the result.
        self.environment = {key: os.environ[key] for key in ('PATH', 'HOME', 'TMPDIR')
                            if key in os.environ}
        self.environment['LC_ALL'] = 'C'
        self.lock = threading.Lock()
        self.nodes = {}
        self.makeflags = False
        self.queries = 0
        self.matches = {}
        self.findings = []
        self.rejected = []

    def packages(self, roots):
        if roots:
            return sorted(set(roots))
        found = []
        for makefile in self.root.glob('*/*/Makefile'):
            category = makefile.parent.parent.name
            if category not in NOT_PACKAGES and not category.startswith('.'):
                found.append(makefile.parent.relative_to(self.root).as_posix())
        return sorted(found)

    def base_command(self, path, role, settings):
        command = [str(self.bmake), '-C', str(self.root / path),
                   'MAKECONF=' + str(self.makeconf), 'PKG_DBDIR=' + str(self.pkgdb),
                   'USE_CROSS_COMPILE=' + role]
        # A cross package passes its target settings to host tool builds.
        return command + settings.split()

    def platform(self, path):
        """Return the build-host facts that bsd.prefs.mk caches in MAKEFLAGS.

        pkgsrc passes MAKEFLAGS to the dependency builds that it starts, so
        that each recursive make does not probe the build host again. On macOS
        each probe starts xcrun, so a query takes many seconds. Only the facts
        about the build host (OSX_* and NATIVE_*) are reused: they are the same
        for every package and role. Platform values such as OPSYS can differ
        between packages (the cross/* packages set them from the target), so
        each query still computes them.
        """
        command = self.base_command(path, 'no', '') + ['-V', '${MAKEFLAGS}']
        try:
            completed = subprocess.run(command, env=self.environment, text=True,
                                       capture_output=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return None
        lines = completed.stdout.splitlines()
        if completed.returncode or len(lines) != 1:
            return None
        # MAKEFLAGS escapes a space in a value with a backslash.
        words = re.findall(r'(?:\\.|[^ \\])+', lines[0])
        return ' '.join(w for w in words if HOST_FACT.match(w)) or None

    def query(self, node):
        path, role, required, settings = node
        command = self.base_command(path, role, settings)
        if required:
            command.append('PKGNAME_REQD=' + required)
        for variable in QUERY:
            command += ['-V', '${' + variable + '}']
        environment = dict(self.environment)
        flags = self.makeflags
        if flags:
            environment['MAKEFLAGS'] = flags
        try:
            completed = subprocess.run(command, env=environment, text=True,
                                       capture_output=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return None, 'bmake timed out'
        with self.lock:
            self.queries += 1
            if self.queries % 500 == 0:
                print('%d bmake queries' % self.queries, file=sys.stderr, flush=True)
        lines = completed.stdout.splitlines()
        if completed.returncode or len(lines) != len(QUERY):
            return None, (completed.stderr.strip().splitlines() or ['bmake failed'])[-1][:300]
        result = dict(zip(QUERY, lines))
        if not result['PKGNAME']:
            return None, 'empty PKGNAME'
        return result, None

    def pmatch(self, pattern, name):
        key = (pattern, name)
        if key not in self.matches:
            completed = subprocess.run([str(self.pkg_admin), 'pmatch', pattern, name],
                                       env=self.environment, capture_output=True,
                                       timeout=self.timeout)
            self.matches[key] = completed.returncode == 0
        return self.matches[key]

    def provider(self, consumer, entry):
        pattern, separator, directory = entry.rpartition(':')
        if not separator or not pattern or not directory:
            return pattern or entry, None, 'malformed dependency entry'
        candidate = (self.root / consumer / directory).resolve()
        try:
            relative = candidate.relative_to(self.root)
        except ValueError:
            return pattern, None, 'provider outside the export: ' + directory
        if len(relative.parts) != 2 or not (candidate / 'Makefile').is_file():
            return pattern, None, 'missing provider: ' + directory
        return pattern, relative.as_posix(), None

    def query_all(self, pool, nodes):
        nodes = sorted(set(nodes) - self.nodes.keys(), key=sort_key)
        # A failed host query leaves MAKEFLAGS unset: slower, same result.
        if nodes and self.makeflags is False:
            self.makeflags = self.platform(nodes[0][0])
        for node, outcome in zip(nodes, pool.map(self.query, nodes)):
            self.nodes[node] = outcome

    def expand(self, node, checks):
        path, role, required, settings = node
        label = ('target:' if role == 'yes' else 'host:') + path
        result, error = self.nodes[node]
        if error:
            self.findings.append(('query-failed', label, '', required or '', '', error))
            return
        for reason in ('PKG_FAIL_REASON', 'PKG_SKIP_REASON'):
            if result[reason]:
                self.rejected.append((label, result['PKGNAME'], reason, result[reason]))
        for kind in SAME_ROLE + HOST_ROLE:
            provider_role = 'no' if kind in HOST_ROLE else role
            provider_settings = settings
            if kind in HOST_ROLE and role == 'yes':
                provider_settings = result['CROSSTARGETSETTINGS']
            for entry in result[kind].split():
                pattern, provider, problem = self.provider(path, entry)
                if problem:
                    self.findings.append(('missing', label, kind, pattern, '', problem))
                else:
                    checks.append((label, kind, pattern, provider, provider_role,
                                   provider_settings))

    def run(self, roots, jobs):
        role = 'yes' if self.cross else 'no'
        queue = {(path, role, None, '') for path in self.packages(roots)}
        expanded = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            while queue:
                self.query_all(pool, queue)
                checks = []
                for node in sorted(queue, key=sort_key):
                    expanded.add(node)
                    self.expand(node, checks)
                plain = {(c[3], c[4], None, c[5]) for c in checks}
                self.query_all(pool, plain)
                # A multi-version provider gets the requested pattern as
                # PKGNAME_REQD, as the pkgsrc dependency installer does.
                variants = set()
                for label, kind, pattern, provider, provider_role, settings in checks:
                    result, error = self.nodes[(provider, provider_role, None, settings)]
                    if not error and not self.pmatch(pattern, result['PKGNAME']):
                        variants.add((provider, provider_role, pattern, settings))
                self.query_all(pool, variants)
                used = set(plain)
                for label, kind, pattern, provider, provider_role, settings in checks:
                    result, error = self.nodes[(provider, provider_role, None, settings)]
                    if error or self.pmatch(pattern, result['PKGNAME']):
                        continue
                    variant = (provider, provider_role, pattern, settings)
                    vresult, verror = self.nodes[variant]
                    if not verror and self.pmatch(pattern, vresult['PKGNAME']):
                        used.add(variant)
                        continue
                    side = 'target:' if provider_role == 'yes' else 'host:'
                    provided = result['PKGNAME'] + (' (with PKGNAME_REQD: %s)' % (
                        vresult['PKGNAME'] if vresult else verror))
                    self.findings.append(('unsatisfied', label, kind, pattern,
                                          side + provider, provided))
                queue = used - expanded
                print('checked %d packages, %d findings, %d queued' % (
                    len(expanded), len(self.findings), len(queue)), file=sys.stderr, flush=True)

    def write(self):
        findings = sorted(set(self.findings))
        with open(self.work / 'findings.tsv', 'w') as stream:
            stream.write('finding\tconsumer\tkind\tpattern\tprovider\tdetail\n')
            for row in findings:
                stream.write('\t'.join(row) + '\n')
        with open(self.work / 'rejected.tsv', 'w') as stream:
            stream.write('package\tpkgname\treason\ttext\n')
            for row in sorted(set(self.rejected)):
                stream.write('\t'.join(row) + '\n')
        return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', required=True, type=Path, help='prepared export')
    parser.add_argument('--makeconf', required=True, type=Path)
    parser.add_argument('--bmake', required=True, type=Path)
    parser.add_argument('--pkg-admin', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path, help='new directory for results')
    parser.add_argument('--mode', choices=('cross', 'native'), default='cross')
    parser.add_argument('--root', action='append', default=[],
                        help='category/package; repeat; default is every package')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--timeout', type=int, default=300, help='seconds per command')
    args = parser.parse_args()
    if not args.work.is_absolute():
        parser.error('--work must be an absolute path')
    args.work.mkdir()
    checker = Checker(args)
    checker.run(args.root, args.jobs)
    findings = checker.write()
    checked = sum(1 for node in checker.nodes if node[2] is None)
    for row in findings:
        print('\t'.join(row))
    if findings:
        print('FAIL: %d dependency findings in %d checked packages; see %s'
              % (len(findings), checked, args.work / 'findings.tsv'), file=sys.stderr)
        return 1
    print('PASS: every dependency pattern of %d checked packages matches its exported provider'
          % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
