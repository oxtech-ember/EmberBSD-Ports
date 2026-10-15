# Current compiler prerequisites

The GCC profile updates MPFR/MPC/Texinfo recipes using
`patches/current-prerequisites.patch` and the test harness using
`patches/stable-expect.patch`. These are AI-assisted EmberBSD deltas,
not submitted upstream. Versions are selected from upstream releases, not
from the age of the pkgsrc recipe. Full archive SHA256 values are in
`sources.tsv`; BLAKE2s, SHA512 and byte counts are in the resulting distinfo.

## MPFR 4.2.2

[Upstream current release](https://www.mpfr.org/mpfr-current/) identifies
4.2.2, released 2025-03-20. NetBSD/pkgsrc's `math/mpfr` still selects 4.2.1
at inspected trunk revision `1d0b4bfd1560971538e8ab1f3cb4648c43960c32`.
The local update preserves the original NetBSD recipe identifiers, LGPLv3
license, GMP >=5.0 dependency, test target and PLIST. It uses upstream's
original `.tar.bz2` archive and HTTPS; copies from mpfr.org and ftp.gnu.org
were byte-identical. The detached upstream signature is preserved privately;
OpenPGP verification was not performed because the host lacks GnuPG.
Pinned hashes verify consistency, not independent signer authentication.

Upstream describes 4.2.2 as ABI-compatible with 4.2.1. Libtool version-info
changes from `8:1:2` to `8:2:2`, retaining runtime major 6. New behavior
includes the `mpfr_float128` conversion-type portability macro and fixes to
formatted output, including `%c` with zero. Binary128 itself predates this
release. The inherited NetBSD `--disable-float128` remains: a libc binary128
comparison repair does not prove compiler `_Float128` API support.

Source checks verify the new archive and prepared recipe, including corrupt
archive and repeated-delta rejection. Run the bounded archive gate with:

```sh
sh profiles/development-toolchain/tests/source-profile.sh \
    /absolute/verified-distfiles/mpfr-4.2.2.tar.bz2
```

On physical Zero 3W, native MPFR configure/build/tests, staging/check-files,
package installation and installed GMP/MPFR identity pass: 195 tests pass and
three inherited decimal/_Float128 cases skip. The unchanged MPC 1.4.1 package
passes all 75 upstream arithmetic tests against MPFR 4.2.2. The already built
GCC16 package passes its dependency and focused compiler/runtime checks without
rebuilding GCC. See the [native evidence and limits](native-validation.md).

The private profile `mk.conf` requires `mpfr>=4.2.2` for buildlink consumers
so an installed 4.2.1 cannot satisfy the selected common dependency policy.
Upstream API/ABI floors stay unchanged outside this profile. The policy does
not set `GCC_REQD`, create an MPFR self-dependency, or activate GCC16 while
building bootstrap math packages. When BSD make is available, the finite
source check parses the real GCC external-math option block and MPC buildlink
metadata with the profile, plus unscoped and bootstrap boundary cases.

## MPC 1.4.1

[Upstream download page](https://www.multiprecision.org/mpc/download.html)
identifies 1.4.1 as current. The archive uses `.tar.xz`, unlike pkgsrc's 1.3.1.
The upstream signature was checked with the maintainer's key from
<https://www.multiprecision.org/downloads/enge.gpg>, fingerprint
`AD17A21EF8AED8F1CC02DBD9F7D5C9BF765C61E3`. The signature is cryptographically
valid; GnuPG reports the published key expired at the time of this check.
This is recorded rather than claiming a currently trusted certification.

The source retains libtool version-info `7:1:4`, hence runtime major 3.
No earlier MPC package was installed on the preparation host. The recipe
adds the new `lib/pkgconfig/mpc.pc` file. Its inherited Solaris complex-number
workaround is refreshed for `_MPC_HAVE_COMPLEX_H` and `DOUBLE_COMPLEX`.
MPC still requires GMP >=5.0 and MPFR >=4.1; this profile selects MPFR 4.2.2
above. Native arithmetic tests and dependency identity pass on Zero 3W, as
described in the linked native validation.

## Texinfo 7.3

[Upstream release announcement](https://lists.gnu.org/archive/html/info-gnu/2026-03/msg00000.html)
identifies 7.3, released 2026-03-02. It reorganizes `tp/` into `tta/`.
The archive's signature verifies against the GNU release keyring from
<https://ftp.gnu.org/gnu/gnu-keyring.gpg>, fingerprint
`EAF669B31E31E1DECBD11513DDBC579DAB37FBA9` (Gavin Smith).
The isolated verification keyring does not assign personal owner trust.
The inherited top-level configure and gnulib patches apply unchanged.
The default Info path patch is refreshed around the new DJGPP conditional.
Three obsolete patches are removed with these concrete reasons:

- `tp/Texinfo/XS/configure` no longer exists. Its replacement is
  `tta/configure`. Keep that replacement's working-iconv check enabled.
- The C parser moved to `tta/C/parsetexi`; the prior patch merely moved a
  C99 loop-variable declaration. Our NetBSD 11 bootstrap compiler supports C99.
- Upstream removed texi2dvi's historical ksh re-exec branch, so the patch
  disabling it is obsolete.

The recipe retains Perl XS and external Perl module dependencies.
Its PLIST follows the 7.3 Automake install destinations: Perl example
converters still install below `Texinfo/Convert`, XS modules move into
`lib/texi2any/XS_extension`, and C libraries into `lib/texi2any/lib`.
The enabled XS/C build also installs new reader, tree-element, configuration
and Texinfo conversion modules, `libtexinfo-main`, and `load_txi_modules`.
Native staging also verified the split `share/texinfo/htmlxref.d` data and
the Unix `info-hooks` script/data replacing the former `htmlxref.cnf` entry.
Native staging and pkgsrc `check-files` must confirm the complete payload.
On native Darwin, `INCOMPAT_ICONV+=Darwin-*-*` selects pkgsrc's GNU libiconv
provider. The pinned recipe is 1.19, also the current release listed by
[GNU](https://www.gnu.org/software/libiconv/). Darwin's built-in implementation
fails the upstream working-iconv test. That failure disables
`USE_SHARED_TXI_LIBRARIES` even with `--enable-perl-xs`, omitting the C
libraries and most XS modules required by the package list. Do not suppress
the test or remove those package entries. NetBSD target provider selection
is unchanged.

The source regression uses real bmake and the pinned iconv builtin policy
for Darwin and NetBSD architectures. Set `TEXINFO_PREPARED_SOURCE` to an
actual unpacked Texinfo 7.3 source tree to execute its shared-library configure
decision with both failed and successful working-iconv results. These fixtures
do not establish a real GNU-provider build. After installing native GNU
libiconv, rerun the actual iconv conftest, then configure and stage Texinfo
anew. Require `am_cv_func_iconv_works=yes`, `USE_SHARED_TXI_LIBRARIES_TRUE=''`,
actual XS loading, Info/HTML conversion and ordinary package file checks.
Preserve the previous failed build and its logs until that acceptance passes.
Patch checksums use pkgsrc's RCS-ID filtering; the source regression invokes
pkgsrc's own checksum verifier and rejects a deliberately unfiltered digest.
Do not weaken pkgsrc's Perl ABI constraints or vendor another Perl runtime
to get through configuration. The pinned Perl 5.44.0 recipe supplies the
required ABI; replacing an installed older Perl requires rollback packages
and a coordinated rebuild of its ABI-bound Perl modules. Test XS loading,
Info/HTML generation, and package file lists before accepting Texinfo.

## Test harness and bootstrap boundaries

GNU make 4.4.1 and DejaGNU 1.6.3 remain upstream current releases. GNU sed
4.10 is supplied by the pinned recipe. Tcl 8.6.18 is the latest supported
8.6 release in 2026, with development ending in 2026 according to
<https://www.tcl-lang.org/software/tcltk/8.6.html>.
The profile updates Expect from 5.45.0 to the last stable 5.45.4;
the [official site](https://core.tcl-lang.org/expect/home) publishes its
archive SHA256. The three pkgsrc portability patches are retained with
refreshed contexts, including the generated configure substitution for
`SHLIB_VERSION`. Library names follow 5.45.4's undotted `5454` suffix.
The NetBSD adaptation also pins stty to its actual stdin behavior. Without
a controlling terminal, upstream's configure probe misidentifies it as
reading stdout, reversing explicit slave-PTY redirections and failing both
upstream stty tests. The test driver now returns failure for failed tests
or sourced test-file errors; the original driver returned zero for 13/15
passing tests. Package revision 1 includes these portability/test fixes.

The official site points to the maintained
[Tcl 9 port](https://github.com/tcltk-depot/expect). Its README identifies
6.0a0 as work in progress, not production ready, with only Linux tested.
Thus this test harness uses the supported Tcl 8.6.18 branch, rather than
an alpha Expect dependency. No other Tcl runtime is installed alongside it.
Remove this exception when a stable Expect supporting Tcl 9 passes the
NetBSD PTY/spawn tests and DejaGNU/GCC test driver checks. This is a bounded
compiler-test dependency, not the release development-runtime selection.

Source preparation and native validation are separate evidence levels.
The named native prerequisite checks do not establish a passed complete GCC
test suite or the common C++ consumer migration.
