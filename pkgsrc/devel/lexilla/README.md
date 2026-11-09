# Lexilla provider

This common recipe builds Lexilla 5.5.5 as a versioned shared library, with the
complete upstream generated lexer catalogue and all `lexers/Lex*.cxx` and
`lexlib/*.cxx` implementations. CMake uses the selected native or cross compiler,
C++17 and PIC; it does not invoke upstream makefile host detection, universal
macOS flags, or an undeclared compiler. Tests alone require C++20 upstream.

The dependency on `devel/scintilla-core` supplies public `ILexer5`/`IDocument`
headers. Lexilla links `Scintilla::Headers`, not `Scintilla::Core`, and has no GUI
backend or editor-core link dependency. The core is a build dependency: its headers and archive are not required
to run an installed Lexilla DSO.

```cmake
find_package(Lexilla CONFIG REQUIRED)
target_link_libraries(frontend PRIVATE Lexilla::Lexilla)
```

Autoconf consumers use the `lexilla` pkg-config module. It propagates the public
`scintilla-headers` include directory. Lexilla's own headers and lexer identifiers
live under `include/lexilla`. Include `ILexer.h` before `Lexilla.h` in C++ code.
`CreateLexer` returns an `ILexer5*`; the caller must call its `Release()` method,
not `delete`. This direct-call API is exported by the DSO as upstream defines it.
The source-only `AddStaticLexerModule` extension is not a DSO export contract.

The upstream `access/LexillaAccess.cxx` is provided once as the PIC archive
`liblexilla-access.a` / `Lexilla::Access` / `lexilla-access.pc`, with
`LexillaAccess.h`. Frontends use it to load additional lexer libraries instead
of carrying their own loader copy. Its upstream direct-call mode uses the linked DSO catalogue by default, without
searching a producer path. This does not
change upstream plugin lifetime, namespace or semicolon-separated path rules.

`Makefile.common` owns source selection and patch/preparation paths. This
preparation does not yet migrate wx, Scintilla's old GTK widget recipe, or SciTE;
their consumer adaptations and package acceptance remain separate work.

## Source and verification

The [official current release](https://www.scintilla.org/LexillaDownload.html)
is 5.5.5. The [source archive](https://www.scintilla.org/lexilla555.tgz) has
SHA256 `fa4093ad5c48acf49a6f3eca1b75143a5c824ef1a6f5b0ee59e8c3d6a970f229`.
The upstream HPND `License.txt` is installed intact. No lexer implementation or
generated catalogue is changed by this packaging.

The explicit `tests` package option builds the provider's installed-interface
contract test and upstream `TestLexers` against the DSO. The contract enumerates
the catalogue, checks Python/C++/JSON availability, rejects an unknown lexer, and
checks creation, ILexer5 identity and release. Upstream tests exercise actual
lexing/folding against their shipped example corpus, using upstream's direct-call
mode; its `LEXILLA_STATIC` macro selects calls, not a second static library here.
`bmake test` runs CTest on a compatible runtime. The standalone `tests/` CMake
project also accepts an installed package and the selected toolchain. Cross-built
tests require the target or an explicitly configured emulator.

Archive integrity and source-set inspection are checked. The native source
build with the selected Clang 23.1.4 passed, as did the provider contract and
upstream lexer corpus. Installed CMake and pkg-config consumers compiled and
linked; both ran against the staged prefix with its library directory on the
loader path. These are diagnostic source-build checks, not a Ports package
install. Target package builds and frontend/GUI acceptance remain pending.
