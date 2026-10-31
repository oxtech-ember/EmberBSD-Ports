#!/usr/bin/env python3
"""Check an ad-hoc Mach-O signature with the selected signer and macOS verifier."""
import argparse
import pathlib
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--cc', required=True, type=pathlib.Path)
p.add_argument('--ldid', required=True, type=pathlib.Path)
p.add_argument('--verifier', required=True, type=pathlib.Path)
a = p.parse_args()
with tempfile.TemporaryDirectory() as directory:
    work = pathlib.Path(directory)
    source = work / 'main.c'
    binary = work / 'main'
    entitlements = work / 'entitlements.plist'
    source.write_text('int main(void) { return 0; }\n')
    entitlements.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.get-task-allow</key><true/></dict></plist>
''')
    subprocess.run([str(a.cc), str(source), '-o', str(binary)], check=True)
    subprocess.run([str(a.ldid), '-r', str(binary)], check=True)
    subprocess.run([str(a.ldid), '-Cadhoc', '-S' + str(entitlements), str(binary)], check=True)
    subprocess.run([str(a.verifier), '--verify', '--strict', str(binary)], check=True)
    requirement = subprocess.run([str(a.verifier), '-d', '-r-', str(binary)],
                                 check=True, capture_output=True, text=True)
    assert 'cdhash' in requirement.stdout + requirement.stderr
    result = subprocess.run([str(a.verifier), '-d', '--entitlements', ':-', str(binary)],
                            check=True, capture_output=True, text=True)
    assert 'com.apple.security.get-task-allow' in result.stdout + result.stderr
    subprocess.run([str(binary)], check=True)
    payload = bytearray(binary.read_bytes())
    payload[4096] ^= 1
    binary.write_bytes(payload)
    result = subprocess.run([str(a.verifier), '--verify', '--strict', str(binary)],
                            capture_output=True)
    assert result.returncode != 0, 'tampered signature was accepted'
print('PASS: ad-hoc signature, cdhash requirement and entitlement')
