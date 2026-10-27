# Native Darwin MIG

This package builds Apple's MIG compiler and frontend from bootstrap_cmds-138.
The frontend requires explicit `MIGCC` and `MIGCOM`; set `SDKROOT` to the
selected host ABI SDK and restrict `PATH` to the selected native tool prefix.
The package retains the `mig` and `migcom` manuals, APSL 1.0 and 2.0 texts,
and the Carnegie Mellon notice. Source file notices identify their terms.

With prepared MIT Kerberos source, validate the installed generator and the
actual KCM interface using the selected native shell and compiler:

```sh
/absolute/native/bin/mksh files/test-kcmrpc.sh \
  /absolute/native/bin/mig /absolute/native/libexec/migcom \
  /absolute/native/bin/clang /absolute/MacOSX.sdk \
  /absolute/krb5-1.22.2 /absolute/new-test-work
```

The check generates and compiles KCM RPC code and rejects a failing
preprocessor; it does not test a running KCM service or a complete Kerberos
package. `files/test-kcmrpc-parallel.sh` checks the patched consumer rule with
GNU make and the same source inputs. Select `apple-public-source-license`,
`apple-public-source-license-1.0`, and `cmu-mig-license` in pkgsrc's license
policy before building the package.
