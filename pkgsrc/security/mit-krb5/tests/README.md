# MIT Kerberos native relocation regression

`server-paths.py` tests the actual `kadm5_get_config_params` API. It accepts the configured source/build directory, selected SDK compiler, disposable relocated trial prefix containing the built libraries and a synthetic Kerberos configuration, disposable work directory, and the configured prefix-relative default database and ACL paths. It makes no server connections and opens no credential or key files. The test checks both compiled defaults and explicit parameters. Its Darwin-only precondition is intentional: the test selects the relocated trial libraries with `DYLD_LIBRARY_PATH`; other hosts need their native loader equivalent. Prefix ownership and loaded-library provenance should be checked when constructing the trial prefix.

Example (arguments are local choices, not required machine paths):

```
SDK_PYTHON server-paths.py --source CONFIGURED_SRC --cc SDK_CC \
  --runtime-prefix MOVED_PREFIX --work TEMP_DIR \
  --db-relative var/krb5kdc/principal --acl-relative var/krb5kdc/kadm5.acl
```

`client.c` is a small native consumer of built `libkrb5` and `libkrb5support`; compile with the configured source include directories and built libraries. Run with a relocated trial prefix and synthetic Kerberos profile to inspect the FILE keytab name and plugin default, then provide explicit profile and environment overrides. `gss-fixture.c` is a synthetic shared module that writes the path selected by `EMBER_GSS_MARKER` when loaded; `gss-probe.c` requests its fixed synthetic mechanism OID. Compile the former as a shared object and link the latter against the built GSS library. Place a synthetic mechanism configuration and module in the relocated prefix to check relative module loading; set `GSS_MECH_CONFIG` to a synthetic configuration containing an absolute module path to check that override. These checks do not start services or authenticate. The compiled test program and runtime prefix must use the selected native SDK and its matching built libraries. No target-platform acceptance is implied.

`incremental.py` takes `--source`, `--cc`, `--make`, `--shell`, one or more `--tool-bin` directories, and `--work`. The shell and PATH entries must come from the selected SDK and its declared native tool aliases; the test restricts child PATH to those directories. It tests both library and plugin owner make fragments using a disposable small C module and a minimal libtool adapter invoking the selected compiler. Each case removes the restat line in an isolated copy for a negative control, verifies the actual loaded value stays stale, restores the candidate rule and verifies the new value is loaded immediately, then confirms a no-change run neither compiles nor links. The source tree and real build objects are not altered.
