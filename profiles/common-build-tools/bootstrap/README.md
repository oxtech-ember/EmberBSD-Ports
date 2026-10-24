# Bind the initial make shell

An initial make binary can have external system-makefile and shell paths
compiled into it. Copying that binary does not change these paths.
The fixed selector `ports-bootstrap-make-v1` binds explicit makefiles and a
selected POSIX shell for a bounded bootstrap producer.
It does not qualify the input binaries as an ordinary native toolset.

## Inputs and layout

The SDK owns input admission, bundle assembly and the producer plan.
It must pin the make binary, its package metadata, the complete upstream
makefile tree and its source provenance. Keep historical builders and
unresolved provenance visible in the scoped seed receipt.
Do not infer qualification from a package name or version.

Pin this Ports revision, [sys.mk.in](sys.mk.in) and its SHA256 too.
The only template substitution is `@QUALIFIED_SH@`.
It must be the selected shell's absolute in-bundle invocation path.
For this fixed binding, reject whitespace and make metacharacters in that
path. Do not escape or reinterpret an unsupported path.

Retain every file, directory and symlink from the accepted upstream tree.
Keep its roster and hashes in the bundle inventory.
Move the original root `sys.mk` to `sys-upstream.mk` without changing bytes.
Create a new `sys.mk` from the exact template bytes.
All other upstream paths stay unchanged.
The template selects `.SHELL` before it includes an upstream makefile.
It also binds the ordinary `SHELL` make variable for recipes that use it.

```text
bundle-mk/
  sys.mk              exact instantiated Ports template
  sys-upstream.mk     unchanged original upstream sys.mk
  ...                 every other original upstream entry
```

The initial accepted upstream tree must not redefine `.SHELL` after the
entry point. Inventory makefile includes and active shell expressions.
Every consumed include must come from the plan's explicit accepted inputs.
A copied tree is not proof that every branch is safe to execute.

## Invocation

The bmake command prefix is:

```text
/absolute/selected/bmake -m /absolute/bundle-mk SHELL=/absolute/selected/sh
```

Add the recipe's `-C` argument after this prefix.
Do not add another `-m`, `MAKESYSPATH` or `MAKEFLAGS` value that changes it.
The command must bind an exact accepted `MAKECONF` before make reads package
metadata. An upstream `bsd.own.mk` can otherwise include a host configuration.
Bind selected compilers, archive tools and other required tools before the
first parse-time query. Upstream implicit rules retain their behavior;
their default tool names are not permission to search the host `PATH`.

The GNU make command prefix is:

```text
/absolute/selected/gmake SHELL=/absolute/selected/sh
```

Pass `SHELL` as a command-line variable for every initial and recursive GNU
make invocation. An environment-only assignment does not select its shell.
The producer must preserve the selected shell through configure-generated
makefiles and recursive make commands.

The [bmake manual](https://man.netbsd.org/make.1) defines `-m`, `.SHELL` and
command-line variables. The [GNU make manual](https://www.gnu.org/software/make/manual/html_node/Choosing-the-Shell.html)
defines GNU make shell selection.

## Acceptance

Accept the initial binary inputs only in the explicit bootstrap scope.
Do not make the first pilot depend on qualification of its future output.
Before the producer compiles anything, execute real package metadata with
the selected bmake, complete makefile tree and selected shell.
Check `.SHELL`, `SHELL`, `.SYSPATH`, recursive argv and every consumed file.
Exercise `!=` and `:sh` expressions through the selected shell.
Reject an absent shell, a missing upstream makefile, an include outside the
accepted inputs or a configuration fallback. Check that a failing shell
command still fails.

Then build the new make tools with the accepted GCC16 producer.
Ordinary native-toolset admission requires its own completed producer,
compiler/linker execution closure and runtime evidence.
The source entry and byte-preserving tree preparation alone do not prove
that a real package's metadata or native build passed.
