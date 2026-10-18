# NetBSD C++ numeric conversion without a process locale change

GCC16's generic C locale backend calls `setlocale` around numeric parsing
and formatting. Two WebKit Skia workers reproduced the resulting race on
EmberBSD 11 AArch64: a worker expecting a comma received a decimal point,
and the ambient process locale was temporarily `C`. Real NetBSD
`snprintf_l` with independent `C` and French locales passed an isolated
check; the shared C++ backend was the remaining source of global changes.

The local, AI-assisted [source patch](patches/gcc-netbsd-locale.patch) uses
NetBSD's existing immutable C locale object for `vsnprintf_l`, `strtof_l`,
`strtod_l`, `strtold_l` and `sscanf_l`. It changes only the generic backend's NetBSD
conversion paths. The `int*` generic handle ABI, stream token extraction,
precision, overflow/failbit handling, errno logic and existing rejection of
named C++ locales remain. No locale allocation, destruction or global
`setlocale` call is needed for these conversions.

The existing configure decisions remain: a missing `HAVE_STRTOF` uses
the same double-to-float conversion, and a missing or broken `HAVE_STRTOLD`
keeps the `sscanf` fallback with its existing partial-token behavior.
Each selected NetBSD operation uses its corresponding real locale API.

`LC_C_LOCALE` names the real exported `_lc_C_locale` object in NetBSD's
public `locale.h`. Explicit POSIX feature macros hide that constant and,
for older POSIX modes, the `locale_t` typedef. The installed internal C++
header therefore declares the exact existing libc object and
`vsnprintf_l` ABI in its NetBSD branch; it neither changes the caller's
feature macros nor introduces a libc symbol or structure layout.
The full library source builds with its normal NetBSD declarations.

The canonical recipe prepares `gcc16-16.2.0nb2` and `gcc16-libs-16.2.0nb3`.
The installed header and rebuilt library must be deployed together.
Consumers that instantiated the old inline formatting implementation must
be rebuilt. The AArch64 `gcc16-runtime-16.2.0nb3` package now passes ordinary
pkgsrc packaging, including RELRO, and installed SDK/EmberBSD checks below.

## Reproduce the bounded check

Run from a genuine native GCC16 environment with Ruby, pkgsrc `digest`,
GNU patch/tar and a supported Valgrind host. Inputs are the pinned pkgsrc
checkout, official GCC16.2 archive, actual target driver and coherent
NetBSD11 sysroot. The output must not exist.

```sh
NATIVE_CXX='/absolute/native-g++ -B/usr/bin/' \
DIGEST=/absolute/native-prefix/bin/digest \
ruby profiles/development-toolchain/tests/locale/build.rb \
  /absolute/pinned-pkgsrc /absolute/gcc-16.2.0.tar.xz \
  /absolute/toolchain/bin/aarch64--netbsd-g++ \
  /absolute/sysroot /absolute/new-output
```

The helper verifies the archive and pkgsrc commit, applies the real
package patches with zero fuzz, invokes pkgsrc's checksum verifier, and
compiles the complete original/repaired `c_locale.cc` with the corresponding
installed-header override. Both target versions link under C++17/20/23 and
explicit POSIX 200112L/200809L namespaces. Each executable defines the actual
conversion functions from its own object; this is a bounded source test,
not a replacement installed libstdc++ package. The helper leaves its inputs,
commands, compiler versions, hashes and logs in the new output directory.
Target compiler calls clear inherited host include/library search variables.

The [contract](tests/locale/contract.cpp) checks float/double/long-double
conversion, signed zero, short-buffer formatting, overflow, malformed and
partial tokens, errno, existing stream grammar, two concurrent conversion
workers and an independent ambient-locale observer. Assertions are required.
The native run uses its genuine native library; it does not execute the
NetBSD source branch. After an approved VM transfer, run both target
executables with an installed comma locale, for example `fr_FR.UTF-8`.
Retain the original failure, repaired result and loaded-provider hashes.
Then rebuild the contract without the private source object and rerun the
actual affected Skia worker contract against the installed repaired package.

## Current evidence and limits

On Linux GCC16.2, the native contract and strict Memcheck pass with zero
errors and zero live blocks. The non-NetBSD preprocessed source and header
are byte-identical before and after the patch. Actual AArch64 GCC16 builds
and links pass in all five language/namespace configurations. These results
are accompanied by actual EmberBSD 11 AArch64 execution of both C++20
source-object binaries. Both pass the serial numeric and stream checks.
The original then fails the ambient-locale observer during concurrent
conversion; the repaired version passes both 2,000-iteration workers and
ambient restoration. Loaded nb2 runtime/base libraries and all fourteen
locale inputs were hash-verified against their existing providers.
This proves the compiled source paths, not an installed repaired package.

Clang19 static analysis of both complete target source variants and the
contract reports no diagnostics using the actual NetBSD/GCC16 headers.
Cppcheck2.22 was also run before and after on real target-preprocessed
source; both stop at an existing GCC16 `__extension__`/`__int128` template
syntax limitation. Its contract model run has no remaining code warning,
but reports unavailable system headers. These incomplete Cppcheck runs
are retained as limitations, not reported as clean whole-module analysis.

The normal AArch64 runtime-only nb3 package has SHA256
`c6db6c55a44c8aa5de89b6569dddbd4d04bb164447b8af6b891be40ee6467335`.
SDK migration verifies all nine runtime payload entries and installs the matching
development headers. The sole changed header is `bits/c++locale.h`, SHA256
`15202f54695ffa342c02f6aaea2070304ef47cb27e230b0e95cb9d358b66ae05`.
The rebuilt library retains all 6,190 defined dynamic symbols. The separate
RELRO relink repairs the three inherited runtime DSOs; it does not replace the
fresh libstdc++ source build.

Actual EmberBSD 11 AArch64 acceptance installs that ordinary package and checks
all nine entries. Fresh consumers compiled against the installed header pass
numeric/stream semantics, both conversion workers and ambient restoration in
plain and LTO builds, without a private conversion object. The associated
C11/C++20 TLS, threads, DSO exception, OpenMP and large-atomic checks also pass.
All 13 selected Skia units were recompiled against the new header; the
[real API contract](../common-graphics/cross/wxwebkit.md#netbsd-numeric-locale)
passes with genuine `fr_FR.UTF-8` locale data. Guest provider hashes match the
package; execution needs no library search override or target compiler.

The original Skia failure, isolated libc success and source-object before/after
comparison remain preserved. Full WebKit compilation, amd64 execution,
physical-board execution and broader named-locale support remain unclaimed.
