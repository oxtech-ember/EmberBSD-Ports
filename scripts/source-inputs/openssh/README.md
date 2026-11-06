# Common OpenSSH source

Prepare the upstream portable OpenSSH archive with the complete selected
`security/openssh` pkgsrc patchset. Use `source.py --sdk-source SDK --git GIT
prepare --archive ARCHIVE --patch PATCH --output NEW_DIRECTORY`. By default the
receipt records the effective Git recipe identity used by the OS prepared-source
checker. A shared pkgsrc export can be supplied with `--pkgsrc-export`.

Retired receipt formats and identity-mode options are not accepted.
Prepare derived source trees again with the current producer.

Run `verify-source --source DIRECTORY` to verify the prepared tree and its
recipe identity.

The OS native OpenSSH integration has additional NetBSD-specific requirements;
this source producer alone does not establish OS compatibility or runtime support.
