# Installed litehtml checks

These tests exercise the installed shared litehtml package used by Qt Assistant.
They do not claim a rendered Assistant window or an accelerated Plasma session.

The upstream UTF-8 test comes unchanged from litehtml-tests commit
[`2bb4d22d7d2a0916e4ec69e30d71b39bfe3b7b8a`](https://github.com/litehtml/litehtml-tests/tree/2bb4d22d7d2a0916e4ec69e30d71b39bfe3b7b8a),
which litehtml 0.10 pins in its CMakeLists.txt. The archive is
[available upstream](https://github.com/litehtml/litehtml-tests/archive/2bb4d22d7d2a0916e4ec69e30d71b39bfe3b7b8a.tar.gz);
SHA256 is `8d831a6e48f1f319a2597236fd865a1a287e10f6485a7914296145b2263b2032`.
The separate upstream Cairo/GDK image comparison suite is not included here.

`css-flags.cpp` is an EmberBSD regression for two negative shifts found by
Cppcheck. It covers all decoration and emphasis-position keywords, including
zero-valued `none` and `over`, and combinations of nonzero flags. The installed
unpatched 0.10 library fails both tests on CM5; 0.10nb1 passes the same binary.
The [Ports patch](../../../../../pkgsrc/www/litehtml/patches/patch-src_style.cpp)
leaves those zero-valued keywords out of the bit-shift operation.

Build on the development host with GCC16, the common sysroot, installed
litehtml 0.10nb1 and GoogleTest 1.18.0:

```sh
CMAKE=/absolute/cmake NINJA=/absolute/ninja sh build.sh \
    /absolute/cross-tools /absolute/sysroot /absolute/test-archive.tar.gz \
    /absolute/new-work
```

The build uses the package's real CMake exports and shared library.
Copy `new-work/build/litehtml-runtime` and `run.sh` to EmberBSD, then run:

```sh
sh run.sh /absolute/litehtml-runtime /absolute/new-results
```

The runner records the executable hash, loaded libraries, test XML and boot
identity. On CM5 on 2026-10-12, the upstream encoding test and both CSS tests
passed after normal package installation. The CSS tests also passed Cppcheck
2.22 and GCC16 `-fanalyzer` without diagnostics.
See [HTML dependency acceptance](../../cross/html.md) for package evidence
and the wider source-analysis limits.
