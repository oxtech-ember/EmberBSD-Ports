# HPN regression

`run.py` builds and runs ordinary client and server configuration cases,
server option serialization, receive-buffer defaults, and a dynamic window
update against the supplied OpenSSH source and native build objects. Supply
`--cc`, `--source`, `--build-dir`, `--prefix`, and `--work-dir` explicitly;
`--sanitize` enables address and undefined-behavior sanitizers when supported
by the selected compiler. `--lpk` additionally builds the published native
LDAP integration with the selected prefix libraries. The build directory must contain a compatible
completed native OpenSSH build, including its configuration and archives.

These checks do not establish target execution, interoperability, or a working
NONE cipher switch. The native configuration tokens for that historical
switch remain accepted with their existing default-off behavior.
