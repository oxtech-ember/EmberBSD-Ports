#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause

"""Check that S31 OpenSBI stays out of the supervisor Wi-Fi DMA pool."""

import pathlib
import subprocess
import struct
import sys


FW_BASE = 0x2F000000
WIFI_POOL_BASE = 0x2F030000
PACKED_FIRMWARE_LIMIT = 0x30000
SHT_SYMTAB = 2


def fail(message):
    raise SystemExit(message)


def cstring(table, offset):
    if offset >= len(table):
        fail("invalid ELF string-table reference")
    end = table.find(b"\0", offset)
    if end < 0:
        fail("unterminated ELF string")
    return table[offset:end].decode("ascii")


def read_elf(path):
    data = pathlib.Path(path).read_bytes()
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    ident = header[0]
    if ident[:4] != b"\x7fELF" or ident[4:6] != b"\x01\x01":
        fail("expected a little-endian ELF32 file")
    if header[2] != 243:
        fail("expected a RISC-V ELF")

    shoff, shentsize, shnum, shstrndx = header[6], header[11], header[12], header[13]
    if shentsize != 40 or shstrndx >= shnum:
        fail("invalid ELF section table")
    sections = [struct.unpack_from("<IIIIIIIIII", data, shoff + i * shentsize)
                for i in range(shnum)]
    names_header = sections[shstrndx]
    names = data[names_header[4]:names_header[4] + names_header[5]]
    by_name = {cstring(names, section[0]): section for section in sections}

    symbols = set()
    for section in sections:
        if section[1] != SHT_SYMTAB:
            continue
        strings_header = sections[section[6]]
        strings = data[strings_header[4]:strings_header[4] + strings_header[5]]
        if section[9] != 16:
            fail("invalid ELF32 symbol size")
        for offset in range(section[4], section[4] + section[5], section[9]):
            name, value, size, info, other, shndx = struct.unpack_from("<IIIBBH", data, offset)
            if name:
                symbols.add((cstring(strings, name), value))
    return by_name, symbols


def fdt_value(fdtget, dtb, node, prop, value_type):
    result = subprocess.run((fdtget, "-t", value_type, dtb, node, prop),
                            check=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()


def fdt_children(fdtget, dtb, node):
    result = subprocess.run((fdtget, "-l", dtb, node), check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    return [node.rstrip("/") + "/" + child
            for child in result.stdout.splitlines() if child]


def find_compatible(fdtget, dtb, root, compatible):
    pending = [root]
    matches = []
    while pending:
        node = pending.pop()
        try:
            values = fdt_value(fdtget, dtb, node, "compatible", "s").split()
        except subprocess.CalledProcessError:
            values = []
        if compatible in values:
            matches.append(node)
        pending.extend(fdt_children(fdtget, dtb, node))
    if len(matches) != 1:
        fail("firmware FDT must contain exactly one " + compatible +
             " node below " + root)
    return matches[0]


def main(argv):
    if len(argv) != 6:
        fail("usage: check-layout.py firmware.elf firmware.bin firmware.dtb kconfig/.config fdtget")
    elf, symbols = read_elf(argv[1])
    firmware_size = pathlib.Path(argv[2]).stat().st_size
    dtb, config, fdtget = argv[3:]

    def symbol(name):
        values = [value for current, value in symbols if current == name]
        if len(values) != 1:
            fail("missing or ambiguous ELF symbol: " + name)
        return values[0]

    start = symbol("_fw_start")
    rw_start = symbol("_fw_rw_start")
    end = symbol("_fw_end")
    if start != FW_BASE:
        fail("firmware load address differs from the S31 memory map")
    rw_offset = rw_start - start
    if rw_offset <= 0 or rw_offset & (rw_offset - 1) or start & (rw_offset - 1):
        fail("firmware RW split violates the OpenSBI PMP alignment contract")
    if rw_start >= WIFI_POOL_BASE or end > WIFI_POOL_BASE:
        fail("OpenSBI overlaps the supervisor Wi-Fi DMA pool")
    for name in (".text", ".rodata", ".dynsym", ".rela.dyn"):
        section = elf.get(name)
        if section is not None and section[3] + section[5] > rw_start:
            fail("read-only firmware section crosses the OpenSBI RW split: " + name)
    provider = [value for name, value in symbols if name == "s31_flash_vendor_ext_provider"]
    if len(provider) != 1 or not start <= provider[0] < rw_start:
        fail("S31 flash SBI provider is absent from the executable firmware region")
    if firmware_size > PACKED_FIRMWARE_LIMIT:
        fail("firmware binary exceeds the S31 SPL load slot")

    config_text = pathlib.Path(config).read_text(encoding="ascii")
    stack_lines = [line for line in config_text.splitlines()
                   if line.startswith("CONFIG_DEFAULT_HART_STACK_SIZE=")]
    if len(stack_lines) != 1:
        fail("missing or ambiguous OpenSBI hart stack configuration")
    stack_size = int(stack_lines[0].split("=", 1)[1], 0)
    listed = subprocess.run((fdtget, "-l", dtb, "/cpus"), check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True).stdout.splitlines()
    hart_count = 0
    for node in listed:
        try:
            device_type = fdt_value(fdtget, dtb, "/cpus/" + node,
                                    "device_type", "s")
        except subprocess.CalledProcessError:
            continue
        if device_type != "cpu":
            continue
        try:
            status = fdt_value(fdtget, dtb, "/cpus/" + node, "status", "s")
        except subprocess.CalledProcessError:
            status = "okay"
        if status not in ("disabled", "fail", "failed"):
            hart_count += 1
    if hart_count == 0:
        fail("firmware FDT has no enabled harts")
    config_node = find_compatible(fdtget, dtb, "/chosen", "opensbi,config")
    heap_size = int(fdt_value(fdtget, dtb, config_node, "heap-size", "x"), 16)
    runtime_end = end + hart_count * stack_size + heap_size
    if runtime_end > WIFI_POOL_BASE:
        fail("OpenSBI stacks and heap overlap the supervisor Wi-Fi DMA pool")
    print("S31 OpenSBI layout and runtime reservation fit before the Wi-Fi pool; flash SBI is present")


if __name__ == "__main__":
    main(sys.argv)
