# Common SWIG 4.5.1

The canonical `devel/swig4` provider uses the current stable SWIG 4.5.1 source.
The common tools, graphics, media and Plasma exports use this same recipe.
They also use the same PCRE2 10.49 recipe from `common-graphics`.
The default and development-only exports retain their upstream providers.

The recipe retains every upstream language backend, CCache compression and
the established `swig4.0`, `ccache-swig4.0` and `share/swig/4.0` interfaces.
It uses the common PCRE2 and zlib packages.
No language, library interface or runtime feature is disabled.
The full static PLIST contains 846 files: two programs, 839 upstream templates
and five original license or copyright notices.

## Source and attribution

The recipe retains its pkgsrc RCS attribution.
The source is the official [SWIG 4.5.1 release](https://www.swig.org/download.html),
with tag `v4.5.1` at commit `88649f559942c29a228fa783dd01581e217bcb20`.
The official archive is `swig-4.5.1.tar.gz`, with SHA256
`7fec50b27deddab5455a9633780b6341eddfb96215a7619e93a76eb27178f653`.
[sources.tsv](../sources.tsv) and the recipe `distinfo` retain the URL and hashes.
The package installs `LICENSE`, `LICENSE-GPL`, `LICENSE-UNIVERSITIES`,
`COPYRIGHT` and `CCache/COPYING` without changes.

The local CCache patch fixes an error path when inherited stderr is closed.
The original code tries to create its stderr descriptor before it initializes
the original compiler arguments. When `dup(2)` fails, compiler fallback
dereferences the missing argument list.
The repair resolves the real compiler and initializes that list before stderr
setup. It also declares the existing non-returning fallback contract for GNU
compilers. Both POSIX and Windows fallback paths retain their exec/exit behavior.

The [regression](../tests/swig-ccache.rb) closes the actual inherited descriptor,
compiles the unmodified upstream example with GCC16, and compares its object
with genuine compressed-cache miss and hit results. The baseline terminates
with SIGSEGV; the repaired packaged executable passes all three paths.

## Native package checks

The ordinary Linux/GCC16 package passes the normal pkgsrc checks.
Its complete stage, static PLIST, package ownership and all 846 payload files
match. An independent inventory uses the real upstream install rules and each
language group's `extra-install.list`. All 839 templates and five notices
match upstream source bytes.

The unmodified upstream `Examples/python/simple` builds through its upstream
Makefile with the common native Python 3.15 provider. The installed binding
returns `gcd(42, 105) == 21` and changes `Foo` from 3.0 to 3.1415926.
The repaired package contains the byte-identical SWIG executable.
The actual packaged CCache also passes the closed-stderr and compressed-cache
contract with identical object hashes.

One complete `common-build-tools` export matches both canonical recipes.
All 137 exporter preflight refusal checks pass.
This does not establish the complete positive composition matrix.

## Analysis and remaining acceptance

Analysis uses the real native build flags for the Python backend, preprocessor
and CCache translation units. Clang 19 reports no findings for the backend or
preprocessor. GCC16 `-fanalyzer` reports no findings for the preprocessor.
Both analyzers reproduce the CCache fallback defect before repair and report
no findings for that translation unit after repair.
Cppcheck 2.22 retains preprocessor/style findings and stops at actual Linux
signed-128-bit and GCC C++ header declarations. Its incomplete parsing is not
a completed analysis result.

Strict Valgrind 3.24 checks remain nonclean, with no suppressions.
The upstream Python generation records 24,804 definitely lost bytes and
139,282,001 reachable bytes in the process-lifetime DOH allocation paths.
The packaged CCache cache-hit check records 18 definitely lost bytes and
562 reachable bytes. The unpatched CCache has the same 18-byte loss;
reachable argument storage varies with the actual command paths.
Neither program has strict memory acceptance.

These results establish ordinary native packaging and focused Python/C compiler
behavior. Target GCC16 cross packaging, installed EmberBSD execution, the full
upstream language test matrix and complete KiCad bindings remain separate checks.
