# Explicit dictionary regressions

Run `run.py` with a selected native SDK compiler, the engine source directory,
a generated `dict-src.h` directory, and a writable output directory. Use
`--sanitize` for an SDK compiler with ASan and UBSan runtimes. No download,
package installation, or target execution is performed by this runner.

`adversarial.c` exercises 16- and 32-bit child arrays, malformed descriptors,
a valid shared DAG and a cyclic edge, and concurrent calls interleaving the
default dictionary and a validated immutable custom handle. The caller must
finish all threads before freeing a handle.

For the representative application regression, generate `dict-src.h` from
upstream's six lists followed by the application's transliterated Russian and
Ukrainian frequency lists, in that order. `actual-dictionary.c` compares the
legacy default and explicit dictionary API scores and match details, including
100/101-byte boundaries and null argument behavior. Keep generated word lists
and output headers out of the repository. These test inputs do not contain
real passwords or accounts.

`generator.sh DICTGEN UPSTREAM_DICTGEN WORDS_DIR INCLUDE_DIR LIB_DIR` uses the
selected native `CC` to compare original output, reject invalid inputs, and
compile and run generated 16-bit and 32-bit descriptors without retaining data.

A `--descriptor NAME` symbol must be an unreserved C identifier and must not
collide with symbols from the headers included by its consumer. Names starting
with `_`, ending in `_t`, C keywords, and known generated or API names are
rejected.
