# Shared Cppcheck 2.22.0

This recipe follows the [official stable release](https://github.com/cppcheck-opensource/cppcheck/releases/tag/2.22.0).
The upstream repository moved to `cppcheck-opensource/cppcheck`.
One recipe supplies CLI analysis, rules, HTML reports, manual pages and tests.
The optional `qt6` GUI uses common Qt 6 providers. The legacy `qt5`
option maps to `qt6`; it does not select an older Qt stack.

## Shared providers

Rules remain enabled. Their XML engine name stays `pcre`.
The source port uses common PCRE2 10.47 or newer with 8-bit code units.
[`pcre2_next_match()`](https://www.pcre.org/current/doc/html/pcre2_next_match.html)
supplies global-match progression, including empty matches and UTF-8 boundaries.
Match data uses scoped ownership, including callback errors.
Provider pkg-config metadata controls include, link and static/DLL flags.
The recipe does not force `PCRE2_STATIC` on Windows.

TinyXML2 and Boost headers come from the common Ports owners.
The finder selects the installed `boost_headers` CMake config directly.
It needs no Boost libraries package or second copy of Boost headers.
SimpleCpp and PicoJSON come from their common Ports owners.
Their implementations match the bundled sources. SimpleCpp adds an installed ABI guard to its header.
CMake requires both providers and has no bundled fallback.
The SimpleCpp 1.9.1 config requires the exact release to avoid unverified C++ ABI changes.
Its public target selects the checked libstdc++ ABI for the library and consumers.
`cppcheck-core` propagates that target requirement to its own dependents.
`CPPCHK_GLIBCXX_DEBUG` remains enabled; no Debug diagnostics are disabled.
The package preserves the complete upstream configuration, addon and platform data.
The GUI also installs its translations, desktop file and icons.

The former `USE_Z3=yes` variable was ignored by upstream 2.8 and 2.22.
It selected no solver backend. The unused Z3 dependency is removed.
The existing `Token::astStringZ3()` format API remains unchanged.
This change does not claim a Z3 solver integration.

## Build and test contract

The recipe uses the upstream CMake build for all selected components.
It binds the selected Python, pkg-config, xmllint, xsltproc and DocBook stylesheet.
The native generator uses `TOOL_PYTHONBIN`; installed scripts use target `PYTHONBIN`.
The DocBook stylesheet comes from the tool provider under `TOOLBASE`.
Cross GUI builds use the existing Qt host-tools contract and `QT_HOST_PATH`.

`DISABLE_DMAKE=ON` disables only maintainer regeneration dependencies.
The shipped Makefile and project descriptions remain present and current.
The `dmake` and `run-dmake` developer targets remain available.
The recipe does not execute a target generator during a cross build.
This setting removes no CLI, rule, report, GUI or test source.

Run `tests/source.py --sdk-source /absolute/SDK --help` for source/hash/patch
and install-roster checks. Supply the pinned archive, selected patch command,
selected CMake and a new work directory through `--archive`, `--patch`, `--cmake`
and `--work`. The source check configures a `LANGUAGES NONE` fixture for the
patched Linux/Clang option path: ON must preserve the common provider's
`_GLIBCXX_DEBUG` ABI, OFF must retain upstream's `-U` behavior, and the original
module must fail the ON negative control. It does not invoke a compiler.
The new `TestRegExPcre` cases cover empty matches, empty input, lookaround,
large capture sets, UTF-8, match errors and callback exceptions.
They are prepared for the ordinary upstream test runner.

Run `tests/metadata.py --sdk-source /absolute/SDK --help` for recipe evaluation.
Supply an exported tree, make configuration, selected bmake and complete environment JSON.
Use `--pkgsrc`, `--makeconf`, `--bmake`, `--environment` and a new `--work` directory.
The check evaluates default, Qt6 and legacy Qt5 options without configuration or compilation.
It rejects missing generator paths and checks native XML tools under `TOOLBASE`.
It also checks both provider recipes and the ZoneMinder dependency edge.
Run `tests/dependencies.py` with `--sdk-source`, `--archives`, `--patch` and a new `--work` directory.
That gate checks four source archives, all carried patches and exact provider-source identity.
Its negative control rejects reintroduction of a bundled SimpleCpp CMake target.

## Clang AST file locations

The importer emits tokens one top-level declaration at a time. Header names
encountered later may be appended to the file table without changing existing
indices or the language fixed by the TokenList constructor. The source file
must still be registered before creating tokens. The shared patch retains
that assertion and the nonempty-name assertion.

`TestClangImport::multipleFiles` covers two headers, return to the first
header, the main source, exact line/index mapping and C++ token language
despite a header with a `.c` suffix. The original analyzer aborts on both
this case and a real Clang two-header input; the patched analyzer passes.
The full Clang import and TokenList suites pass with the new case.

The location lexer preserves nested pseudo-file delimiters such as
`<<built-in>:line:column>`. The upstream stdin case and new built-in, stdin,
and scratch-space cases verify exact file/line mapping. A second-coordinate
pseudo-file and physical filenames containing `<` preserve their boundaries.
Malformed and
unterminated locations still produce `internalAstError`. Real Clang output
from a small `#line` input fails before this patch and passes with it.

This does not qualify arbitrary LLVM translation units. With both location
fixes, analysis of LLVM's NetBSD driver and of Cppcheck's changed token-list
and importer modules reaches an unrelated token-type assertion in `Token::update_property_info`.
Those analyses remain incomplete. Paired Clang Static Analyzer runs on the
token-list module retain the same two existing diagnostics outside the changed
function; no diagnostic is introduced by the file-table change. Original and
patched importer modules both pass Clang Static Analyzer without diagnostics.

On Darwin arm64, isolated ASan/UBSan modules pass the five positive location
cases and six TokenList cases. The invalid-location case terminates with an
uncaught `InternalError` in that diagnostic build, while the ordinary test
runner catches the expected error and passes all 105 cases. Sanitizer coverage
of the exceptional path remains incomplete; this is not a Valgrind result.

The packaging and PCRE2 adaptation are AI-assisted EmberBSD work.
Source and metadata checks do not qualify an analyzer executable.
Native Darwin arm64 2.22.0nb4 package build and replacement installation passed
with Clang 23.1.4. Installed-file checks covered 84 files; the selected analyzer
reported version 2.22.0, accepted a safe C input and rejected a deliberate null
dereference. The nb3/nb4 changes also passed isolated module and upstream
executable checks described above. This Darwin artifact is not the later nb5
Linux Clang/libstdc++ configuration revision. The full upstream suite, arbitrary translation-unit
analysis, HTML/GUI behavior, cross execution and package lifecycle remain separate checks.
