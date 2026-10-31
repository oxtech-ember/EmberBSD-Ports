# DHCP DAD and IPv4LL regression

The fixture extracts the actual dhcpcd functions from the selected prepared
source and replaces OS I/O and timers. It covers lease validation after DAD
and cleanup of a previous IPv4LL address after a usable DHCP bind. It does not
emulate DHCP packets, a radio, or the target kernel ABI.

With a native prefix and a newly created output directory, run:

```
CC="$HOST_PREFIX/bin/clang" TEST_AWK="$HOST_PREFIX/bin/nawk" \
  TEST_SHASUM="$HOST_PREFIX/bin/shasum" \
  CFLAGS='-O1 -g -std=c11 -Wall -Wextra -Werror -fuse-ld=lld -fsanitize=address,undefined -fno-sanitize-recover=all' \
  "$HOST_PREFIX/bin/mksh" pkgsrc/net/dhcpcd/tests/dhcpcd-dad.sh \
  "$DHCPCD_SOURCE" "$NEW_WORK"
```

For cross compilation set `CC` and `CFLAGS` to the selected target compiler
and flags, and set `DHCPCD_DAD_RUN=0`. A target build is not a runtime test.
