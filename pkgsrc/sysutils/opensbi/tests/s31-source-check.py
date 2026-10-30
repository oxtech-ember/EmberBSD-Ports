#!/usr/bin/env python3
"""Check S31 integration points that must survive upstream OpenSBI updates."""
import pathlib
import sys

root = pathlib.Path(sys.argv[1])

def source(name):
    return (root / name).read_text()

platform = source('platform/generic/espressif/esp32s31/esp32s31.c')
irqchip = source('lib/utils/irqchip/fdt_irqchip_clic.c')
traps = source('lib/sbi/sbi_expected_trap.S')
stores = source('lib/sbi/sbi_trap_ldst.c')
assert 'const struct fdt_driver esp32s31' in platform
assert 'generic_platform_ops.vendor_ext_provider' in platform
assert 'generic_final_init(cold_boot)' in platform
assert 'fdt_fixup_buffer_begin' in platform and 'fdt_fixup_buffer_end' in platform
for path in ('lib/utils/fdt/fdt_domain.c', 'lib/utils/fdt/fdt_fixup.c',
             'platform/generic/platform.c'):
    assert 'fdt_fixup_open_into' in source(path)
    assert 'CONFIG_PLATFORM_ESPRESSIF_ESP32S31' not in source(path)
assert 'fdt_pack' in platform and 's31_uboot_dtb_size' in platform
assert 'num_hwirq' in irqchip and 'target_harts' in irqchip
assert 'return sbi_irqchip_add_device(&clic_device)' in irqchip
assert 'const struct fdt_driver fdt_irqchip_clic' in irqchip
assert 'CLICCFG_NMBITS_MASK' in irqchip and 'readb(' in irqchip
assert 'union sbi_ldst_data val;' not in stores
assert traps.count('csrc\tCSR_MSTATUS, a4') == 2
assert traps.count('slli\ta4, a4, (__riscv_xlen - 12)') == 2
print('S31 source integration checks passed')
