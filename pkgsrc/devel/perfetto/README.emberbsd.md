# Shared Perfetto source

This recipe owns the selected Perfetto source and the common portability
patches used by consumers. The source artifact does not itself establish a
working tracing implementation for any particular consumer.

OpenBSD 8.0 and later use `getexecpath` to find the current executable;
NetBSD uses its process pathname sysctl. On older OpenBSD, requesting that
path fails explicitly because there is no verified equivalent. In particular,
`tracebox` cannot re-execute its services there. This limitation does not
disable the tracing SDK.
