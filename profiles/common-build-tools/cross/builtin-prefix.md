# Built-in package root in cross builds

`mk/buildlink3/bsd.buildlink3.mk` sets `BUILDLINK_PREFIX.<pkg>` for a package
that comes from the base system (`USE_BUILTIN.<pkg>=yes`). Upstream pkgsrc
uses `${OSX_SDK_PATH}/usr` when `OSX_SDK_PATH` is defined. It does not check
`OPSYS`.

The macOS host prefix sets `OSX_SDK_PATH` for native host packages, and the
cross `MAKECONF` includes that host file. A cross build for NetBSD then put
the base editline, gettext, iconv, termcap, curses, xz and bzip2 in the macOS
SDK. Package detection used the sysroot, so no ELF file used a macOS header
or library. The AArch64 Clang cross packages of 27 October 2026 show these
effects:

- chrony lost `-I/usr/include/readline`, and `chronyc` has no line editing.
- python315 recorded SDK include and library flags for `_lzma` in
  `config-3.15/Makefile` and in its sysconfig data.
- gnutls recorded an SDK `--with-libintl-prefix` in `+BUILD_INFO`.

`patches/pkgsrc-buildlink-darwin-sdk-prefix.patch` uses the SDK prefix only
when `OPSYS` is `Darwin`. Native Darwin builds and native dependencies of a
cross build keep it. A cross target uses `/usr` below `TOOLS_CROSS_DESTDIR`.
A `USE_CROSS_COMPILE` test is not sufficient: cross-libtool runs with
`USE_CROSS_COMPILE=no` and a NetBSD `OPSYS`.

Run the check with the cross `MAKECONF` of the host:

```sh
python3 -B tests/cross-builtin-prefix.py --pkgsrc EXPORT \
    --makeconf CROSS_MAKECONF --bmake "BMAKE -m SYS_MK_DIR" --work NEW_DIRECTORY
```

It gives a foreign `OSX_SDK_PATH` on the command line. It checks the cross
prefixes of chrony and python315, and the native Darwin prefix of chrony.
It builds nothing.

The phase caches of a kept work directory record the old prefix. Run
`make clean` before you rebuild an affected package.

A cross compiler does not put `-I` paths below its sysroot. The cwrapper kept
`-I/usr/include/<subdir>`, for example `/usr/include/readline` from the
editline built-in, as a build host path. On a Linux host that path can name
host headers. `patches/pkgsrc-cross-base-include-subdirs.patch` maps these
subdirectories to the target sysroot in a cross build and keeps the same
sysroot paths from pkg-config. The base directory stays a default search path.
Native builds keep the previous rules.

Check it with the cross `MAKECONF` and the installed cwrapper:

```sh
python3 -B tests/cross-base-include.py --pkgsrc EXPORT \
    --makeconf CROSS_MAKECONF --bmake "BMAKE -m SYS_MK_DIR" \
    --cwrapper HOST_PREFIX/libexec/cwrappers/cc-wrapper --work NEW_DIRECTORY
```

It runs the real `cc-wrapper` with the chrony rules and a program that prints
its arguments. It builds nothing.

One limit remains. The sqlite3 autosetup script skips its readline header
search in a cross build, so sqlite3 needs explicit readline options.
