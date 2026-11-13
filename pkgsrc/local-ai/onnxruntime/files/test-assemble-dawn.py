#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise reproducibility and refusal with small synthetic source archives."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile


def run(bsdtar):
    tool = Path(__file__).with_name('assemble-dawn.py')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inputs = root / 'inputs'
        inputs.mkdir()
        dawn = inputs / 'dawn.zip'
        long_path = '/'.join(['long-segment-' + str(i) * 40 for i in range(6)]) + '/source.txt'
        long_content = b'long PAX path payload\n'
        assert len('dawn-20260916.214021/' + long_path) > 255
        with zipfile.ZipFile(dawn, 'w') as archive:
            archive.writestr('dawn-pin/LICENSE', 'Dawn license\n')
            archive.writestr('dawn-pin/' + long_path, long_content)
        dependency = inputs / 'dep.tar.gz'

        def make_input(mtime):
            with dependency.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=mtime) as gz:
                with tarfile.open(fileobj=gz, mode='w|') as archive:
                    content = b'upstream source\n'
                    info = tarfile.TarInfo('source.txt')
                    info.mode = 0o644
                    info.mtime = mtime
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))

        data_hash = hashlib.sha256(b'upstream source\n').hexdigest()
        tree_hash = hashlib.sha256(f'source.txt\0' '644\0' f'{data_hash}\n'.encode()).hexdigest()
        manifest = {'format': 1,
                    'dawn': {'filename': 'dawn.zip', 'sha256': hashlib.sha256(dawn.read_bytes()).hexdigest()},
                    'dependencies': [{'filename': 'dep.tar.gz', 'path': 'third_party/dep',
                                      'tree_sha256': tree_hash}]}
        manifest_path = root / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest))
        first, second = root / 'first.tar.gz', root / 'second.tar.gz'
        command = [sys.executable, str(tool), '--manifest', str(manifest_path), '--inputs', str(inputs)]
        make_input(1)
        subprocess.run([*command, '--output', str(first)], check=True, stdout=subprocess.DEVNULL)
        make_input(2)
        subprocess.run([*command, '--output', str(second)], check=True, stdout=subprocess.DEVNULL)
        assert first.read_bytes() == second.read_bytes()
        extracted = root / 'extracted'
        extracted.mkdir()
        subprocess.run([str(bsdtar), '-xzf', str(first), '-C', str(extracted)], check=True)
        assert (extracted / 'dawn-20260916.214021' / long_path).read_bytes() == long_content
        manifest['dependencies'][0]['tree_sha256'] = '0' * 64
        manifest_path.write_text(json.dumps(manifest))
        rejected = subprocess.run([*command, '--output', str(second)], capture_output=True)
        assert rejected.returncode != 0 and b'tree SHA-256 mismatch' in rejected.stderr
        assert first.read_bytes() == second.read_bytes()
    print('Dawn source assembly: reproducibility, PAX extraction and refusal passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bsdtar', type=Path, required=True,
                        help='absolute path to bsdtar in the selected native Ports prefix')
    args = parser.parse_args()
    if not args.bsdtar.is_absolute() or not args.bsdtar.is_file():
        parser.error('--bsdtar must name an existing absolute executable')
    run(args.bsdtar)
