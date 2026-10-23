# Gettext declaration and link provider

The Meson adaptation tests `dgettext` with the selected `<libintl.h>` declaration.
It uses libc when that declaration links without another library.
Otherwise it requires `libintl`.
This preserves header redirects such as GNU `libintl_dgettext`.
It avoids choosing a provider from the operating-system name alone.

Run the focused test with a native glibc compiler and the coherent AMD64 sysroot:

```sh
MESON=/absolute/current/meson CC=/absolute/native/gcc \
ruby intl-link.rb /absolute/pulseaudio-17.0.tar.xz \
  /absolute/toolchain/bin/x86_64--netbsd-gcc /absolute/sysroot /absolute/new-results
```

The script verifies the archive pin and applies the canonical patch with zero fuzz.
It extracts the actual patched gettext selection into a small Meson project.
The native consumer links and runs with libc.
The AMD64 consumer requires external `libintl` and retains `libintl.so.1` in its dynamic dependencies.
The target control without `-lintl` must fail.
The test uses the sysroot's base gettext header and library.
It does not execute the target program or accept PulseAudio runtime behavior.

Set `BASELINE_PATCH` to a saved prior `patch-meson.build` for a causal comparison.
The inherited patch incorrectly requires absent `libintl` on native glibc.
That native Meson configuration must fail, while the target link still succeeds.
The result directory retains source fragments, commands, compiler logs and hashes.
