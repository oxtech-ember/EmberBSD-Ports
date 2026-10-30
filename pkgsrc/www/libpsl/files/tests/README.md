# Exact rule lookup

Compile `exact-rule.c` against the package under test. Pass the upstream
`list/public_suffix_list.dat`, a binary DAFSA generated from that same file by
`psl-make-dafsa --output-format=binary`, and domain arguments covering the
consumer corpus. The fixture compares both loaded context forms, checks raw
ICANN, private, wildcard and exception flags, and exercises length and invalid
input boundaries. The compiled-in context and consuming applications must be
checked separately against their selected data and ABI.

`psl_lookup_rule` performs a byte-exact lookup in a `psl_ctx_t`; it does not
normalize case, dots, or Unicode and does not apply the implicit wildcard rule.
The caller passes an explicit byte length. A return of -1 denotes an absent
rule or invalid input; otherwise the result is a bitwise OR of
`PSL_RULE_EXCEPTION` (exception rule), `PSL_RULE_WILDCARD` (wildcard rule),
`PSL_RULE_ICANN` (ICANN section), and `PSL_RULE_PRIVATE` (private section).
A normal rule may have neither wildcard nor exception bit. The internal PLAIN
bit is not part of this interface. Inputs containing NUL, empty inputs and lengths
that cannot be represented by the selected context are rejected.
