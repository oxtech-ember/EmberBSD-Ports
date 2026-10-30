# Qt ImageFormats

The target build selects the common Jasper, MNG, TIFF and WebP packages.
On amd64 EmberBSD, a Qt `QImageReader` consumer decoded upstream JP2, MNG,
TIFF and WebP samples on the physical target using the installed plugins. This
is a CPU codec check; it does not claim a GUI or graphics acceptance run.

The QtGui closure also reaches the existing Mesa/LLVM dependencies on base
`libpci.so.2`, `libelf.so.2` and `libedit.so.3`. The PCI bus interface is an
OS API. The target sysroot's elftoolchain and editline distinfo markers match
the common owner recipes; their builtin contracts check the markers, headers,
libraries and ABI rather than selecting an unverified second provider.
