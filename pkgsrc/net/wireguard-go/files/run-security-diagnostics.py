#!/usr/bin/env python3
"""Test patched prepared wireguard-go in a disposable copy, never in the source tree."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True, type=Path, help='prepared and patched WRKSRC')
parser.add_argument('--go', required=True, type=Path, help='selected host Go executable')
parser.add_argument('--patch', required=True, type=Path, help='selected patch executable')
parser.add_argument('--work-parent', required=True, type=Path, help='parent for disposable copies')
parser.add_argument('--goproxy', required=True, help='configured trusted Go proxy, e.g. file:///absolute/path')
parser.add_argument('--before', action='store_true', help='reverse the two upstream fixes for causal verification')
a = parser.parse_args()
source = a.source.resolve(strict=True)
go = a.go.resolve(strict=True)
patch_tool = a.patch.resolve(strict=True)
parent = a.work_parent.resolve(strict=True)
recipe = Path(__file__).resolve().parent.parent
if not (source / 'device/noise-protocol.go').is_file() or not (source / 'device/receive.go').is_file():
    parser.error('source must be a prepared wireguard-go tree')
if parent == source or source in parent.parents:
    parser.error('work-parent must be outside source')
with tempfile.TemporaryDirectory(prefix='wireguard-security-', dir=parent) as temp:
    temp = Path(temp)
    dest = temp / 'source'
    shutil.copytree(source, dest, symlinks=True)
    if a.before:
        for patch in ('patch-device_receive.go', 'patch-device_noise-protocol.go'):
            subprocess.run([str(patch_tool), '-p0', '-R', '-i', str(recipe / 'patches' / patch)], cwd=dest, check=True)
    path = dest / 'device/noise-protocol.go'
    text = path.read_text()
    pos = text.index('func (device *Device) ConsumeMessageResponse')
    head, tail = text[:pos], text[pos:]
    marker = '\t// update handshake state\n\n\thandshake.mutex.Lock()'
    if tail.count(marker) != 1:
        raise RuntimeError('unsupported upstream handshake source')
    tail = tail.replace(marker, '\t// Diagnostic-only schedule hook; never installed.\n\tif diagnosticBeforeResponseCommit != nil { diagnosticBeforeResponseCommit() }\n\n' + marker, 1)
    path.write_text(head + tail)
    test = dest / 'device/security_diagnostic_test.go'
    shutil.copyfile(recipe / 'files/security_diagnostic_test.go', test)
    with test.open('a') as stream:
        stream.write('\nvar diagnosticBeforeResponseCommit func()\n')
    env = os.environ.copy()
    env.update(GOPROXY=a.goproxy, GOSUMDB='off', GOTOOLCHAIN='local',
               GOMODCACHE=str(temp / 'gomodcache'), GOCACHE=str(temp / 'gocache'))
    result = subprocess.run([str(go), 'test', './device', '-run',
        '^(TestResponseAfterNewInitiation|TestIPv6OversizedPayloadRejected)$',
        '-count=1', '-timeout=45s'], cwd=dest, env=env)
    raise SystemExit(result.returncode)
