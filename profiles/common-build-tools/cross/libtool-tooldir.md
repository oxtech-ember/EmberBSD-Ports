# Cross libtool in an OS TOOLDIR

`prepare-libtool.py` composes the selected cross tools, exports the common
pkgsrc recipe and builds its `cross/cross-libtool-base` package. The package is
installed with its own package database inside the selected OS TOOLDIR. Its
ordinary native build dependencies use the selected native Ports prefix and
its package database. By default that database is the one
`pkg_admin config-var PKG_DBDIR` reports. That answer is compiled into
pkg_install and is not relocated when the prefix moves; a missing
`etc/pkg_install.conf` in the current prefix does not change it. Pass
`--native-makeconf FILE` to select the database from the same host query the
SDK uses, instead of rewriting the shared prefix or the compiled configuration:

```
bmake -C PKGSRC/pkgtools/pkg_install USE_CROSS_COMPILE=no MAKECONF=FILE \
  show-vars VARNAMES=PREFIX PKG_DBDIR
```

`PREFIX` must be the selected host prefix. `PKG_DBDIR` must be a real
directory, not a symlink, outside the target sysroot. Every `@cwd` line in
every installed `+CONTENTS` must name that host prefix; a later `@cwd` and a
trailing space are refused. The target sysroot database and a database from
another prefix are refused. This still requires `--pkgsrc-tree` or
`--pkgsrc-export`. The producer verifies that input before the query.
`--pkgsrc-export` is the stage directory; the query uses the inner `pkgsrc`
tree from its receipt, not the stage directory itself. The dependency
`pkg_add -K PKG_DBDIR -U` and the prefix and database locks are unchanged;
the lock directory still defaults to the native prefix parent. A prefix can
keep that database outside `var/db/pkg`.

Select the host prefix, compiler, target sysroot, OS TOOLDIR, Git, work parent,
and target explicitly. A Clang runtime stage must match the actual foundation;
without one, the selected sysroot must contain a matching installed runtime.
`--distdir` selects an existing distfiles cache; otherwise pkgsrc uses a
temporary one. Prefix and package database writes use the existing SDK context
locks. Their directory defaults to the native prefix parent; `--lock-directory`
selects a different shared namespace. Producers using the same prefix must use
the same lock directory.

For the RV32 C-only profile, pass `--target riscv32`,
`--c-foundation-result RESULT`, and `--c-foundation-base BASE`. The sysroot may
then be a separately installed target root while the selected C foundation
continues to supply compiler-rt and static libunwind. This route does not select
a C++ runtime.

Without an export input the producer exports pkgsrc into its temporary work
directory on every run. `--pkgsrc-export DIR` selects a stage made by
`scripts/pkgsrc-export-stage.py prepare ROOT --sdk-source SDK --git GIT --patch PATCH`, which
prints `ROOT/FINGERPRINT`. The fingerprint hashes the Git object ids of the
pinned `upstream/pkgsrc` gitlink and of every input that
`scripts/prepare-pkgsrc.py` reads, plus the patch tool. A Ports commit outside
those inputs keeps it, and uncommitted, untracked or ignored files inside an
input are refused. The producer verifies the stage against the current inputs
and only reads it: work directories stay under its temporary `WRKOBJDIR`, with
no `work` links in the shared tree. Run the stage before the builds that read
it; creating it is a separate step.

`--pkgsrc-tree DIR` selects an existing read-only export tree already used by
the package graph. Its recorded upstream revision must match the pinned Git
submodule; the selected libtool recipe and patches are included in the context
identity.


The producer reuses a compatible context identified by effective recipe,
compiler, wrapper, runtime and foundation inputs. An interrupted owned context
is recreated in place. An incompatible or foreign entry is left untouched.
After installation and package validation, the stable `TOOLDIR/bin/target-libtool`
alias and returned target-tools directory select that context. These paths must
stay within their TOOLDIR because libtool records its compiler and tool paths.
The context also exposes `target-tools/bin/target-libtool`. When this alias is
present, the common cross profile selects it as `PKG_LIBTOOL` for target package
builds; native dependency builds retain the host libtool. `EMBERBSD_CROSS_LIBTOOL`
can name another selected target script in a cross MAKECONF.

The contexts and their compiler bindings name the sysroot only through the
`sysroot` link in the context directory, never the stage directory. Every run
points this link at its selected stage before it selects a context, while the
SDK holds the TOOLDIR for the whole run, so a reused context reaches the
current stage and renaming a stage does not force a rebuild. The real headers
and libraries the context was configured with (`lib`, `usr/include`,
`usr/lib`) remain part of its key.
