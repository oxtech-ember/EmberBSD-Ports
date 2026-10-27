# Retro68 native resource tools

This recipe builds upstream Retro68's Rez and ResInfo from commit
`0cbd3cb918a127a0d30a675b337f8f8e15062786`, using the common Boost and
libhfs packages. The narrow CMake option leaves ResourceFiles disk-image
support enabled; it does not build the Retro68 cross compiler.

`Rez --input-format=text` accepts text independently of its filename;
`binary` selects binary resource inputs, and the default `auto` retains the
upstream extension rules. On macOS, `--resource-fork-only --append` merges
resources into the native resource fork of an existing regular file without
writing its data fork or FinderInfo. Input parsing and fork serialization
complete before the write. Other hosts refuse this mode. An I/O error is
reported; the filesystem determines the state of the fork after a failed
write. Callers that require transactional output should work on a copy.

After building, run the CLI test on macOS with selected Python and the built
Rez. The optional fixture may be a Mach-O executable; omit it to use ordinary
file contents. The scratch directory must already exist.

```sh
"$HOST_PREFIX/bin/python3.15" -B pkgsrc/devel/retro68-rez/tests/resource-fork.py \
  --rez "$REZ" --work-dir "$WORK" --fixture "$MACHO"
```

The test checks existing resources, their names and attributes, replacement
resources, text and binary input,
malformed input, write errors, and preservation of data, mode, FinderInfo and
another extended attribute. It does not claim target runtime support.

`tests/fork-validation.cc` checks the real ResourceFork implementation with
valid, truncated and out-of-range maps. Compile it with the selected native
C++ compiler, the prepared source's `ResourceFiles` include directory and
its `ResourceFork.cc`, `BinaryIO.cc` and `ResType.cc` files. The same test can
be run with ASan/UBSan where supported.

The complete Rez CLI has not passed a sanitizer run. An instrumented build
reported a container overflow while using an uninstrumented Boost.Wave; the
cause has not been established. Ordinary native package and resource-fork
checks have separate scope.
