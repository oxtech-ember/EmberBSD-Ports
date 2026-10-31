# Shared runit source

This recipe updates the pinned pkgsrc `sysutils/runit` source from 2.1.2 to
upstream runit 2.3.1. The original pkgsrc recipe is the packaging base.

The upstream installation guide identifies 2.3.1 as the current release and
publishes SHA-256 `634f23c8c4d1d440043be0fe928ddf904626289e97bfe7c5826e93aaf2cc6fe9`
for `runit-2.3.1.tar.gz`. `distinfo` also records pkgsrc's BLAKE2s, SHA-512,
and archive size. The package has no external library dependencies.

The package installs the upstream command suite, manuals, documentation, and
examples. It adds no rc.d script, does not select a PID 1, and does not enable
or start a service. A system may run `runsv` under its existing init scheme.

The upstream `package/check` target executes built programs. The pkgsrc `test`
phase runs it only with a native build profile and refuses a cross build.
Package staging copies the built files and does not run upstream test programs.

Run the ordinary-user lifecycle regression with a native `runsv` executable:

```sh
python3 tests/supervisor-lifecycle.py --runsv /absolute/path/to/runsv
```

The test checks service restart, duplicate-supervisor refusal, and termination
of the child when the supervisor receives TERM. Its service fixture has a
bounded lifetime and creates no helper processes. The record parser ignores an
incomplete final line and rejects malformed complete records. Run the focused
fixture/parser checks with `python3 tests/supervisor-lifecycle.py --self-test`.
Both checks use only temporary files and do not require root access.
