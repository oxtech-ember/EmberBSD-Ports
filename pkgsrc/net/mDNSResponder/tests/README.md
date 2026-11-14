# mDNSResponder tests

`test-netbsd-adaptations.py` compiles the actual `Reconfigure`, `DropPrivileges`,
NetBSD socket-policy helpers, and `mDNSPlatformSourceAddrForDest` function from
a selected prepared source tree. It stubs resolver, privilege, and socket calls
so it can assert the TEST-NET-2 probe, UDP port 7, quiet expected probe failure,
`MDNSD_NOROOT` behavior, optional IPv6 startup, and transient multicast errors
without network access or root privileges.

The same runner extracts the production core interface-advertising helpers.
It checks `mDNS_Init_AdvertiseLocalAddresses` with zero `AutoTargetServices`,
retention of local address records when the last `Target_AutoHost` service is
removed, the `mDNS_Init_DontAdvertiseLocalAddresses` client-only case, and the
per-interface `Advertise` gate. These are common mDNSCore policy checks, not
daemon network-operation tests.

Run it with the host-prefix Python and Clang, a prepared source tree and a new
work directory:

```sh
"$HOST_PREFIX/bin/python3.15" -B pkgsrc/net/mDNSResponder/tests/test-netbsd-adaptations.py \
    --cc "$HOST_PREFIX/bin/clang" \
    --source /absolute/prepared-mDNSResponder \
    --work /absolute/new-test-output
```

`t-addr-tailq.c` remains the standalone ABI-layout regression for the shared
queue adapter.
