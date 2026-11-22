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

The Darwin defaults patch may create only `darwin-defaults.c` and
`darwin-defaults-gen.c`. Its `/dev/null` headers do not relax the SDK's checks
for absolute paths or traversal. Check both creation scopes and that guard:

```sh
python3 scripts/source-inputs/openssh/test-kerberos-paths.py \
  --sdk-source /absolute/EmberBSD-SDK --patch /absolute/patch
```

The LDAP public-key patch keeps its saved argument count only under
`WITH_NETBSD_LPK`; the saved argument vector remains available for re-exec in
both profiles. Check the real OS translation unit with the selected wrapper's
compiler and warning flags:

```sh
python3 pkgsrc/security/openssh/tests/ldap/compile-profiles.py \
  --sdk-source /absolute/EmberBSD-SDK --host-prefix /absolute/host-pkg-llvm \
  --os-source /absolute/EmberBSD --nbmake /absolute/selected-nbmake \
  --source /absolute/prepared-openssh --sysroot /absolute/ldap-off-dest \
  --ldap-sysroot /absolute/ldap-enabled-dest \
  --config-object /absolute/ldap-config-object \
  --builtin-config-object /absolute/builtin-config-object \
  --work-dir /absolute/check-work
```

This checks `sshd-session.c` with `MKLDAP=no` and `MKLDAP=yes` without linking
or running target code. It also checks the actual `ssh-keygen.c` source with
builtin crypto and LDAP disabled, using the public crypto selector and
`MKPIC=no`. The enabled sysroot must retain the LDAP headers, and each config
object directory must contain the generated `build/config.h` for that profile.
To run only the builtin crypto case, omit the LDAP inputs and add
`--builtin-only`.
