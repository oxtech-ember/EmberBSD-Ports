# Explicit common FFmpeg regression

Run `common-regression.py` with the selected host Python, compiler and the
ffprobe built from this recipe. Pass compiler include and link options with
`--cflag=<option>` and `--ldflag=<option>`, and pass the cdsc, rndr, fragment
init and fragment media test paths using the four named options shown by
`--help`. The test compiles `encryption-init-info.c`, exercises list cleanup
under a 256 KiB stack, verifies repeated appends and allocation failure, and
checks the MOV T.35 track and packets using the supplied fixtures. Chromium's
`media/test/data/agtm-metadata-*` fixtures cover those MOV cases; they are test
inputs, not package dependencies. This test is explicit and does not run during
ordinary package builds.

`upstream-regression.py` separately compiles `hdr-avstring-regression.c` with
explicit selected compiler and library flags, then uses the supplied `ffprobe`
with a local loopback RTSP server. It covers HDR saturation with and without
tone mapping, empty and normal replacements, and the eight-redirect limit.
The chosen FFmpeg build must enable the RTSP demuxer and TCP protocol. This
explicit test is not part of ordinary builds.
# FFmpeg native Darwin preset qualification

Build the common FFmpeg recipe with the selected native SDK. Install a portable
candidate into a disposable second prefix containing ffmpeg9 and ffprobe9;
leave the producer prefix intact. The recipe installs tools in `bin` and preset
data in `share/ffmpeg9`. For causal comparison use the old CLI in the same
moved layout, then the candidate:

```
python3 test_presets.py --prefix /absolute/moved-prefix --producer-prefix /absolute/producer-prefix --expect old
python3 test_presets.py --prefix /absolute/moved-prefix --producer-prefix /absolute/producer-prefix --expect new
```

Use the selected SDK Python. The fixture verifies healthy CLI execution,
UUID-named producer absence, default .ffpreset and .avpreset, valid output,
environment and HOME precedence, explicit path, missing lookup and symlink.
It creates and removes its own unique fixtures under the disposable prefix.

Before qualifying with SDK `package-portable.py --relocate-text
--allow-binary-prefix`, unpack the exact candidate and run:

```
python3 check_binary_prefix.py --payload /absolute/unpacked-payload --config-h /absolute/build/config.h --producer-prefix /absolute/producer-prefix
python3 test_check_binary_prefix.py
```

The checker permits only the complete NUL-terminated configure diagnostic
string in binaries; it rejects other binary producer-prefix occurrences. SDK
qualification still checks text and Mach-O dependencies. Preserve the real
configuration and source provenance. The SDK contract also requires a compiler
check at a different prefix; this test does not replace that check.

For changed CLI units run Clang Static Analyzer and Cppcheck using the actual
compile flags, and run the moved CLI fixture with both units instrumented by
ASan/UBSan. Cppcheck 2.22.0 has a reproducible parser limitation on the Darwin
mux unit: direct actual source with the selected SDK headers reports
`AV_VERSION_DOT` token-paste syntaxError; Clang-preprocessed output reports
`pragma .. typedef` syntaxError in `_mach_port_t.h`. Its experimental Clang AST
mode reports `internalAstError`. Reproduce against the actual unit and selected
SDK using the compilation database and `cppcheck --project=COMPILE_DB`, or
preprocess with the recorded Clang command using `-E` and analyze the output.
Compare old and new diagnostics; these parser failures are not a full mux-unit
Cppcheck pass. Do not alter upstream headers or suppress unrelated categories.
