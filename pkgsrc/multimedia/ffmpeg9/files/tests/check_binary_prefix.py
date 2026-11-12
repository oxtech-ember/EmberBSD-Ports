#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Qualify FFmpeg binaries while preserving exact diagnostic configuration."""
import argparse
import ast
import re
import subprocess
import tempfile
from pathlib import Path

THIN_MACHO = (b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe',
              b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe')
FAT_MACHO = (b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
             b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca')
CONTROLS = {'+CONTENTS', '+COMMENT', '+DESC', '+BUILD_INFO', '+BUILD_VERSION',
            '+INSTALL', '+DEINSTALL', '+MTREE_DIRS', '+DISPLAY', '+SIZE_PKG', '+SIZE_ALL'}


def run(argv):
    return subprocess.run([str(arg) for arg in argv], check=True,
                          capture_output=True, text=True).stdout


def disjoint(ranges, label):
    ordered = sorted(ranges)
    for (start, end), (next_start, _) in zip(ordered, ordered[1:]):
        if next_start < end:
            raise ValueError(f'overlapping ranges: {label}')


def macho_ranges(path, data, config, readobj):
    output = run([readobj, '--sections', path])
    sections = re.findall(r'  Section \{\n(.*?)\n  \}', output, re.S)
    if not sections:
        raise ValueError(f'no Mach-O sections: {path}')
    section_ranges = []
    matches = []
    for section in sections:
        section_type = re.search(r'^    Type: (\w+) \(0x([0-9A-Fa-f]+)\)$', section, re.M)
        if not section_type:
            raise ValueError(f'missing section type: {path}')
        offset = re.search(r'^    Offset: (\d+)$', section, re.M)
        size = re.search(r'^    Size: 0x([0-9A-Fa-f]+)$', section, re.M)
        if not offset or not size:
            raise ValueError(f'incomplete section: {path}')
        start = int(offset.group(1))
        end = start + int(size.group(1), 16)
        kind = int(section_type.group(2), 16)
        if kind in (0x1, 0xc, 0x12):  # zero-fill sections occupy no file bytes
            continue
        if end > len(data):
            raise ValueError(f'out-of-bounds section: {path}')
        if end > start:
            section_ranges.append((start, end))
        if kind != 0x2:
            continue
        position = 0
        for value in data[start:end].split(b'\0'):
            if value == config and position + len(value) < end - start:
                matches.append((start + position, start + position + len(value)))
            position += len(value) + 1
    disjoint(section_ranges, path)
    disjoint(matches, path)
    return matches


def validate_positions(data, prefix, config, ranges, label):
    disjoint(ranges, label)
    positions = [m.start() for m in re.finditer(re.escape(prefix), data)]
    if not ranges or any(not any(start <= pos and pos + len(prefix) <= end
                                 for start, end in ranges) for pos in positions):
        raise ValueError(f'unqualified prefix: {label}')
    if len(positions) != len(ranges) * config.count(prefix):
        raise ValueError(f'incomplete prefix accounting: {label}')


def archive_ranges(path, data, config, ar, readobj, tmp):
    offsets = []
    for row in run([ar, 'tO', path]).splitlines():
        try:
            name, value = row.rsplit(' ', 1)
            offset = int(value, 16)
        except ValueError as exc:
            raise ValueError(f'invalid archive listing: {path}') from exc
        if name == 'version.o':
            offsets.append(offset)
    matches = []
    members = []
    for instance, offset in enumerate(offsets, 1):
        directory = tmp / str(instance)
        directory.mkdir()
        run([ar, '--output', directory, 'xN', str(instance), path, 'version.o'])
        member = directory / 'version.o'
        body = member.read_bytes()
        end = offset + len(body)
        if offset < 0 or end > len(data) or data[offset:end] != body:
            raise ValueError(f'archive member mismatch: {path}')
        members.append((offset, end))
        if not body.startswith(THIN_MACHO):
            raise ValueError(f'version.o is not thin Mach-O: {path}')
        matches.extend((offset + start, offset + stop)
                       for start, stop in macho_ranges(member, body, config, readobj))
        member.unlink()
        directory.rmdir()
    disjoint(members, path)
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--config-h', type=Path, required=True)
    parser.add_argument('--producer-prefix', required=True)
    parser.add_argument('--llvm-ar', type=Path, required=True)
    parser.add_argument('--llvm-readobj', type=Path, required=True)
    args = parser.parse_args()
    for tool in (args.llvm_ar, args.llvm_readobj):
        if not tool.is_absolute() or not tool.is_file():
            parser.error('select absolute LLVM tools')
    line = next((v for v in args.config_h.read_text().splitlines()
                 if v.startswith('#define FFMPEG_CONFIGURATION ')), None)
    if line is None:
        parser.error('missing FFMPEG_CONFIGURATION')
    config = ast.literal_eval(line.split(' ', 2)[2]).encode()
    prefix = args.producer_prefix.encode()
    if not prefix.startswith(b'/') or prefix not in config or b'\0' in config:
        parser.error('invalid producer/configuration')
    seen = 0
    with tempfile.TemporaryDirectory(prefix='ffmpeg-prefix-check-') as directory:
        tmp = Path(directory)
        for path in args.payload.rglob('*'):
            if path.is_symlink() or not path.is_file():
                continue
            if path.parent == args.payload and path.name in CONTROLS:
                continue
            data = path.read_bytes()
            if prefix not in data:
                continue
            if data.startswith(b'!<arch>\n'):
                ranges = archive_ranges(path, data, config, args.llvm_ar, args.llvm_readobj, tmp)
            elif data.startswith(THIN_MACHO):
                ranges = macho_ranges(path, data, config, args.llvm_readobj)
            elif data.startswith(FAT_MACHO) or b'\0' in data:
                raise ValueError(f'unknown or fat binary contains producer prefix: {path}')
            else:
                try:
                    data.decode('utf-8')
                except UnicodeDecodeError as exc:
                    raise ValueError(f'unknown binary: {path}') from exc
                continue  # SDK separately requires and verifies text relocation.
            validate_positions(data, prefix, config, ranges, path)
            seen += len(ranges)
    if not seen:
        raise ValueError('diagnostic configuration absent')
    print(f'PASS: {seen} exact diagnostic configurations, no other binary prefix')


if __name__ == '__main__':
    main()
