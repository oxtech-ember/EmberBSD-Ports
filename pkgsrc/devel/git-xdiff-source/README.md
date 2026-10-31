# Git xdiff sources

This source-only package extracts the xdiff files from the same release and
complete patch set as `devel/git-base`. It does not provide a standalone
library or a system xdiff ABI. A consumer must supply compatible allocation,
regular expression, error and algorithm-selection behavior. In particular,
libgit2 has not yet been switched or validated against this source.

After `package`, validate the staged source with the selected native Python
and Clang. `SOURCE` is `share/git-xdiff-source` in the staged prefix:

```
"$PYTHON" ../git-base/files/test-xdiff-native.py --source "$SOURCE" --cc "$CC"
```

The check verifies policy hooks, one exact merge output, allocation-failure
cleanup, and error returns for invalid context lengths under ASan/UBSan. It does
not replace a consumer's own diff and merge tests, target compilation or target
execution.
