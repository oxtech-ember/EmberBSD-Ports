# Common libpcap

This recipe selects the upstream stable libpcap 1.10.7 release and retains the
pkgsrc patch inventory from pinned revision `fff4deb639a1a640476203c80f752fb77b6cb14b`.
EmberBSD adaptations are shared by the
package and the native OS integration. The OS owns its BPF headers and ABI.

The [upstream release index](https://www.tcpdump.org/) listed 1.10.7 as stable
and 1.11.0 as testing when checked on 2026-10-29.

A previous EmberBSD testing package used 1.11.0 and SONAME 0. Stable 1.10.7
uses SONAME 1 because that testing package exposed APIs absent from the stable
remote-disabled package. Explicitly replace any installed testing package and
rebuild its binary consumers; a lower version does not update it automatically.
The buildlink constraint selects this stable package and excludes 1.11 testing.
