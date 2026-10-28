# rpcsvc-proto native rpcgen

This recipe gives the native `rpcgen` for NetBSD cross builds on Darwin
hosts. `prepare-native-tools.py` selects `bin/rpcgen` from the host prefix
as `TOOLS_PATH.rpcgen`. The Darwin bootstrap installs the package. macOS
`/usr/bin/rpcgen` is not selected.

rpcgen runs `cpp` from `PATH` with a `.x` input file. On Darwin and in cross
builds, `cpp` is a Clang compiler driver. A compiler driver treats `.x` files
as linker input and writes no output, and rpcgen then writes empty files
without an error. `patch-rpcgen_rpc__main.c` gives `-x c` to the
preprocessor. GCC and Clang accept this option.

The macOS SDK has `<rpcsvc/*.h>` files with the same names. On Darwin the
package installs its protocol headers in `include/rpcsvc-proto/rpcsvc`, so
that `-I${PREFIX}/include`, for example from a `pkg-config` file, does not
select them before the SDK headers. `buildlink3.mk` gives this directory
to consumers.

The build-time protocol headers use a `cpp` script that runs `${CC} -E`,
because the native wrapper `cpp` can run the compiler without `-E`.

The generated client code casts `xdr_void` to `xdrproc_t`. The EmberBSD
`xdr_void` has the `xdrproc_t` type, so the cast has no effect. The client
code of a sample protocol compiles with the aarch64 cross compiler and
`-Werror -Wcast-function-type-mismatch`.

Run this check on an installed or staged prefix:

```sh
python3 -B tests/test-native.py --prefix /absolute/prefix --cc /absolute/cc
```

The check runs rpcgen with a `cpp` script that runs `cc -E` without `-x c`,
and fails when the headers or the generated code are empty. On Darwin it
also fails when the protocol headers are in `include/rpcsvc`.
