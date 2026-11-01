# OpenSBI

All board packages use the common OpenSBI 1.9 source and patch set. The S31
changes derive from Espressif OpenSBI commit
`5395e03e1cb295257142cfdeaade6334f1543bcb` (BSD-2-Clause) and are adapted to
the 1.9 generic platform and irqchip interfaces. The ESP32-S31 package selects
RV32 `ilp32` and `rv32imac_zicsr_zifencei` explicitly. `OPENSBI_LLVM_PREFIX`
selects the host LLVM binary directory, including its trailing slash.
The build takes libfdt sources from the common dtc source package and compiles
them with OpenSBI's freestanding environment; no host libfdt library is linked.
The S31 profile uses Clang `-Oz` and excludes CPPC and MPXY ecall frontends:
it provides neither a CPPC device nor an MPXY channel, so those frontends
would not register. Generic profiles retain their upstream configuration.

The package creates OpenSBI firmware only. It does not provide the compatible
SPL, U-Boot, operating-system device tree, kernel-copy stub or flash layout.
The firmware must not be treated as evidence of a boot on ESP-Mosaico.
The SPL must supply an S-accessible writable FDT whose `totalsize` includes
enough space for OpenSBI fixups; insufficient capacity stops the handoff.
S31 CLIC privilege selection uses the [rev0.0 measured layout](https://github.com/annoyedmilk/esp32-s31-linux/blob/086e52a6b9ae43a3bb07beb2557ea7595df8165b/docs/internals.md#interrupts-the-clic)
and checks configuration and mode readback. The ESP-IDF register description
differs; operation on a specific board remains a hardware check.

S31 cold and warm reboot use the official ROM `software_reset` entry at
`0x2f800094`, exported by ESP-IDF 6.1 as
`esp_rom_software_reset_system()`. The S31 ROM map and wrapper are the source
for this address: Espressif's [S31 ROM map](https://github.com/espressif/esp-idf/blob/v6.1/components/esp_rom/esp32s31/ld/esp32s31.rom.ld)
defines the entry, the [S31 ROM API map](https://github.com/espressif/esp-idf/blob/v6.1/components/esp_rom/esp32s31/ld/esp32s31.rom.api.ld)
exports the wrapper, and [esp_rom_sys.h](https://github.com/espressif/esp-idf/blob/v6.1/components/esp_rom/include/esp_rom_sys.h)
declares it. The ROM implementation itself is not part of the package.
OpenSBI does not claim shutdown support because this platform has no power-off
path. If the ROM reset call returns, OpenSBI prints a diagnostic and parks in
WFI. The ROM effect is not hardware-verified by the source regression.

`tests/clic-check.py` runs the actual CLIC driver on fake MMIO with the selected
SDK native compiler. It covers registration, error propagation, source routing,
and an injected registration failure. `tests/fwft-check.py` checks real FWFT
CSR bit helpers with simulated 32- and 64-bit hart widths, including invalid-bit
controls. `tests/csr-check.py` exercises the counter 31 mask under UBSan.
`tests/fdt-check.py` uses upstream libfdt and the actual S31 handoff
functions to exercise fixed-up output, capacity and allocation failures.
`tests/libfdt-source-check.py` compares the firmware's prepared sources with
the common libfdt package and checks its environment adapter.
`tests/s31-source-check.py` checks the upstream integration points.
`tests/s31-reset-check.py <source>` exercises the real reset-type callback on
host and checks the target reset call address in emitted RV32 code. `CC` and
`RISCV_CC` select the SDK native compiler for host and target checks.
These tests do not execute firmware on the target.
