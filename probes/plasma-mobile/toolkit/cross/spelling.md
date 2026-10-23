# Spelling dependencies for the full desktop

On 2026-10-12, macOS/GCC16 cross-builds produced complete Aspell 0.60.8.2nb2,
Hunspell 1.7.5nb1 and Sonnet 6.31.0nb2 packages for EmberBSD/AArch64.
All three install normally in the common sysroot and on physical CM5.
Their normal manifest, dependency, interpreter, permission, PIE, RELRO,
runtime-path and build-reference checks pass. Both Sonnet backends are retained.

[Hunspell 1.7.5](https://github.com/hunspell/hunspell/releases/tag/v1.7.5),
released 4 October 2026, is the selected current upstream release.
[Aspell 0.60.8.2](https://github.com/GNUAspell/aspell/releases) is the current
Aspell release. [sources.tsv](../sources.tsv) pins the original archives and hashes.
Inherited pkgsrc authorship, licenses and platform patches are preserved.

## Repairs

The common graphics [Hunspell delta](../../../../profiles/common-graphics/cross/current-hunspell.patch)
selects Hunspell 1.7.5nb2 and the current US English dictionary.
Both dictionary recipes used `perl:run`, which pkgsrc rejects in cross builds.
The native interpreter now performs build operations; installed scripts retain
`/usr/pkg/bin/perl` and depend on the current target Perl package. Native recipe
behavior stays unchanged. `tests/spell-cross.rb` exercises the actual recipes,
including missing-host-interpreter rejection.

Hunspell's manifest includes its new public `hunversion.h`. A clean package
rebuild is required after correcting an earlier staged manifest; reusing old
package metadata omitted this header and broke the real Sonnet consumer.
The inherited Solaris patch only needed context refreshed for 1.7.5.

Cppcheck found an actual Aspell bug: `.spcl` and `.special` dictionary suffixes
were compared using six characters, although they contain five and eight.
The original installed package rejects valid multi-dictionary files with both
extensions. The Ports patch repairs the lengths. Both files then load and
recognize a word; the same content under an unknown extension still fails.

Sonnet's upstream cross path omitted the packaged `parsetrigrams6` executable
and could silently omit language-model resources when no host generator exists.
The patch builds the target tools and runs a separate imported native generator.
A missing generator is now fatal. Widgets, QML, Designer and both backends remain
in the target package. The native helper builds only the build-time executable:

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ \
sh cross/build-sonnet-tool.sh DISTFILES HOST_QT ECM_CMAKE_DIR NEW_WORK
```

Expose `NEW_WORK/bin/parsetrigrams6` as
`${EMBERBSD_KF6_HOST_TOOLING}/bin/parsetrigrams6` before building Sonnet.
Use the same Qt 6.12 generators and common EmberBSD sysroot as the other modules.

## CM5 acceptance

CM5 Rev 1.0 / BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B uses the operator's
`EMBERV3DRENDER #0` fan-update kernel from
`ab6f88f04ca73c6958adb39d0e1c717f629e7901`. Original firmware/carrier revisions
are unknown. The test intervals preserve the boot identity.

- Aspell passes unchanged upstream sanity checks, all 50 Markdown cases and
  the valid/secure wide-string API cases. The unsafe null-terminated wide-string
  call is rejected with the expected diagnostic. The suffix repair has both
  the original-failure control and installed positive/negative checks.
- Hunspell runs all 174 entries from its upstream test list: 172 pass and two
  skip. The ABI shell test excludes non-Linux systems; `gh211` requires absent
  gawk. The other cases include the upstream malformed-input regressions.
- Normal deletion/reinstallation of both new packages passes; package tools
  check 166 files. Both installed Perl scripts pass syntax checking with target
  Perl 5.44.0nb3. The new Hunspell header is present in the installed package.
- Sonnet's installed target generator reproduces the native generator's full
  language-model bytes. Five unchanged core suites report 20 passes and nine
  skips. Both backend plugins load. Dictionary-dependent cases skip because
  the plugins do not discover the isolated test dictionaries. These results
  do not establish language detection or suggestions in the desktop.

`tests/spell-upstream.rb` cross-builds the original C/C++ test consumers and
bundles the upstream test data. It takes `ASPELL_SOURCE HUNSPELL_SOURCE
DISTFILES CROSS_TOOLS SYSROOT NEW_OUTPUT`. Transfer the generated bundle,
verify its SHA256 manifest, then run `sh run.sh BUNDLE NEW_RESULTS` on EmberBSD.
The dictionary generator runs on the board; no target C/C++ compilation occurs.
`tests/sonnet-runtime.sh` takes a fixture directory containing the five upstream
executables, `trigrams/` and `native.map`, the private Aspell dictionary directory,
and a new result directory.

The Aspell upstream test fixture uses these exact additional archives:

| Fixture | SHA256 |
| --- | --- |
| [English test dictionary](https://ftp.gnu.org/gnu/aspell/dict/en/aspell6-en-2018.04.16-0.tar.bz2) | `f11071e74b0c0753f4afabf024941a5c3a96bafe3879211ebd47bc34e76fbd2f` |
| [IPC::System::Simple 1.30](https://cpan.metacpan.org/authors/id/J/JK/JKEENAN/IPC-System-Simple-1.30.tar.gz) | `22e6f5222b505ee513058fdca35ab7a1eab80539b98e5ca4a923a70a8ae9ba9e` |

These are private test inputs, not permanent runtime dependencies or the selected
system dictionary release. The original test bodies and expectations are retained.
A small launcher invokes upstream Hunspell's Bash script through `/usr/pkg/bin/bash`.
Installed binaries use a strict `libtool --mode=execute` adapter without build-tree
library overrides. Aspell's Markdown harness requires GNU `diff -u -Z`; a private
text-only adapter normalizes trailing ASCII whitespace and runs the real base diff.
Equal, unequal and unsupported-argument controls verify that adapter before use.

Cppcheck 2.22 examined 67 actual Aspell and 28 actual Hunspell compilation units.
The fixed Aspell unit was analyzed again; the two suffix diagnostics disappeared.
Inherited allocation-failure, initialization and other warnings remain, so neither
analysis is clean. Hunspell's pointer-size warnings refer to deliberate pointer
serialization; no suppression was added. Allocation exhaustion was not tested.
Valgrind has no accepted EmberBSD/AArch64 runner; no memory-safety pass is claimed.

## Evidence and remaining integration

| Object | SHA256 |
| --- | --- |
| Aspell package | `a9a109c0819ea5a1e2854935bfb20073a69ae748100650c6e4435e508f59648b` |
| Hunspell package | `284f56cf5ea431354a1af6a168695ec939b50270c0b2b2c40be8453b20379b5e` |
| Sonnet package | `0a54cb59dce1e7b1abe173fbb0fcc521ccec24ab8808c1af19713cec09d558d1` |
| Aspell/Hunspell target results | `57ce9b607540ac81d42a64840d9f1f3aac431050a699965fc683bc9553a2c93c` |
| Native and target language models | `3f5ff05e04a87b399d02aba5219359e232d9999a16e11505188115f96e05f5ed` |

All 106 profile archives pass source checks. The final Aspell/Hunspell/Sonnet
patch sets also pass fresh checksums and zero-fuzz application; the final profile
export matches the recipes. The complete KCMUtils chain next reaches QtMultimedia
and FFmpeg dependencies, where LAME 4.0 has a GCC16 pointer-type incompatibility.
KWin, a Plasma login and the accelerated desktop are still unfinished.
