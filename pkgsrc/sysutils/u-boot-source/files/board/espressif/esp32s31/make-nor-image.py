#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Create an ESP32-S31 NOR image from explicitly prepared firmware inputs."""
import argparse
import hashlib
import os
import platform
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib

FLASH_SIZE = 0x1000000
SPL_OFFSET = 0x2000
FIT_OFFSET = 0x20000
ROOT_SIZE = 0x400000
DTB_SIZE = 0x3000
IMAGES = {'firmware': ('opensbi.bin', 0x2f000000, 0x30000),
          'uboot': ('u-boot.bin', 0x50400000, 0x30000),
          'fdt': ('firmware.dtb', 0x50430000, DTB_SIZE),
          'root': ('root.fs', 0x50000000, ROOT_SIZE),
          'kernel': ('kernel.itb', 0x50c00000, 0x370000)}


def validate_rom(data):
    if len(data) < 24 or len(data) > FIT_OFFSET - SPL_OFFSET:
        raise ValueError('SPL ROM image size is outside its NOR slot')
    magic, count, mode, size_freq, entry = struct.unpack_from('<BBBBI', data)
    chip = struct.unpack_from('<H', data, 12)[0]
    digest_flag = data[23]
    if (magic, mode, size_freq, chip) != (0xe9, 2, 0x40, 32) or not 1 <= count <= 16 or digest_flag != 1:
        raise ValueError('expected ESP32-S31, DIO 40 MHz, 16 MiB image with digest')
    pos, checksum, segments = 24, 0xef, []
    for _ in range(count):
        if pos + 8 > len(data): raise ValueError('truncated segment header')
        addr, size = struct.unpack_from('<II', data, pos); pos += 8
        if size == 0 or pos + size > len(data) or not (0x2f040000 <= addr < addr + size <= 0x2f050000):
            raise ValueError('SPL segment outside SRAM or truncated')
        if any(addr < end and start < addr + size for start, end in segments):
            raise ValueError('overlapping SPL segments')
        segments.append((addr, addr + size))
        for byte in data[pos:pos + size]: checksum ^= byte
        pos += size
    check = pos | 15
    if check + 33 != len(data) or data[check] != checksum or hashlib.sha256(data[:check + 1]).digest() != data[check + 1:]:
        raise ValueError('invalid ROM image checksum, digest or trailer')
    if not any(start <= entry < end for start, end in segments):
        raise ValueError('SPL entry outside segments')


def elf_extent(data, low=0x50400000, high=0x50430000):
    if len(data) < 52 or data[:7] != b'\x7fELF\x01\x01\x01': raise ValueError('proper is not ELF32 little endian')
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    if h[2] != 243 or h[4] != low or h[7] & 0x0e: raise ValueError('proper is not RV32 ILP32 soft-float at expected entry')
    phoff, phentsize, phnum = h[5], h[9], h[10]
    if phentsize < 32 or phoff + phentsize * phnum > len(data): raise ValueError('invalid ELF program headers')
    loads = []
    for n in range(phnum):
        typ, off, va, pa, filesz, memsz, _, _ = struct.unpack_from('<8I', data, phoff + n * phentsize)
        if typ == 1:
            if filesz > memsz or off + filesz > len(data) or va != pa or not (low <= pa <= pa + memsz <= high):
                raise ValueError('proper ELF load/BSS outside allowed range')
            loads.append((pa, pa + memsz))
    if not loads or min(x[0] for x in loads) != low: raise ValueError('missing proper LOAD')
    return max(x[1] for x in loads)


def run(argv, *, cwd=None, env=None):
    return subprocess.run([str(x) for x in argv], cwd=cwd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def resolve_mkimage(path, prefix):
    mkimage = path.resolve(strict=True)
    if not mkimage.is_relative_to(prefix):
        raise ValueError('mkimage resolves outside prefix')
    return mkimage


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('host-prefix', 'mkimage', 'spl-rom', 'opensbi', 'uboot', 'uboot-elf', 'firmware-dtb', 'kernel-fit', 'kernel-elf', 'root-fs', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    prefix = a.host_prefix.resolve(strict=True)
    tools = {n: (prefix / 'bin' / n).resolve(strict=True) for n in ('dtc', 'fdtget', 'llvm-objcopy', 'llvm-readobj')}
    if any(not v.is_relative_to(prefix) for v in tools.values()): raise ValueError('host tool resolves outside prefix')
    mkimage = resolve_mkimage(a.mkimage, prefix)
    env = dict(os.environ, PATH=str(prefix / 'bin') + os.pathsep + str(prefix / 'gnu/bin'), SOURCE_DATE_EPOCH='0', LC_ALL='C')
    machine = {'arm64': 'aarch64', 'x86_64': 'x86_64', 'aarch64': 'aarch64'}.get(platform.machine())
    if not machine: raise ValueError('unsupported host architecture')
    for tool in (*tools.values(), mkimage):
        headers = run((tools['llvm-readobj'], '--file-headers', tool), env=env).decode()
        if 'Arch: ' + machine not in headers.splitlines(): raise ValueError('wrong host architecture: ' + str(tool))
    spl = a.spl_rom.read_bytes(); validate_rom(spl)
    proper = a.uboot.read_bytes(); extent = elf_extent(a.uboot_elf.read_bytes())
    root = a.root_fs.read_bytes(); kernel = a.kernel_fit.read_bytes(); opensbi = a.opensbi.read_bytes()
    kernel_end = elf_extent(a.kernel_elf.read_bytes(), 0x80200000, 0x80800000)
    if len(root) != ROOT_SIZE: raise ValueError('root FS must be exactly 4 MiB')
    with tempfile.TemporaryDirectory(prefix='s31-nor-') as tmp:
        work = Path(tmp)
        run((tools['llvm-objcopy'], '--gap-fill=0xff', '-O', 'binary', a.uboot_elf.resolve(), work / 'proper-flat'), env=env)
        if not proper.startswith((work / 'proper-flat').read_bytes()): raise ValueError('U-Boot binary differs from ELF')
        for name, data in (('opensbi.bin', opensbi), ('u-boot.bin', proper), ('root.fs', root), ('kernel.itb', kernel)):
            (work / name).write_bytes(data)
        run((tools['dtc'], '-I', 'dtb', '-O', 'dtb', '-S', str(DTB_SIZE), '-o', work / 'firmware.dtb', a.firmware_dtb.resolve()), env=env)
        if (work / 'firmware.dtb').stat().st_size != DTB_SIZE: raise ValueError('firmware FDT exceeds padded slot')
        def firmware_get(node, prop, typ='s'):
            return run((tools['fdtget'], '-t', typ, work/'firmware.dtb', node, prop), env=env).decode().strip()
        if 'fit-images' in run((tools['fdtget'], '-l', work/'firmware.dtb', '/'), env=env).decode().splitlines():
            raise ValueError('firmware DTB already contains fit-images')
        if ('espressif,esp32s31' not in firmware_get('/', 'compatible').split() or
            firmware_get('/memory@50000000', 'reg', 'x') != '50000000 1000000' or
            firmware_get('/chosen', 'stdout-path') != 'serial0:115200n8'):
            raise ValueError('firmware DTB memory, console or SoC differs from profile')
        for name, (filename, address, limit) in IMAGES.items():
            size = (work / filename).stat().st_size
            if not size or size > limit: raise ValueError(name + ' exceeds its memory slot')
        def nested_get(node, prop, typ='s'):
            return run((tools['fdtget'], '-t', typ, work/'kernel.itb', node, prop), env=env).decode().strip()
        config = nested_get('/configurations', 'default')
        if (nested_get('/configurations/' + config, 'kernel') != 'kernel' or
            nested_get('/configurations/' + config, 'fdt') != 'fdt'):
            raise ValueError('nested FIT selects unexpected images')
        nested_payloads = {}
        for node in ('kernel', 'fdt'):
            path = '/images/' + node
            payload = bytes(int(x, 16) for x in nested_get(path, 'data', 'bx').split())
            hashes = [x for x in run((tools['fdtget'], '-l', work/'kernel.itb', path), env=env).decode().splitlines() if x.startswith('hash')]
            nested_payloads[node] = payload
            if not payload or not hashes:
                raise ValueError('nested FIT payload or hash missing: ' + node)
            for hash_node in hashes:
                digest = bytes(int(x, 16) for x in nested_get(path + '/' + hash_node, 'value', 'bx').split())
                if (nested_get(path + '/' + hash_node, 'algo') != 'sha256' or
                    hashlib.sha256(payload).digest() != digest):
                    raise ValueError('nested FIT hash mismatch: ' + node)
            if node == 'fdt':
                (work/'nested.dtb').write_bytes(payload)
                run((tools['dtc'], '-I', 'dtb', '-O', 'dtb', '-o', work/'nested-checked.dtb', work/'nested.dtb'), env=env)
        inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
        flat = inflater.decompress(nested_payloads['kernel'], 0x600001)
        if len(flat) > 0x600000 or not inflater.eof or inflater.unused_data:
            raise ValueError('nested kernel gzip exceeds its RAM span or is incomplete')
        run((tools['llvm-objcopy'], '--gap-fill=0', '-O', 'binary', a.kernel_elf.resolve(), work/'kernel-flat'), env=env)
        if flat != (work/'kernel-flat').read_bytes():
            raise ValueError('nested kernel differs from ELF')
        nested_dtb = work/'nested.dtb'; nested_dtb.write_bytes(nested_payloads['fdt'])
        def dtget(node, prop, typ='s'):
            return run((tools['fdtget'], '-t', typ, nested_dtb, node, prop), env=env).decode().strip()
        if ('espressif,esp-mosaico' not in dtget('/', 'compatible').split() or
            dtget('/memory@50000000', 'reg', 'x') != '50000000 1000000' or
            dtget('/chosen', 'stdout-path') != 'serial0:115200n8'):
            raise ValueError('nested DTB memory, console or board differs from profile')
        if (nested_get('/images/fdt', 'type') != 'flat_dt' or
            nested_get('/images/fdt', 'arch') != 'riscv' or
            nested_get('/images/fdt', 'compression') != 'none'):
            raise ValueError('nested FDT metadata differs from profile')
        if (nested_get('/images/kernel', 'type') != 'kernel' or
            nested_get('/images/kernel', 'arch') != 'riscv' or
            nested_get('/images/kernel', 'os') != 'netbsd' or
            nested_get('/images/kernel', 'compression') != 'gzip' or
            int(nested_get('/images/kernel', 'load', 'x'), 16) != 0x50600000 or
            int(nested_get('/images/kernel', 'entry', 'x'), 16) != 0x50600000):
            raise ValueError('nested kernel FIT metadata differs from profile')
        shutil.copyfile(Path(__file__).with_name('nor-firmware.its'), work / 'firmware.its')
        run((mkimage, '-E', '-B', '0x200', '-f', 'firmware.its', 'firmware.itb'), cwd=work, env=env)
        fit = (work / 'firmware.itb').read_bytes()
        if FIT_OFFSET + len(fit) > FLASH_SIZE: raise ValueError('FIT exceeds NOR')
        def get(node, prop, typ='s'):
            return run((tools['fdtget'], '-t', typ, work/'firmware.itb', node, prop), env=env).decode().strip()
        if (get('/configurations', 'default') != 'conf' or
            get('/configurations/conf', 'firmware') != 'firmware' or
            get('/configurations/conf', 'fdt') != 'fdt' or
            get('/configurations/conf', 'loadables') != 'uboot root kernel'):
            raise ValueError('unexpected FIT configuration')
        fit_size = struct.unpack_from('>I', fit, 4)[0]
        payload_ranges = []
        for name, (filename, address, _) in IMAGES.items():
            node = '/images/' + name
            props = set(run((tools['fdtget'], '-p', work/'firmware.itb', node), env=env).decode().splitlines())
            expected_type = 'flat_dt' if name == 'fdt' else 'firmware'
            if (int(get(node, 'load', 'x'),16) != address or get(node, 'compression') != 'none' or
                get(node, 'type') != expected_type or get(node, 'arch') != 'riscv' or
                get(node+'/hash', 'algo') != 'sha256'):
                raise ValueError('wrong FIT image metadata: ' + name)
            if name in ('root', 'kernel', 'fdt') and ({'os', 'entry'} & props):
                raise ValueError('unexpected OS or entry for ' + name)
            if name in ('firmware', 'uboot'):
                if get(node, 'os') != ('opensbi' if name == 'firmware' else 'u-boot') or int(get(node, 'entry', 'x'), 16) != address:
                    raise ValueError('wrong firmware OS or entry: ' + name)
            offset = int(get(node, 'data-offset', 'x'),16) + ((fit_size + 3) & ~3)
            size = int(get(node, 'data-size', 'x'),16)
            if offset % 512 or (size + 511) // 512 * 512 > IMAGES[name][2]:
                raise ValueError('FIT external alignment exceeds load slot: ' + name)
            if offset < fit_size or offset + size > len(fit) or any(offset < end and start < offset + size for start,end in payload_ranges): raise ValueError('overlapping or invalid FIT payload')
            payload_ranges.append((offset, offset+size))
            payload = (work / filename).read_bytes()
            digest = bytes(int(x, 16) for x in get(node+'/hash', 'value', 'bx').split())
            if size != len(payload) or fit[offset:offset+size] != payload or digest != hashlib.sha256(payload).digest():
                raise ValueError('FIT data/hash mismatch: ' + name)
        image = bytearray(b'\xff') * FLASH_SIZE
        image[SPL_OFFSET:SPL_OFFSET+len(spl)] = spl
        image[FIT_OFFSET:FIT_OFFSET+len(fit)] = fit
        with a.output.open('xb') as output:
            output.write(image)
        print(f'NOR image {len(image)} bytes; FIT {len(fit)} bytes; U-Boot runtime end 0x{extent:08x}; kernel RAM end 0x{0x50600000 + kernel_end - 0x80200000:08x}; SHA256 {hashlib.sha256(image).hexdigest()}')

if __name__ == '__main__':
    main()
