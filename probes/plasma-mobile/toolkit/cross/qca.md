# QCA and the KWallet dependency

QCA 2.3.12nb1 is the common Qt 6.12 cryptographic provider for EmberBSD.
The complete package includes `qca-ossl`, both CLI tools, headers and CMake
exports. It cross-builds on macOS with GCC 16.2 and the fork's sysroot;
CM5 executes the resulting tests. The source archive is pinned in
[sources.tsv](../sources.tsv), including its upstream URL and SHA256.
No second Qt or compiler runtime is introduced.

## Cross-build corrections

The imported recipe built no cryptographic plugin. Enable OpenSSL, which
KWallet needs for encrypted Secret Service sessions. Normal package dependencies
retain the Qt6 Core5Compat and Mozilla trust-store providers.

Native qmake describes the host prefix. Cross builds explicitly select the
final target paths under `/usr/pkg/qt6`, with manual pages under `/usr/pkg/man`.
Set the common installation prefix and upstream `USE_RELATIVE_PATHS=ON` so
installed CMake imports resolve inside the consuming sysroot. The initial
absolute exports failed KWallet configuration; the corrected exports build
that real consumer. Do not rewrite installed imports to a private sysroot path.

The upstream certstore probe scans the host filesystem even when the cache
contains a target path. Set both its cache value and `QC_CERTSTORE_PATH` to
the target Mozilla bundle; check that the bundle exists in the sysroot.
The regression executes the actual upstream selection block with an existing
host fixture: omission reproduces the wrong host selection, while the recipe
retains the target path. Native builds keep their original discovery behavior.

```sh
BMAKE=/absolute/native/bmake CMAKE=/absolute/native/cmake ruby \
    probes/plasma-mobile/toolkit/tests/qca-cross.rb \
    /absolute/exported-pkgsrc /absolute/cross-mk.conf \
    /absolute/configured-qca-source /absolute/new-check
```

## CM5 acceptance on 2026-10-12

Normal target installation and replacement passed. `pkg_admin check` verified
164 files from Qt5Compat and QCA. The real installed OpenSSL plugin loads;
`ldd` resolves the common target libraries. The kernel boot identity was
unchanged during these tests.

All 25 CTest-listed upstream invocations complete after the test-data repair
below. They cover cipher vectors, hashes, certificates, RSA/DSA, derivation,
MACs, secure arrays, file watching and plugin lifecycle. Upstream tests emit
warnings instead of failures for unsupported optional algorithms/providers,
including MD2, SHA0 and the absent PGP provider. Those warnings do not establish
support. The TLS case checks advertised ciphers, not a network handshake.
This does not certify a complete KWallet session or a production security audit.

The original Hashing invocation failed because its compiled data path pointed
to the build host. The source patch adds `QCA_TEST_DATA_DIR`, preserving the
native absolute default; cross builds select `.` and keep the CTest working
directory. No C++ test body or expected digest is changed. The repaired target
Hashing invocation passes all 65 reported rows; unsupported rows still warn.

```sh
CTEST=/absolute/native/ctest ruby \
    probes/plasma-mobile/toolkit/tests/qca-upstream.rb \
    /absolute/configured-qca-build /absolute/new-bundle
# Transfer the bundle, verify SHA256SUMS, then on EmberBSD:
sh /absolute/bundle/run.sh
```

The runner refuses a developer-mode plugin override and requires `qca-ossl`.
It clears library/plugin path overrides and preserves individual exit statuses.
Use a new bundle for each run; keep the original failure alongside the repaired
Hashing result. The complete package SHA256 is
`0522d731a0081c61ce2cb522b71682da401a6f4a1b8f791517560a015f376b54`.
The CM5 result archive SHA256 is
`4f16d177502a6801d97d763e892e7c30a882bbcebffe1fa59ac61b40aae6dcfe`.

## Analysis and remaining checks

Cppcheck 2.22 inspected the actual compilation database for 147 translation
units, but Qt preprocessing errors and inherited warnings prevent a clean
result. A second attempt on GCC16 target-preprocessed `qca_textfilter.cpp`
stopped on an unsupported target `assert.h` construct. No C/C++ implementation
is changed by this port; the changes are recipe and test-path configuration.
The inherited warnings remain upstream QCA review items, not confirmed port
regressions. Valgrind was not run: this target lacks a supported runner.
No memory-safety certification is claimed.

## Installed KWallet

KWallet 6.31.0nb1 now cross-packages its daemon, query CLI, manual and upstream
D-Bus compatibility activation name. The latter routes to the current provider;
it does not install Qt5. Its complete package SHA256 is
`19c35af52b3a9986591ac91c2f30af928886e1294d0dfe6f580e648c38fe0e0e`.
Normal installation on CM5 and package-file verification pass. Both unchanged
CTest suites pass: 16 FDO Secret Service rows and three Blowfish rows. The FDO
suite mocks persistent storage but uses real QCA/OpenSSL operations, including
short Diffie-Hellman values, sign padding, encryption and invalid UTF-8 rejection.
It does not test an interactive wallet or on-disk secret persistence.

The installed `org.kde.kwalletd5` and `org.kde.kwalletd6` names each activate on a
fresh private D-Bus session. Both start the current wrapper and `ksecretd`, then
answer `isEnabled`. The runner stops only daemon owners on that private bus;
`ksecretd` can otherwise outlive a bus disconnect. Test HOME and runtime paths
are private, and no user's wallet is opened. No reboot occurred during this run.

```sh
# Copy the two upstream _KDE_build/bin test executables, verify their hashes,
# and run against the normally installed package on EmberBSD:
sh tests/kwallet-runtime.sh /absolute/test-binaries /absolute/new-results
```

CM5 result archive SHA256:
`725abb3092b7f001f5400cadaa3c2ae033e60873e8edac42b34177223988ab46`.
The first batch also installed complete Clang 23.1.3 and QtTools 6.12 packages;
`pkg_admin check` checked 2,836 files from 12 packages. The interactive wallet,
desktop authorization, package removal and full Plasma session remain unaccepted.
