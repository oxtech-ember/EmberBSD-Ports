# LDAP public-key filter check

Run `filter.py` with `--source` pointing to the prepared OpenSSH source,
`--cc` to the selected native compiler, `--ldap-prefix` to its OpenLDAP
installation, and `--work` to a scratch directory. The check compiles the
production group and assertion-value functions with ASan and UBSan. It checks
ordinary group names and a literal percent sign. It does not test an LDAP
server, target execution, or the complete authentication flow.
