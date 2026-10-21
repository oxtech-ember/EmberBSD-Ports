# libxslt RVT ownership candidate

The prepared common profiles select `libxslt-1.1.45nb1`. Its source repair
keeps result value tree (RVT) ownership lists outside XML document sibling
links. XPath must not traverse an implementation list as XML siblings.
The source delta preserves the upstream source archive, licences and authorship.
It does not disable package vulnerability checks or change the audit database.
Normal package acceptance and dynamic memory checks remain pending.

## Source provenance and scope

The upstream archive is
`https://download.gnome.org/sources/libxslt/1.1/libxslt-1.1.45.tar.xz`.
Its SHA256 is
`9acfe68419c4d06a45c550321b3212762d92f41465062ca4ea19e632ee5d216e`.

The core source patches adapt Daniel Cheng's
[upstream MR77](https://gitlab.gnome.org/GNOME/libxslt/-/merge_requests/77),
head `a3139eabb3e204f62e42ae226c8eeea964611733`.
That proposal remains unmerged. The corresponding
[Debian 1.1.45-0.1 patch](https://sources.debian.org/data/main/libx/libxslt/1.1.45-0.1/debian/patches/77.diff)
has 22,066 bytes and SHA256
`013cdd55ce00d5e2e0802c4b58f8b4cdb2618e0564f1aaa752269c24b31fbce3`.
The EmberBSD adaptation also assigns `list->RVT = RVT` in `xsltReleaseRVT`.
Without that assignment, the proposed public release wrapper dereferences NULL.
Internal ownership transitions reuse existing list nodes without allocation.
Variable evaluation obtains its list before a document and frees the list if
document creation fails. List-transfer helper declarations require `IN_LIBXSLT`.
Local corrections and their tests are AI-assisted work, not an upstream acceptance.
Four additional EXSLT source patches handle registration failure before an
unowned document can escape. Global variable evaluation has the same check.

The repair addresses the RVT ownership cause described in
[CVE-2025-10911 / issue144](https://gitlab.gnome.org/GNOME/libxslt/-/issues/144).
It does not repair source attribute `atype` flag storage in standalone libxslt.
The following distinctions remain necessary:

| Advisory | Scope of this candidate |
| --- | --- |
| CVE-2025-7424 | The unchanged 1.1.45 release already includes the upstream fix. See its [NEWS](https://github.com/GNOME/libxslt/blob/v1.1.45/NEWS). |
| CVE-2025-7425 | The recipe requires `libxml2>=2.15.4`. The checked 2.15.4 source contains the [upstream ID-removal guards](https://github.com/GNOME/libxml2/commit/f1e1f13b766eb580a8dcc0c4e7a447346dfd862e). This is paired mitigation, not a standalone libxslt fix. |
| CVE-2025-10911 | The carried RVT-list candidate and wrapper correction pass the functional checks below. No instrumented UAF acceptance is claimed. |
| Generic GNOME advisory | The [upstream security page](https://gitlab.gnome.org/Teams/Releng/security/-/wikis/2025#libxslt) still lists unresolved issues. A new maintainer does not resolve them. |

The exact checked libxml2 archive SHA256 is
`98087fd181d9070724f3fbc65c7377db03038eb92bd882374daff44940138821`.
Later dependency versions need their own compatibility and applicability checks.
A vulnerability gate must not treat this entire package family as safe.

## Reproduce the functional checks

Run the prepared recipe checks without building or installing a package:

```sh
sh profiles/development-toolchain/tests/source-profile.sh
python3 profiles/development-toolchain/tests/libxslt-source.py /absolute/prepared/pkgsrc
```

Build `tests/libxslt-security.c` with GCC16 against the selected headers and
libraries. Use the same libxml2 prefix for libxslt and the consumer.
For a native installed source pilot:

```sh
"$CC" -O2 -g -I"$XSLT_PREFIX/include" -I"$XML_PREFIX/include/libxml2" \
    profiles/development-toolchain/tests/libxslt-security.c \
    -L"$XSLT_PREFIX/lib" -L"$XML_PREFIX/lib" \
    -Wl,-rpath,"$XSLT_PREFIX/lib" -Wl,-rpath,"$XML_PREFIX/lib" \
    -lexslt -lxslt -lxml2 -lm -o /absolute/new/libxslt-security
python3 profiles/development-toolchain/tests/libxslt-security.py \
    /absolute/new/libxslt-security /absolute/new/results
```

For a cross build, compile with the common target GCC16 and run the executable
and Python runner on the target. These source patches do not require native
configuration probes or target execution during a cross package build.
Inspect `ldd` and `xsltproc --version` before interpreting the result.
An old library from another prefix invalidates the paired check.

The runner executes twelve separate processes. It checks independent RVT
siblings for persistent, local and temporary registration; XPath axis controls;
release without a context; release with a cache; cache saturation and reuse;
a NULL RVT; paired ID cleanup; and one hundred EXSLT transformations.
The EXSLT case covers global/local fragments, `node-set`, `key` and function
results with the independently expected output `global:local`.
The ID check changes the attribute type flags and requires ID lookup removal
after attribute destruction. It does not dereference a freed attribute.

The additional allocation checks use the actual configured `transform.c` and
`variables.c` translation units with the other production PIC objects.
Standard `xmlMemSetup` hooks deny selected allocation sizes deterministically.
The checks use valid, owned local documents. They cover persistent and function
result transfers, selected-variable ownership, stack cleanup, fresh/cached
variable evaluation and document allocation failure. Targeted document/list
accounting reaches zero after cleanup; this is not a general memory checker.
Three compiler controls check the public API and private helper declaration.

Run them with a configured native GCC16 build and a new output directory:

```sh
python3 profiles/development-toolchain/tests/libxslt-alloc.py \
    /absolute/configured/libxslt-1.1.45 /absolute/libxml2-prefix \
    /absolute/new/allocation-results --cc /absolute/gcc16/bin/gcc --ar /usr/bin/ar
```

The fresh-document fixture checks seven registration callers and seven normal
success controls. It covers global variables, EXSLT `node-set`, content-based
`func:result`, `tokenize`, `split`, string return and dynamic `map`.
One list allocation is denied after the fresh document allocation. Each error
must be visible, and the unregistered document must be freed. Normal controls
check independent text/node-set results and final document/list accounting.

```sh
python3 profiles/development-toolchain/tests/libxslt-fresh.py \
    /absolute/configured/libxslt-1.1.45 /absolute/libxml2-prefix \
    /absolute/new/fresh-results --cc /absolute/gcc16/bin/gcc --ar /usr/bin/ar
```

`tests/libxslt-layout.c` compares relevant structure sizes and offsets.
Compile it with the original headers, then with repaired headers and `-DFIXED`.
These checks preserve layout; they do not promise the same private field names
or direct access semantics for the changed implementation lists.

## Executed native evidence

GCC16.2.0 built both releases on NetBSD11/amd64 with one build worker.
The isolated libxml2 2.15.4 pilot disabled Python, iconv and zlib, and retained
legacy/HTTP compatibility interfaces. The libxslt pilot used its default
crypto/plugin options and disabled Python. The normal recipe retains crypto
and plugin support; their package integration is not accepted by this pilot.

| Build | Functional result |
| --- | --- |
| Original 1.1.45 | 9/12 pass. Three RVT sibling-isolation cases fail. |
| Unchanged MR77 | 9/12 pass. Three release-wrapper cases terminate with SIGSEGV. |
| Corrected candidate | 12/12 pass. |
| Installed candidate after source reinstall | 12/12 pass. |
| Original-header consumer linked to repaired libraries | 12/12 pass. |

The ownership/header regression passes 11/11 checks after the review corrections.
The first candidate passed 3/11: seven ownership cases failed, and the helper
was incorrectly visible in the public header. The positive document-allocation
error control already passed.

The fresh-document fixture passes 14/14 after its corrections. Before them,
all seven normal controls passed. All seven allocation failures lost a document
and failed to report the operation error. The corrected error paths free the
document and propagate XPath, transformation or function errors.

Full upstream `make check` returns zero before and after the repair.
Each run reports 747 tests and no errors. Both emit the upstream C-locale
collation warning. The positive XPath controls also pass before the repair;
they are not presented as reproductions of the UAF.
The original upstream exploit attachments were not used.

Isolated source install, uninstall and reinstall return zero.
The consumer loads only its selected libxslt, libexslt, libxml2 and base C,
pthread and math libraries. Actual runtime versions are libxml 21504,
libxslt 10145 and libexslt 825. All 232 libxslt and thirteen libexslt defined
public function symbol names remain present, with no additions or removals. Checked structure sizes and
mapped field offsets match. Normal pkgsrc package lifecycle remains untested.

Static analysis covers six translation units: `transform.c`, `variables.c`, and
EXSLT `common.c`, `functions.c`, `strings.c` and `dynamic.c`.
The comparison uses configured NetBSD headers and settings before and after the
fresh-registration correction. GCC16 `-fanalyzer` reports no warnings in either
version. Cppcheck2.22 reports the same 38 diagnostics and returns one.
Clang23.1.1 Static Analyzer reports the same nine diagnostics in both versions.
Their diagnostic-message multisets have no additions. These inherited findings
include potential NULL arguments and redundant checks; they remain an upstream
analysis debt, not a clean static-analysis result. No suppressions were added.

Valgrind is absent on the checked host. The accepted GCC16 seed explicitly
disables sanitizer runtimes; neither `libasan` nor `libubsan` is available.
No Memcheck, ASan or UBSan success is claimed. Exit-zero functional results do
not prove memory safety. Additional allocation-failure paths, instrumented UAF
checks, full package integration, cross execution and downstream Qt/KDE
acceptance remain separate gates. The generic advisory remains open.
