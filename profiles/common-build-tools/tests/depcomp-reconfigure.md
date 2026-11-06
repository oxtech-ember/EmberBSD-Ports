# Native depcomp reconfigure regression

`depcomp-reconfigure.py` exercises the pkgsrc `depcomp-override` target
with selected native Autoconf, Automake, Clang, bmake, gmake and shell. The
negative input is the old wrapper-based `libtool-override.mk`; the positive
input is the prepared file with the current common Ports patch applied.
Use separate prepared source inputs, not an active build or shared export.

Run with the selected native SDK Python and explicit paths:

```sh
python3 depcomp-reconfigure.py \
  --prefix /path/to/native-prefix --tools /path/to/native-tools \
  --old-mk /path/to/old/libtool-override.mk \
  --new-mk /path/to/new/libtool-override.mk \
  --output /path/to/new/empty-test-directory
```

The tools directory provides the selected `sh` and command aliases. The test
creates `old` and `new` subdirectories and fails if they already exist. It
checks that the old second configure loses dependency tracking, the new one
selects `gcc3`, a no-change build preserves the object, and a changed header
rebuilds the object and changes the executable's result. It tests the native
host tool path; it does not claim cross-target execution coverage.
