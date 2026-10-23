# XKB rule merge regression

Fcitx5 5.1.23 parses keyboard models and option groups into temporary lists.
Its `XkbRulesParseState::merge()` moves only layouts into the public result.
The stock dump test returns zero without checking these missing lists.
The patch appends models and groups with move iterators.
It preserves the existing order within each XML file and across parsed files.

Run the real-source regression with prepared native dependencies:

```sh
RUBY=/absolute/ruby sh tests/xkbrules.sh \
    /absolute/fcitx5-5.1.23 /absolute/native-utils-build \
    /absolute/fcitx5-recipe /absolute/native-expat-prefix \
    /absolute/new-results
```

The native Utils build must include `compile_commands.json` and `lib/libFcitx5Utils.a`.
The Expat prefix must contain its headers and `lib/libexpat.a`.
The script uses the recorded native compiler and flags.
It compiles the actual XKB parser, XML parser and separate regression.
It does not replace the XML parser with a fixture implementation.
Use a matching ASan/UBSan Utils build to instrument the same regression.
Do not mix compiler sanitizer runtimes.

Five XML files exercise two directories, their extras and an explicit extra file.
Checks retain every model, group, option and their field values in parse order.
They also cover layouts, version selection, repeated reads and `clear()`.
The group attribute is tested with `true`, `false` and no attribute.
The absent-attribute case preserves the existing value-initialized `exclusive=false`.
No header default or attribute policy changes are made.
Checks remain active with `NDEBUG`.

Native and ASan/UBSan runs pass on macOS with current native Expat 2.8.5.
The original source fails both runs with missing models; the patched source passes.
Clang 23 reports no findings before or after the fix with actual GCC16/AArch64 headers and configuration.
Cppcheck 2.22 stops at `__has_cpp_attribute` in the captured GCC macro configuration.
Its analysis is incomplete. No diagnostic suppression was added.
These checks do not establish Valgrind, leak-checking or target runtime acceptance.
The complete Fcitx package and installed runtime suite require separate acceptance.
