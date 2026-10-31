# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Bounded tests for the S31 NOR image input geometry checks."""
import sys
sys.dont_write_bytecode = True
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

producer = Path(__file__).resolve().parents[1] / 'files/board/espressif/esp32s31/make-nor-image.py'
spec = importlib.util.spec_from_file_location('nor_image', producer)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def rom():
    payload = b'valid test data!'
    head = bytearray(24)
    struct.pack_into('<BBBBI', head, 0, 0xe9, 1, 2, 0x40, 0x2f040000)
    struct.pack_into('<H', head, 12, 32)
    head[23] = 1
    image = head + struct.pack('<II', 0x2f040000, len(payload)) + payload
    checksum = 0xef
    for value in payload:
        checksum ^= value
    image.extend(bytes((15 - len(image) % 16)))
    image.append(checksum)
    image.extend(hashlib.sha256(image).digest())
    return bytes(image)


class NorInputs(unittest.TestCase):
    def test_mkimage_prefix_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve(); prefix = root/'prefix'; prefix.mkdir()
            inside = prefix/'mkimage'; inside.write_bytes(b'test')
            outside = root/'other'; outside.write_bytes(b'test')
            link = prefix/'link'; link.symlink_to(outside)
            self.assertEqual(m.resolve_mkimage(inside, prefix), inside)
            with self.assertRaises(ValueError): m.resolve_mkimage(outside, prefix)
            with self.assertRaises(ValueError): m.resolve_mkimage(link, prefix)

    def test_rom_header_and_checksum(self):
        data = rom()
        m.validate_rom(data)
        for offset, value in ((2, 0), (3, 0), (12, 31), (27, 0)):
            bad = bytearray(data); bad[offset] = value
            with self.assertRaises(ValueError):
                m.validate_rom(bytes(bad))

    def test_digest_flag_is_required_even_with_matching_trailer(self):
        data = bytearray(rom())
        data[23] = 0
        data[-32:] = hashlib.sha256(data[:-32]).digest()
        with self.assertRaises(ValueError): m.validate_rom(bytes(data))

    def test_rom_entry_and_segments_fit_sram(self):
        data = bytearray(rom()); struct.pack_into('<I', data, 4, 0x2f080000)
        data[-32:] = hashlib.sha256(data[:-32]).digest()
        with self.assertRaises(ValueError):
            m.validate_rom(bytes(data))

    def test_spl_segment_ends_before_bss(self):
        data = bytearray(rom())
        size = struct.unpack_from('<I', data, 28)[0]
        start = 0x2f050000 - size
        struct.pack_into('<I', data, 4, start)
        struct.pack_into('<I', data, 24, start)
        data[-32:] = hashlib.sha256(data[:-32]).digest()
        m.validate_rom(bytes(data))
        struct.pack_into('<I', data, 4, start + 1)
        struct.pack_into('<I', data, 24, start + 1)
        data[-32:] = hashlib.sha256(data[:-32]).digest()
        with self.assertRaises(ValueError): m.validate_rom(bytes(data))

    def test_elf_extent_includes_bss(self):
        data = bytearray(128)
        struct.pack_into('<16sHHIIIIIHHHHHH', data, 0, b'\x7fELF\x01\x01\x01', 2, 243, 1, 0x50400000, 52, 0, 1, 52, 32, 1, 0, 0, 0)
        struct.pack_into('<8I', data, 52, 1, 84, 0x50400000, 0x50400000, 44, 0x2efb0, 7, 4)
        self.assertEqual(m.elf_extent(data), 0x5042efb0)
        struct.pack_into('<I', data, 72, 0x30001)
        with self.assertRaises(ValueError):
            m.elf_extent(data)


if __name__ == '__main__':
    unittest.main()
