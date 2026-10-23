# GNU gettext locale declarations

This recipe preserves the NetBSD pkgsrc recipe and the upstream licenses.
The installed package has revision 1 on native and cross builds.
The API floor stays at 0.22. The package ABI floor selects the corrected package.
The built-in provider keeps its API contract.

GCC C on Darwin uses the existing locale macro mappings in `libgnuintl.in.h`.
The mappings keep calls and function addresses bound to `libintl_setlocale`
and `libintl_newlocale`. They avoid a second declaration of the libc names.
The change does not alter native C++ or other target platforms.
It does not disable compiler diagnostics or replace platform headers.

Run `tests/locale-redirect.py` with generated before and after headers from
matching GNU gettext configurations. Use a native GCC16 compiler and its
matching C++ compiler. Set `--apple-sdk` to the selected host SDK.
The test uses the explicit SDK API 1 for bounded owned commands.
It does not configure, install, or modify the prefix.
The test requires native Darwin. It does not claim NetBSD runtime acceptance.

```sh
python3.15 -B -E -S tests/locale-redirect.py \
  --before-header "$OLD_HEADER" --fixed-header "$NEW_HEADER" \
  --prefix "$PREFIX" --apple-sdk "$(xcrun --sdk macosx --show-sdk-path)" \
  --sdk-root "$SDK_SOURCE" --obj-root "$OBJROOT" \
  --work "$OBJROOT/probes/gettext-locale-redirect"
```

The baseline must fail with `-Werror=redundant-decls`. The fixed header must
pass with the same diagnostics. Both objects must reference the same libintl
symbols. Real calls through function pointers must produce the same result.
The native C++ preprocessed tokens must remain identical.
