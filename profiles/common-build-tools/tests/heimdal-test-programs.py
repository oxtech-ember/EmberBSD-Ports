#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check Heimdal test selectors while preserving installed programs and generators."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True, help='upstream-patched Heimdal source')
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--gmake', type=Path, required=True)
p.add_argument('--patch', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
recipe = root/'pkgsrc/security/heimdal'
patch = recipe/'patches/patch-zz-optional-test-programs'
expected = re.search(r'^SHA1 \(patch-zz-optional-test-programs\) = ([a-f0-9]+)$',
                     (recipe/'distinfo').read_text(), re.M)
if not expected or hashlib.sha1(patch.read_bytes()).hexdigest() != expected.group(1):
    raise SystemExit('Heimdal patch digest differs')
dirs = ('lib/roken', 'lib/krb5', 'lib/gssapi', 'lib/hcrypto', 'lib/hdb',
        'lib/kadm5', 'lib/otp', 'kdc', 'kadmin')
paths = [sub+'/Makefile.'+ext for sub in dirs for ext in ('am', 'in')]
paths += [sub+'Makefile.'+ext for sub in ('', 'appl/') for ext in ('am', 'in')]
with tempfile.TemporaryDirectory(prefix='heimdal-options-', dir=a.work_parent) as work:
    w = Path(work)
    for name in paths:
        target = w/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((a.source/name).read_bytes())
    with patch.open('rb') as inp:
        subprocess.run([str(a.patch), '-s', '-p0', '-d', str(w)], stdin=inp, check=True)
    source = (recipe/'options.mk').read_text()
    source = '\n'.join('' if line.lstrip().startswith('.include ') else line
                       for line in source.splitlines())
    for selection, enabled in (('', False), ('tests', True)):
        f = w/'options.mk'
        f.write_text('PKG_OPTIONS='+selection+'\n'+source+
                     '\nshow:\n\t@printf "%s\\n" "${MAKE_FLAGS}" "${TEST_TARGET}"\n')
        r = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(f), 'show'],
                           text=True, capture_output=True)
        if r.returncode:
            raise SystemExit(r.stderr)
        flags, target = r.stdout.splitlines()
        names = ('HEIMDAL_TEST_PROGRAMS=', 'HEIMDAL_TEST_LIBRARIES=',
                 'HEIMDAL_TESTS_DIR=', 'HEIMDAL_APPL_TEST_DIR=', 'HEIMDAL_GSSMASK_DIR=')
        if any((name in flags.split()) == enabled for name in names) or (target == 'check') != enabled:
            raise SystemExit('incorrect Heimdal package selection')
        for sub in dirs:
            program_source = (w/sub/'Makefile.in').read_text()
            assignments = [line for line in program_source.splitlines()
                           if line.startswith(('HEIMDAL_TEST_PROGRAMS =', 'noinst_PROGRAMS ='))]
            if len(assignments) != 2:
                raise SystemExit('test program control missing in '+sub)
            f.write_text('EXEEXT =\nam__EXEEXT_1 = make-roken\n'+'\n'.join(assignments)+
                         '\nshow:\n\t@echo $(noinst_PROGRAMS)\n')
            cmd = [str(a.gmake), '-s', '-f', str(f), 'show']
            if not enabled:
                cmd.append('HEIMDAL_TEST_PROGRAMS=')
            value = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.split()
            if enabled and not value:
                raise SystemExit('tests-on programs missing in '+sub)
            if not enabled and value != (['make-roken'] if sub == 'lib/roken' else []):
                raise SystemExit('tests-off program selection changed in '+sub)
    for rel, excluded in (("Makefile.in", {"tests"}), ("appl/Makefile.in", {"test", "gssmask"})):
        lines = (w/rel).read_text().splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("SUBDIRS ="))
        end = start + 1
        while lines[end-1].rstrip().endswith(chr(92)):
            end += 1
        variables = [line for line in lines if line.startswith(
            ("HEIMDAL_TESTS_DIR =", "HEIMDAL_APPL_TEST_DIR =", "HEIMDAL_GSSMASK_DIR ="))]
        f = w/"subdirs.mk"
        f.write_text("kcm_dir = kcm\nam__append_1 = doc\ndir_afsutil = afsutil\ndir_otp = otp\ndir_dce = dceutils\n" +
                     "\n".join(variables + lines[start:end]) + "\nshow:\n\t@echo $(SUBDIRS)\n")
        base = [str(a.gmake), "-s", "-f", str(f), "show"]
        on = subprocess.run(base, capture_output=True, text=True, check=True).stdout.split()
        off = subprocess.run(base + ["HEIMDAL_TESTS_DIR=", "HEIMDAL_APPL_TEST_DIR=", "HEIMDAL_GSSMASK_DIR="],
                             capture_output=True, text=True, check=True).stdout.split()
        if set(on) - set(off) != excluded or set(off) - set(on):
            raise SystemExit("incorrect test-only subdirectory control in " + rel)
    for rel in ('include/Makefile.in', 'lib/com_err/Makefile.in', 'lib/asn1/Makefile.in'):
        if rel in paths:
            raise SystemExit('a required native generator was touched')
print('PASS: Heimdal opt-in test programs and preserved generator selection')
