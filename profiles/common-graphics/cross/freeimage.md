# Maintained FreeImage and LibRaw sources

The common graphics profile replaces `graphics/freeimage` and
`graphics/freeimageplus` together with the maintained FreeImage 3.19.25 release.
It also updates the existing `graphics/libraw` provider to 0.22.2.
These are source recipes. Complete native and target packages remain pending.
The original native core build passes eight of nine upstream tests. The
JPEG transform test exposes an unsupported path in the unmodified release.
The source repair uses the common TurboJPEG public API and passes the focused
coefficient contract below. The revised package's complete suite remains pending.
The static package list uses the `FreeImageTargets-noconfig.cmake` file produced
by both ordinary native and AArch64 stages. The repaired complete packages
have not yet passed their final package checks.

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

The release's system-TIFF G3 implementation returns failure. Its restoration
remains separate work. The system-JPEG lossless implementation now uses
`tj3Transform` from the same common libjpeg-turbo 3.2.0 package as libjpeg.
It retains marker copying, trimming, perfect-transform checks, crop queries
and same-handle writes. The original bundled-codec branch remains intact.
TurboJPEG rejects crops of unknown sampling types. Both crop queries and
output calls report that limit; uncropped transforms remain available.
The recipes require the common libjpeg-turbo provider explicitly.
JPEG XR, HEIF and JPEG XL
retain upstream's Unix defaults (off). These boundaries do not prevent OCCT's
normal FreeImage C API integration, which still needs its installed image tests.

`BUILD_TESTS` remains enabled. Test assertions remain active in Release builds.
The core CTest suite and actual upstream FreeImagePlus test are retained.
Their test-only loader environment selects the build library, then the package
prefix, while retaining the existing host runtime search path.
In particular, JPEG-transform assertions remain active for package acceptance.

## Checks and next integration

The [JPEG contract](../tests/freeimage-jpeg/README.md) builds the complete real
`JPEGTransform.cpp` translation unit against the native common codec provider.
The original source fails a valid perfect vertical flip. The repaired source
passes 334 transform, crop and error cases. Independent coefficient identities
check every transformed DCT value, quantization tables and APP1/COM markers.
All eight operations cover common subsampling types and grayscale, including
partial edges. Tests also cover normalized and edge-relative rectangles,
crop queries, nonzero same-handle offsets, short I/O, allocation failure and
failed or throwing callbacks. Unknown 3:1 sampling keeps uncropped transforms
and reports the public API's crop restriction consistently.

The repaired contract passes strict native Memcheck with zero errors and no
live allocations. Clang19 reports no diagnostics for either source version
with the selected GCC16 C++ headers. Cppcheck2.22 retains inherited source/header
findings with modeled system headers. Its actual GCC16-preprocessed pass stops
at a system `math.h` parser error in both versions. A clean full Cppcheck result
is not claimed. The test runner retains both diagnostic sets without category
suppression. It also compiles, links and runs the actual patched CMake JPEG
branch. Full package and target execution remain separate gates.

```sh
python3.15 profiles/common-graphics/tests/freeimage-jpeg/check-source.py \
  /absolute/FreeImage-3.19.25-linux-source.tar.gz \
  /absolute/native-g++ /absolute/native-codec-prefix /absolute/new-check
```

`AssignPixel` copies the same eight supported pixel widths with `memcpy`.
This removes word and floating-point accesses to potentially unaligned byte
storage. Its unsupported-width assertion remains unchanged. All existing
callers use separate storage: TIFF strip buffers and destination bitmaps,
TARGA pixel buffers and scanlines, or rotation scratch arrays and newly
allocated images. `FreeImage_Paste` does not call this internal helper.
The change does not add an overlapping-buffer API contract.

The focused [pixel contract](../tests/freeimage-pixels/check-source.rb) extracts
the complete upstream function and retains the actual public byte/word types.
Matched GCC16 `-O2` builds reproduce the original alignment-sanitizer failure
and pass all eight widths at four unaligned offsets after the repair.
Exact pixel bytes and untouched surrounding bytes are checked. The repaired
native contract passes strict Memcheck with zero errors and no live allocations.
Clang19 reports no diagnostics for either finite contract. Cppcheck2.22 on
actual GCC16-preprocessed input removes fourteen incompatible-pointer-cast
reports. The unchanged assertion and system-header style reports remain.
The actual AArch64 rotation translation unit also compiles without its previous
inline pixel-copy warnings. These checks do not establish target execution or
complete FreeImage memory acceptance.

```sh
ruby profiles/common-graphics/tests/freeimage-pixels/check-source.rb \
  /absolute/FreeImage-3.19.25-linux-source.tar.gz \
  /absolute/native-g++ /absolute/new-pixel-check
```

The common cross profile also selects the installed GCC16 C++ library during
CMake discovery. The [provider contract](../../common-build-tools/cross/pkgconfig.md)
prevents an explicit LibRaw `-lstdc++` from selecting the base C++ ABI alongside
GCC16. Full FreeImage target relinking and package validation remain pending.

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
