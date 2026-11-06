# MIT Kerberos native relocation regression

`server-paths.py` tests the actual `kadm5_get_config_params` API. It accepts the configured source/build directory, selected SDK compiler, disposable relocated trial prefix containing the built libraries and a synthetic Kerberos configuration, disposable work directory, and the configured prefix-relative default database and ACL paths. It makes no server connections and opens no credential or key files. The test checks both compiled defaults and explicit parameters. Its Darwin-only precondition is intentional: the test selects the relocated trial libraries with `DYLD_LIBRARY_PATH`; other hosts need their native loader equivalent. Prefix ownership and loaded-library provenance should be checked when constructing the trial prefix.

Example (arguments are local choices, not required machine paths):

```
SDK_PYTHON server-paths.py --source CONFIGURED_SRC --cc SDK_CC \
  --runtime-prefix MOVED_PREFIX --work TEMP_DIR \
  --db-relative var/krb5kdc/principal --acl-relative var/krb5kdc/kadm5.acl
```

A full regression should also check default, explicitly supplied and secure-context configuration, FILE default keytab name, GSS relative and absolute modules, and the config/lib.in and config/libnover.in incremental relink behavior. Actual trial evidence and prototype sources are in the companion relocation and relink fixtures. These are not represented as target-platform acceptance.

`incremental.py` takes `--source`, `--cc`, `--make`, and `--work`. It tests both library and plugin owner make fragments using a disposable small C module and a minimal libtool adapter invoking the selected compiler. Each case removes the restat line in an isolated copy for a negative control, verifies the actual loaded value stays stale, restores the candidate rule and verifies the new value is loaded immediately, then confirms a no-change run neither compiles nor links. The source tree and real build objects are not altered.
