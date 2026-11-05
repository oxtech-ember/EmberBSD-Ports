# Installed path relocation regression

Run `relocated-paths.py` on Darwin with the selected SDK Python, passing paths
to the old and new native g-ir-compiler/g-ir-inspect directories and their
corresponding libgirepository dylibs, plus `--producer-prefix`. Inputs must be
actual tool/library build outputs. Example (fill in the selected paths):

    python3.15 relocated-paths.py --old-bin OLD_BIN --old-lib OLD_DYLIB \
      --new-bin NEW_BIN --new-lib NEW_DYLIB --producer-prefix PREFIX

The fixture checks old failures and new success for installed GIR and typelib
lookup, loaded dylib identity, explicit GI_GIR_PATH, --includedir and
GI_TYPELIB_PATH, and absence of producer-prefix fallback. It sets XDG data
paths to an empty temporary directory because XDG is an intentional higher
priority source and may otherwise include the producer prefix. It is an
explicit test, not part of ordinary package builds; DYLD and .dylib make this
fixture Darwin-specific.
