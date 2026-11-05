# PDFium OpenJPEG donor audit

Baseline: Ports common openjpeg 2.5.4. Donor [PDFium revision
`fa4d5f8fbd89ea07273529daf9fd24fe1c7f6b9a`](https://pdfium.googlesource.com/pdfium/+/fa4d5f8fbd89ea07273529daf9fd24fe1c7f6b9a/third_party/libopenjpeg/),
`README.pdfium` and numbered patches. All ported
hunks below apply in donor order with nbpatch `-F0`; 0009 needs three context
lines adjusted to preserve common's existing `OPJ_UINT64` cast. Literal
unpatched hunk preimages matched common, except that context difference. An
exact old hunk alone does not prove that no other guard elsewhere is equivalent.

| Donor | Semantic delta | Common assessment |
|---|---|---|
| 0003 | Bounds checks on inverse DWT temporary arrays. | Donor guard absent; port. |
| 0005 | Index palette output by component index rather than palette-column index. | Donor guard absent; port. |
| 0006 | Reject zero divisor during tile setup. | Donor guard absent; port. |
| 0007 | Read colour-map component indexes explicitly as big endian. | Donor logic absent; port. |
| 0009 | Reject precinct index outside precinct grid in RPCL/PCRL/CPRL. | Guard absent; retain common's existing uint64 casts while porting. |
| 0011 | Avoid unsafe signed-to-unsigned conversion in image update. | Donor guard absent; port. |
| 0012 | Restrict MCT SSE intrinsics in 32-bit builds. | Donor architecture guard absent; port and preserve non-SSE fallback. |
| 0014 | Release the previous components allocation before replacing it in JP2 IHDR. | Donor cleanup absent; port. |
| 0015 | Guard SPCod/SPCoc buffer lengths. | Donor guard absent; port. |
| 0016 | Guard SQcd/SQcc buffer lengths. | Donor guard absent; port. |
| 0019 | Guard tile code-block allocation arithmetic. | Donor guard absent; port. |
| 0022 | Guard palette arithmetic and null component data. | Donor checks absent; port. |
| 0023 | Prevent MCT record heap-use-after-free. | Donor ownership fix absent; port. |
| 0025 | Check MCT record data before use. | Donor guard absent; port. |
| 0034 | Replace OpenJPEG allocator with PDFium FXMEM and C++ shim. | Consumer-specific policy, not a generic security backport; common libc allocator retained. OOM/zero-size behavior is not identical. |
| 0039 | Delete unused static MQC helper. | Cleanup only; keep common upstream source unchanged. |
| 0041 | Remove unused private opj_clock include. | Cleanup only; keep common upstream source unchanged. |
| 0046 | Match codec callback signatures instead of incompatible function-pointer casts. | Callback struct fields stay unchanged; private j2k/jp2 functions adopt matching `void *` ABI. Port. |
| 0047 | `opj_j2k_read_sod` correction, upstream PR 1621. | Donor hunk absent; port. |
| 0048 | NEON 9/7 inverse DWT fix, upstream PR 1629. | Donor hunk absent; port. |
| 0049 | NEON 5/3 inverse DWT fix, upstream PR 1630. | Donor hunk absent; port. |
| 0050 | Overflow guard in packet iterator encoder init, upstream PR 1619. | Donor hunk absent; port. |
| 0051 | Reset and increment owned MCT/MCC record counts on partial deep-copy failure. | Donor ownership fix absent; port and test allocation failure. |
| 0052 | Restore actual MCC record count after copy. | Donor assignment absent; port and test separately. |
| 0053 | Return/propagate failure from private `opj_copy_image_header`. | Common private-but-exported function currently returns void; donor changes to OPJ_BOOL and updates internal call sites. Installed public header remains unchanged. |

Evidence: isolated selected native Clang/Ninja builds shared+static; target ELF
vs patched host Mach-O have identical 250 `opj_*` exported names (not a full
ABI proof). `deepcopy-test.c` passes after 0051/52 and fails before each fix;
`image-copy-test.c` tests invalid components and both allocation failures.
Five PDFium JP2 examples produce identical component hashes with installed and
patched native library. No target execution or full security audit is claimed.

Run `pdfium-ownership.py --cc SELECTED_CC --source PREPARED_SOURCE
--config-dir CMAKE_CONFIG_DIR --static-library OPENJPEG_STATIC_LIBRARY`, with
`--cc-arg=OPTION` for selected toolchain/sysroot arguments. The fixtures include
actual private implementation and inject allocation failure. They check that
partial tile deep copies release only owned records, the completed MCC count is
preserved, and image-header copy rejects invalid inputs and allocation failure.
Use `--compile-only` for a target whose executable cannot run on the host.

With selected Clang, `--strict-callbacks` also rejects incompatible function
pointer casts in `openjpeg.c`; this specifically checks donor 0046.
