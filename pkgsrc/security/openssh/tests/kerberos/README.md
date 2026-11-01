# Native Kerberos-2 compatibility

The guarded native method preserves the base configuration and method name.
The historical client requests mutual authentication, but this method does not
consume the returned AP-REP; it does not claim mutual authentication or a new
wire exchange. `KerberosTgtPassing` is accepted for configuration compatibility
and does not implement credential forwarding. Portable builds do not enable
this native method.

Tests of local serialization and ownership do not establish interoperability
with a Kerberos realm or target runtime behavior.
