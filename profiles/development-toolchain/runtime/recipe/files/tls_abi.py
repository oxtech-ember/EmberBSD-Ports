# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); bounded GCC16 TLS ABI qualification.
"""Inspect defined dynamic call_once symbols without executing target code."""

import struct

from emberbsd_sdk import elf, paths
from emberbsd_sdk.errors import SDKError

REQUIRED = {'_ZSt11__once_call': 6, '_ZSt15__once_callable': 6, '__once_proxy': 2}
LEGACY = ('_ZSt14__once_functor', '_ZSt23__get_once_functor_lockv',
          '_ZSt27__set_once_functor_lock_ptrPSt11unique_lockISt5mutexE')


def require(condition, message):
    if not condition:
        raise SDKError(message)


def inspect(path, machine):
    """Require exported TLS state and the shared call_once proxy.

    The package keeps an ELF section table after normal stripping. Reject
    absent or ambiguous dynamic symbol tables and all unbounded offsets.
    Legacy non-TLS symbols are reported, not promised by this ABI correction.
    """
    handle, before = paths.open_regular(path)
    with handle:
        def read_at(offset, length):
            require(0 <= offset <= before.st_size and
                    0 <= length <= before.st_size - offset,
                    'TLS ABI table exceeds ELF bounds')
            handle.seek(offset)
            data = handle.read(length)
            require(len(data) == length, 'Truncated TLS ABI table')
            return data

        header = read_at(0, 64)
        record = elf.parse_elf_header(header, machine=machine, required_type=3)
        require(record is not None, 'TLS ABI requires an ELF DSO')
        offset = struct.unpack_from('<Q', header, 40)[0]
        width, count = struct.unpack_from('<HH', header, 58)
        require(width == 64 and 0 < count < 65535 and offset >= 64,
                'Unsupported TLS ABI section table')
        sections = list(struct.iter_unpack('<IIQQQQIIQQ', read_at(offset, width * count)))
        symbols = [row for row in sections if row[1] == 11]
        require(len(symbols) == 1, 'Missing or ambiguous TLS ABI dynamic symbols')
        symbols = symbols[0]
        require(symbols[9] == 24 and symbols[5] % 24 == 0
                and 0 < symbols[5] <= 24 * 262144 and symbols[6] < count,
                'Invalid TLS ABI dynamic symbol table')
        strings = sections[symbols[6]]
        require(strings[1] == 3 and 0 < strings[5] <= 16 * 1024 * 1024,
                'Invalid TLS ABI symbol string table')
        strings = read_at(strings[4], strings[5])
        selected = {}
        watched = {item.encode() for item in (*REQUIRED, *LEGACY)}
        for name, info, visibility, section, value, size in struct.iter_unpack(
                '<IBBHQQ', read_at(symbols[4], symbols[5])):
            require(name < len(strings), 'TLS ABI symbol name exceeds string table')
            end = strings.find(b'\0', name)
            require(end >= name, 'Unterminated TLS ABI symbol name')
            raw = strings[name:end]
            if raw not in watched:
                continue
            name = raw.decode('ascii')
            # Undefined, local, hidden and internal symbols are not exports.
            if section == 0 or info >> 4 not in (1, 2) or visibility & 3 not in (0, 3):
                continue
            require(section < count, 'Invalid TLS ABI export section: ' + name)
            if name in REQUIRED:
                flags = sections[section][2]
                require(bool(flags & (0x400 if REQUIRED[name] == 6 else 4)),
                        'Wrong TLS ABI export section flags: ' + name)
            require(name not in selected, 'Ambiguous TLS ABI export: ' + name)
            selected[name] = info & 15
        for name, kind in REQUIRED.items():
            require(selected.get(name) == kind, 'Missing or wrong TLS ABI export: ' + name)
    paths.verify_stable(path, before)
    return {'required': {name: selected[name] for name in REQUIRED},
            'legacy_exports': sorted(name for name in LEGACY if name in selected),
            'old_non_tls_consumer_compatibility': 'not-qualified; rebuild consumers'}
