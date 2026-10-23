# libc++ GCC16 regression tests

The libc++ GCC 16 regression compares the exact pinned libc++ header blobs
with the carried max-size and `std::function` small-buffer patch. It checks
string allocator, difference-type, SSO, and character-width bounds at compile
time. A public-API `std::function` fixture compiles copy, move, swap,
over-aligned, throwing-copy, and `std::bind` paths against both the pinned
baseline and patched headers in C++11 and C++14. That fixture checks source and
public API compatibility; it is not a causal reproduction of the GCC array-bounds
diagnostic. A separate executable fixture covers bounded string allocation
and function copy, move, swap, over-alignment, and throwing-copy behavior. The
runner compiles that fixture for exact GCC16 targets `aarch64--netbsd` and
`x86_64--netbsd` with exceptions enabled. It checks every successful object for
ELFCLASS64, little-endian encoding, ET_REL type, and the target machine ID. It
does not execute target objects or claim runtime acceptance.

Run it with the selected host CPython 3.15 and an explicit SDK API 1 source:

```sh
python3.15 -E -S probes/electron/tests/libcxx-gcc16-regression.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --ports-root /absolute/Ports \
  --source-root /absolute/chromium/src \
  --patch /absolute/Ports/probes/electron/patches/libcxx-gcc16-maxsize-function-sbo.patch \
  --cxx /absolute/GCC16-aarch64--netbsd-g++ \
  --sysroot /absolute/target-sysroot \
  --work-dir /absolute/NEW_LIBCXX_WORK
```

The runner requires the pinned libc++ revision to be an ancestor of the checkout
and requires both live headers to match either the exact pinned baseline or the
exact carried patch. It rejects unrelated dirty header edits. It obtains the
baseline header bytes only with `git show <pin>:<path>`, builds before/after
overlays, and records the actual checkout head and header hashes. Use a new work
directory outside Ports, Chromium source, the SDK, and sysroot. The string baseline must
fail its max-size contract checks; both baseline and patched function fixtures
must compile. The memory fixture uses exceptions for its behavioral code,
while Chromium production objects still use the existing `-fno-exceptions`
configuration. This regression does not compile or link the complete libc++ runtime. Target
execution remains deferred until an ABI-matching NetBSD libc++ runtime is
available; this runner does not claim Valgrind, ASan, or UBSan runtime coverage.

The causal GCC array-bounds check uses the exact production Perfetto translation
units `unix_task_runner.cc` and `weak_runner.cc`; both fail before the header
change and compile after it with their full GN flags. `cpu_info.cc` provides
the corresponding allocation-size diagnostic check. Those production receipts
cover AArch64. Cppcheck 2.18 cannot parse the unchanged pinned libc++ input in
either variant, so no clean Cppcheck result is claimed. Apple Clang 21 static
analysis of the function and exception-enabled memory fixtures finds no issues
in either variant. Static analysis does not establish runtime memory safety.



The libc++ recursive-call patch follows the max-size/SBO patch. The clone
follow-up patch follows the existing `operator()` patch. Its fixture mirrors
`TrackEventDataSource::OnStop`: it copies a closure that captures another
`std::function` by value. The case before the clone patch must fail in GCC's
recursive `__clone` inline chain. The clone patch must compile the same fixture.
The production `track_event_internal.cc` translation unit supplies the
exact-build before/after check. Keep the target sysroot under a shared SDK
context lease:

```sh
python3.15 -E -S probes/electron/tests/libcxx-gcc16-regression.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --ports-root /absolute/Ports \
  --source-root /absolute/chromium/src \
  --patch /absolute/Ports/probes/electron/patches/libcxx-gcc16-maxsize-function-sbo.patch \
  --recursive-patch /absolute/Ports/probes/electron/patches/libcxx-gcc16-recursive-function.patch \
  --clone-recursive-patch /absolute/Ports/probes/electron/patches/libcxx-gcc16-recursive-clone.patch \
  --cxx /absolute/GCC16-target-g++ --sysroot /absolute/target-sysroot \
  --workspace /absolute/SDK-workspace \
  --work-dir /absolute/NEW_LIBCXX_WORK
```

The clone follow-up changes only the GCC fallback annotation on the virtual
`__clone()` call. It keeps hidden visibility. The regression checks the
expected failure before this patch and the successful compile after it. It
does not link DSOs or execute a target binary.
