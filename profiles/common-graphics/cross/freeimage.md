# Maintained FreeImage and LibRaw sources

The common graphics profile replaces `graphics/freeimage` and
`graphics/freeimageplus` together with the maintained FreeImage 3.19.25 release.
It also updates the existing `graphics/libraw` provider to 0.22.2.
These are source recipes. Complete native and target packages remain pending.

## Provenance and licensing

The original project is [FreeImage](https://freeimage.sourceforge.io/).
The maintained [danoli3 release 3.19.25](https://github.com/danoli3/FreeImage/releases/tag/3.19.25)
was published on 2026-10-17. Its tag points to
`363311f106e3fa50e9c39fcc80afe832cb26eabb`.
The recipe uses the release's `FreeImage-3.19.25-linux-source.tar.gz` asset.
The archive contains portable sources; the asset name does not select a Linux binary.
Its SHA256 is `dab013044c3d9122b0a93cee7b53a656426bccc571d3d46880dd8d90a10d1968`.
This matches the publisher's `SHA256SUMS-linux.txt`.
The [source manifest](../sources.tsv) and recipe `distinfo` pin the download.

The original copyrights remain intact. The package uses the recognized
GPLv2 or GPLv3 license alternatives. It also installs the original
FreeImage Public License 1.0 text verbatim. That text is not relabeled MPL.
System codec packages retain their own license ownership.

[LibRaw 0.22.2](https://www.libraw.org/download) comes from its original upstream.
The source SHA256 is `de86b035655accff8d4010f1a221fdf50d353cb7b1422ba26f14a0db92612cfa`.
The existing LGPLv2.1/CDDL alternatives, dependencies, examples policy,
package list and `libraw_r.pc` patch remain unchanged.
The verified 0.22.1 and 0.22.2 sources both select Libtool version `25:0:0`.
This source comparison does not establish installed binary compatibility.

## Package boundaries

Both FreeImage recipes consume the same source archive and patch directory.
The core retains the normal system codecs: JPEG, OpenJPEG, PNG, TIFF, WebP,
LibRaw, OpenEXR, Imath and zlib. OpenEXR must be at least 3.5.2; LibRaw must
be at least 0.22.2. The common Imath provider remains 3.2.3.
No bundled codec is substituted for a missing package dependency.

The small CMake patch extends upstream's lowercase library layout to Unix.
The intended ELF ABI remains `libfreeimage.so.3` and `libfreeimageplus.so.3`.
Both packages also retain their static development archives and public headers.
The C++ package builds the actual seven upstream wrapper translation units.
It uses the core C library instead of rebuilding a private codec stack.
Darwin library filenames have a separate package-list selection; Darwin build
and runtime acceptance are not established by the Linux checks below.

System OpenEXR mode now uses installed `Imath/half.h` in the TIFF plugin.
It omits the bundled `half.cpp` provider from the same build.
The original bundled half header can link against current Imath; no previous
link failure is claimed. This change makes the selected system provider explicit.
The bundled-header route remains available for upstream's bundled configuration.

The release's system-TIFF G3 implementation returns failure. Its system-JPEG
lossless transform implementation also returns failure. The previous canonical
recipe omitted these two implementations. The new recipe does not claim their
restoration and does not introduce replacement stubs. JPEG XR, HEIF and JPEG XL
retain upstream's Unix defaults (off). These boundaries do not prevent OCCT's
normal FreeImage C API integration, which still needs its installed image tests.

`BUILD_TESTS` remains enabled. Test assertions remain active in Release builds.
The core CTest suite and actual upstream FreeImagePlus test are retained.
Their test-only loader environment selects the build library, then the package
prefix, while retaining the existing host runtime search path.
In particular, failing JPEG-transform checks must not be disabled to report
complete codec acceptance. Their system-provider limitation requires a separate
upstream repair if that broader behavior is needed.

## Checks and next integration

On 2026-10-18, the complete common profile export succeeded with the new recipes.
Real native and AArch64 pkgsrc metadata selects the expected versions and
system dependencies, with no package failure reason. All source patches apply
with zero fuzz to the verified archives. LibRaw's C and C++ public declarations
compile with GCC16; all seven FreeImagePlus implementation files compile too.
These are compile and metadata checks, not installed library tests.

The focused [half contract](../tests/freeimage-half.rb) compiles the real TIFF
translation unit before and after the patch. Compiler dependency files prove
the header selection changes from the bundled file to installed Imath.
Both headers produce the same expected results for all 65,536 half encodings.
Finite values round-trip exactly. The installed Imath 3.2.3 run passes strict
Memcheck with zero errors and no live allocations.
GCC16 and Clang19 report no diagnostics for the small contract. Cppcheck2.22
retains upstream-header style/unused-function and missing-system-header reports;
a complete clean Cppcheck result is not claimed.

Run this bounded native check with an actual installed Imath provider:

```sh
CXX='/absolute/native-g++ -B/absolute/native-binutils/' \
  ruby profiles/common-graphics/tests/freeimage-half.rb \
  /absolute/FreeImage-3.19.25-linux-source.tar.gz \
  /absolute/imath-prefix /absolute/new-check-directory
```

The command uses the release's TIFF 4.7.2 headers for translation-unit checks.
It does not build or install a TIFF package. It records commands, statuses,
source/provider hashes and memory diagnostics. It requires genuine native
GCC16 and Valgrind; it does not execute a target binary.

Next, install the common codec dependencies through ordinary pkgsrc. Build,
test and package both FreeImage recipes. Validate their actual installed lists,
shared-library closure, C/C++ image round trips and OCCT load/save operations.
Target package lifecycle and KiCad's complete 3D workflow remain pending.
