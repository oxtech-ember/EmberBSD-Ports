# Initial GNU make without an installed make

[gnu-gmake.json](gnu-gmake.json) is a fixed initial source-build contract.
Use the common `upstream/pkgsrc/devel/gmake` recipe from the Ports Git link.
Pin that Git link, the recipe, its options, distinfo and all six patches.
Do not represent these upstream files as top-level Ports Git blobs.
The ordinary recipe and its NLS policy stay unchanged.

The GNU Make 4.4.1 release README supports this bootstrap sequence:
run `configure`, then run `build.sh` with the selected shell.
The script reads generated `build.cfg`, compiles every object, creates the
Gnulib archive and links `make`. It does not need an installed make.
Use the accepted native GCC16 command and ABI flags, official LLVM archive
and linker tools, and a source-built selected shell. Pin the whole release
and all canonical patches. Check every published archive checksum and Size.

The SDK fixed recognizer owns the exact two build commands and runtime cases.
It must omit `make` and `gmake` from the initial roles, aliases and environment.
Set `CONFIG_SHELL` and `SHELL` to the selected shell. Add the canonical recipe's
`PKGSRC_DEFAULT_SHELL` definition with that same accepted shell path.
Set `EMBERBSD_BOOTSTRAP_EXPECTED_SHELL` to the same path for the fixed oracle.
Do not add arbitrary command fields or run an installation target.
The build output is `make`; the SDK can select it as the `gmake` role.

The initial mode disables NLS and Guile. It does not replace the ordinary
package or claim either optional feature. Eight finite cases check version,
compiled shell, a spaced variable, recursion through the new make, parallel
dependencies, question mode and two real failure statuses.
The configure and bootstrap commands are sequential. The parallel semantic
case uses two jobs. Keep the SDK heavy-link fence around the bootstrap step.
Compiler provenance, native output, runtime closure, all process groups and
input revalidation need actual SDK checks before initial provisioning.
This manifest and its source checks do not qualify an ordinary toolset.

The source-only check accepts explicit public inputs:

```sh
python3 profiles/common-build-tools/tests/gmake-bootstrap-source.py \
    --ports /absolute/Ports --archive /absolute/make-4.4.1.tar.gz
```

It does not execute a release script, make, shell, compiler or patch tool.
