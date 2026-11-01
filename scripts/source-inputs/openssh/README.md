# Common OpenSSH source

Prepare the upstream portable OpenSSH archive with the complete selected
`security/openssh` pkgsrc patchset. Use `source.py --sdk-source SDK --git GIT
prepare --archive ARCHIVE --patch PATCH --output NEW_DIRECTORY`. By default the
receipt records the effective Git recipe identity used by the OS prepared-source
checker. A shared pkgsrc export can be supplied with `--pkgsrc-export`.

`--export-identity` writes the legacy export-input receipt for source-only
compatibility; `verify-source` continues to accept it, while the OS current
recipe checker requires the effective Git identity. `--scoped-identity` is an
alias for the default.

Run `verify-source --source DIRECTORY` to verify the prepared tree and its
recipe identity.

The OS native OpenSSH integration has additional NetBSD-specific requirements;
this source producer alone does not establish OS compatibility or runtime support.
