#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Preserve indexed padding and shared TU tables.
import os
from pathlib import Path
import shutil
import struct
import sys
sys.dont_write_bytecode = True
from llvm_host import load_sdk, query, log_run


def sections(path):
    from emberbsd_sdk.elf import parse_elf_header
    elf = Path(path).read_bytes()
    if parse_elf_header(elf) is None:
        raise ValueError('Expected ELF64 little endian input')
    table = struct.unpack_from('<Q', elf, 40)[0]
    width, count, strings = struct.unpack_from('<HHH', elf, 58)
    if width < 64 or not count or strings >= count or table + count * width > len(elf):
        raise ValueError('Invalid DWP section table')
    headers = [elf[table + i * width:table + (i + 1) * width] for i in range(count)]

    def payload(header):
        start, size = struct.unpack_from('<QQ', header, 24)
        if start + size > len(elf):
            raise ValueError('DWP section exceeds file')
        return elf[start:start + size]

    names = payload(headers[strings])
    result = {}
    for header in headers:
        start = struct.unpack_from('<I', header)[0]
        end = names.find(b'\0', start)
        if start >= len(names) or end < 0:
            raise ValueError('Invalid DWP section name')
        result[names[start:end].decode()] = payload(header)
    return result


def rewrite_index(data, update):
    if len(data) < 16 or len(data) % 4:
        raise ValueError('Invalid DWP index size')
    words = list(struct.unpack('<' + 'I' * (len(data) // 4), data))
    version, columns, units, slots = words[:4]
    ids = 4 + slots * 3
    if ids + columns + 2 * columns * units > len(words):
        raise ValueError('DWP index tables exceed section')
    if 6 not in words[ids:ids + columns]:
        return data
    column = words[ids:ids + columns].index(6)
    offsets, sizes = ids + columns, ids + columns + columns * units
    for row in range(units):
        pos = row * columns + column
        offset, length = words[offsets + pos], words[sizes + pos]
        if length:
            words[offsets + pos] = update(offset, length)
    return struct.pack('<' + 'I' * len(words), *words)


def prepare(args):
    if len(args) != 3:
        raise ValueError('Use ACCEPTED_RESULTS SOURCE_FIXTURES NEW_WORK')
    results, fixtures, output = map(os.path.abspath, args)
    os.mkdir(output)
    cc, objcopy = os.environ['CC'], os.environ['OBJCOPY']
    if query([cc, '-dumpfullversion']) != '16.2.0' or query([cc, '-dumpmachine']) not in ('aarch64--netbsd', 'x86_64--netbsd'):
        raise ValueError('Common GCC16 target compiler required')
    log_run(output + '/empty.log', [cc, '-x', 'assembler', '-c', '/dev/null', '-o', output + '/empty.o'])
    with open(output + '/cases.tsv', 'w') as cases:
        for line in Path(fixtures, 'cases.tsv').read_text().splitlines(keepends=True):
            name, version, types = line.split()
            directory = Path(output, name)
            directory.mkdir()
            source = Path(results, name, 'input.dwp')
            data = sections(source)
            original = data['.debug_str_offsets.dwo']
            strings = bytearray(b'\xa5' * 16 + original)
            updates = {'.debug_cu_index': rewrite_index(data['.debug_cu_index'], lambda offset, length: offset + 16)}
            if '.debug_tu_index' in data:
                aliases = {}

                def update(offset, length):
                    key = offset, length
                    if key not in aliases:
                        if offset + length > len(original):
                            raise ValueError('DWP string contribution exceeds section')
                        strings.extend(b'\xa5' * 8)
                        aliases[key] = len(strings)
                        strings.extend(original[offset:offset + length])
                    return aliases[key]

                updates['.debug_tu_index'] = rewrite_index(data['.debug_tu_index'], update)
            strings.extend(b'\xa5' * 7)
            updates['.debug_str_offsets.dwo'] = strings
            command = [objcopy]
            for section, data in updates.items():
                path = directory / (section + '.bin')
                path.write_bytes(data)
                command.extend(['--update-section', section + '=' + str(path)])
            log_run(directory / 'update.log', command + [str(source), str(directory / 'program.dwp')])
            shutil.copyfile(Path(fixtures, name, 'program'), directory / 'program')
            cases.write(line)
    print('Prepared indexed padding, shared tables and independent TU contributions.')


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        prepare(args)
    except Exception as error:
        exit_error(error)
