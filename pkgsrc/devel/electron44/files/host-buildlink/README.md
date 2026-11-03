# Electron native host dependency view

`../host-buildlink.py` creates a native pkgsrc consumer from the single
`../../host-dependencies.mk` declaration. It selects the provided SDK, native
binding, pkgsrc export, host prefix and replacement stage and runs the normal
pkgsrc wrapper phase. Missing dependencies fail instead of installing packages.
All options are absolute paths; run `--help` with the selected host Python for
the complete interface. The command prints the resulting `.buildlink` path.

The view uses pkgsrc's own buildlink selection and transitive dependencies.
`--check` re-evaluates the selected makefiles, package metadata and view files;
it exits 3 if the saved selection has changed. On a change, create a new work
directory and rerun the wrapper phase. Directory symlinks in the generated
view are rejected because their contents cannot be checked as file links.
This checks the host build view, not target execution or a full Electron build.
