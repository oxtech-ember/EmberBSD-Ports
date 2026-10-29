# Target LLVM C++ runtime packages

The cross NetBSD amd64 and aarch64 package recipes compose the common full
runtime stage or a completed application sysroot. The cross adapter supplies
the selected runtime source, SDK and native Python to the package recipes.
An explicit stage is checked against its base; a completed sysroot uses the
SDK application runtime loader. Both routes check LLVM source, relevant
patches and ELF runtime closure. The package prefix must be `/usr/pkg`.

The runtime packages contain shared libraries and licenses. Their matching
`-devel` packages contain headers, static archives and linker inputs. This
route does not build a second LLVM runtime or claim target execution. The
native Darwin libcxx producer remains the existing separate native route.
