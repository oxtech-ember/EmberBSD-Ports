# Target LLVM C++ runtime packages

The cross NetBSD amd64 and aarch64 package recipes compose the common full
runtime stage. Set `EMBER_LLVM_CXX_STAGE`, `EMBER_LLVM_CXX_BASE`,
`EMBERBSD_SDK_SOURCE` and `EMBER_LLVM_CXX_PYTHON`
to absolute paths. The selected stage is checked against its base, LLVM source,
relevant patches and ELF runtime closure. The package prefix must be `/usr/pkg`.

The runtime packages contain shared libraries and licenses. Their matching
`-devel` packages contain headers, static archives and linker inputs. This
route does not build a second LLVM runtime or claim target execution. The
native Darwin libcxx producer remains the existing separate native route.
