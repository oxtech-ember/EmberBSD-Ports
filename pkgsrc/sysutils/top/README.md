# top source and platform scope

The common source is the original top 3.8beta1 distribution with the complete
NetBSD-maintained source delta, EmberBSD fixes and the retained pkgsrc NetBSD
and DragonFly backend sources. The native OS consumer uses the NetBSD backend,
its own installation rules and the same prepared source. Linux, FreeBSD,
Solaris and other upstream platform modules remain in the distribution.

The selected target signal header is explicit in cross builds; the native
configure search is retained. DragonFly and older NetBSD backend runtime
requires its own platform testing. Darwin versions lacking kvm remain unsupported.
