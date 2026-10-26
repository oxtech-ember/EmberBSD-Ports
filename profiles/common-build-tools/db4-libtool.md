# Berkeley DB libtool language selection

The common db4 recipe selects explicit C and C++ libtool tags after configure.
The compiler, fixed arguments, compile/link modes and library ABI remain unchanged.
`PKGREVISION` is 2.

Libtool can record a compiler with fixed arguments, such as `clang -std=gnu23`.
Berkeley DB previously passed an untagged `clang` command. Automatic language
inference then failed before compilation. The common recipe now tags `CC`,
`CCLINK` and `SOLINK` as C, and `CXX`, `CXXLINK` and `XSOLINK` as C++.

The Linux regression uses the actual configured Berkeley DB Makefile and
pkgsrc compiler wrappers. Supply the SDK native command mapping so bare tool
names such as `ar` resolve to the selected prefix's LLVM tools.

```sh
"$HOST_PREFIX/bin/python3.15" profiles/common-build-tools/tests/db4-libtool-tags.py \
    --makefile "$DB_WORK/db-4.8.30/build_unix/Makefile" \
    --wrapper-config "$DB_WORK/.cwrapper/config" \
    --native-tools "$NATIVE_TOOLS" --host-prefix "$HOST_PREFIX" \
    --work "$NEW_TEST_OUTPUT"
```

The check compiles and calls real C/C++ shared libraries, then links and runs
both executable forms. Each result must be 42. `--expect-rejection` requires
the old configured command to fail specifically at libtool language inference.
It does not accept an unrelated compiler, header or wrapper error as a baseline.
Shared-library loading uses the Linux `.so` convention; other hosts need their
own loader checks. These checks do not establish target Berkeley DB execution.

On Linux with Clang 23.1.4, the old configured C command reproduced the tag
inference failure. All six repaired command roles passed the executable and
shared-library checks. The complete db4-4.8.30nb2 package passed its normal
file checks and installation. Installed `db4_load`, `db4_verify` and `db4_dump`
preserved the expected B-tree key/value pair. The upstream full test suite and
package removal/reinstallation were not run during this host-tool repair.
