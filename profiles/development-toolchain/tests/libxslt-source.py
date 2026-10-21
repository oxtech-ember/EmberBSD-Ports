#!/usr/bin/env python3
"""Check the exported libxslt recipe and ordinary pkgsrc patch digests."""
import hashlib
import pathlib
import re
import sys
p = pathlib.Path(sys.argv[1]) / 'textproc/libxslt'
make = (p/'Makefile').read_text()
common = (p/'Makefile.common').read_text()
assert re.search(r'^DISTNAME=\s*libxslt-1\.1\.45$', common, re.M)
assert re.search(r'^PKGREVISION=\s*1$', make, re.M)
assert re.search(r'^BUILDLINK_API_DEPENDS\.libxml2\+=\s*libxml2>=2\.15\.4$', make, re.M)
dist = (p/'distinfo').read_text()
patches = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([a-f0-9]+)$', dist, re.M)
assert len(patches) == 7, patches
for name, expected in patches:
    data = (p/'patches'/name).read_bytes()
    filtered = b''.join(l for l in data.splitlines(keepends=True)
                        if b'$NetBSD' not in l)
    assert hashlib.sha1(filtered).hexdigest() == expected, name
assert 'CHECK_VULNERABILITIES' not in make and 'IGNORE' not in make
print('PASS: libxslt recipe version, paired dependency and seven patch digests')
