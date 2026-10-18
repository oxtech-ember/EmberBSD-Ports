# openTPU Python Package Design

## Goal

Add a pkgsrc package for the complete upstream openTPU Python distribution. Build the package for the EmberBSD AArch64 target with the current Ports toolchain. Run a useful subset of upstream CPU tests on the local host.

This work provides a software package candidate and local test evidence. It does not close E11.

## Package

- Add `py-opentpu` under `pkgsrc/local-ai`.
- Fetch the immutable upstream source revision `730ca28feb77b5598090e97ab209f302f0c56eec`, which is tag `v0.5`.
- Verify the source archive with SHA512 `c1d06fcc1831c36cdf20ccbc6066e0f14d41b5dacddfaa1a53023b4e740911de39b13b75adb6dce9876216e65d929b003891f56b80e2df31902ea60daad9f2b4`.
- Preserve the upstream Python project version `0.1.0`. Record the source tag separately because it does not match the Python package version.
- Package all `opentpu` Python modules, the four upstream command-line entry points, and declared package data.
- Declare the upstream Apache-2.0 license and NumPy runtime dependency.
- Do not patch upstream version metadata or remove project components to fit the package.
- Do not claim support for the YPCB-00338 card, Xilinx XDMA, Vivado, or FPGA hardware. The upstream PCIe setup script is Linux-specific.

The package recipe and source metadata belong in `pkgsrc/local-ai`. The category Makefile must list the new package. Any repository-owned helper must use shell, not Python.

## Local tests

Run upstream `tests/test_isa.py`, `tests/test_compiler.py`, and `tests/test_kernels.py` on the local host. These tests exercise the ISA simulator, compiler, and NumPy kernel references without FPGA hardware.

Install pytest only in a task-owned temporary virtual environment. Do not add pytest to the runtime package. Build and install a host wheel from the same pinned source in that environment. Check package imports and registration of all four command-line entry points.

Do not count `tests/test_rtl.py` as passed when Verilator is unavailable. Do not claim full model inference without the required optional model dependencies and weights.

## Acceptance

- The pinned source archive passes its recorded SHA512 check.
- The AArch64 pkgsrc package builds with GCC 16 and current Ports dependencies.
- The local host wheel install smoke check passes.
- The selected upstream CPU test files pass on the local host.
- The package contents retain upstream provenance, license, modules, entry points, and package data.
- The README records the package, tested platform, commands, and evidence limits.

E11 remains open until the upstream ISA/RTL checks and reproducible model scenario pass on EmberBSD. FPGA integration remains a separate hardware acceptance stage.
