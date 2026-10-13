#!/bin/sh
# Cover the legacy parser path after removal of self-initialization.
set -eu
result=`printf '%s' legacy`
test "$result" = legacy
result=$(printf '%s' modern)
test "$result" = modern
result=$(printf '%s' "`printf mixed`")
test "$result" = mixed
result=`printf '%s' "$(printf reverse)"`
test "$result" = reverse
result=`printf 'a\nb\n'`
test "$result" = 'a
b'
result=$(cat <<END
`printf legacy` $(printf modern)
END
)
test "$result" = 'legacy modern'
printf 'PASS: 6 legacy and mixed command-substitution contracts\n'
