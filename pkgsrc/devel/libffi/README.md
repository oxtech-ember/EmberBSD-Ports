# libffi tool selection

The shared recipe requires `readelf` for non-Darwin targets. Darwin uses Mach-O
objects and does not need this ELF utility, including during the initial Clang
bootstrap. No replacement command or forced configure result is installed.

In the pinned [libffi 3.8.0 configure source](https://github.com/libffi/libffi/blob/v3.8.0/configure.ac),
`READELF` only inspects writable ELF `.eh_frame` section flags. Tool discovery
is optional and that check retains its existing read-only result if the tool
is absent. The AArch64 assembly uses CFI directives; the
[x86-64 assembly](https://github.com/libffi/libffi/blob/v3.8.0/src/x86/unix64.S)
selects its Apple `__TEXT,__eh_frame` section separately. The recipe leaves
those upstream checks and all runtime code unchanged.

Run the finite metadata regression with an explicitly selected BSD make:

```sh
python3 -B profiles/common-build-tools/tests/libffi-tools.py \
  --bmake /absolute/native-prefix/bin/bmake \
  --makefiles /absolute/native-prefix/share/mk \
  --shell /absolute/native-prefix/bin/mksh
```

It parses the complete recipe with empty framework includes for Darwin,
NetBSD and Linux. Two deliberately wrong selections must fail its checks.
This validates recipe tool metadata, not a libffi build or execution test.
