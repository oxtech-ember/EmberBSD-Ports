# SHA1 collision detection provider

The package uses upstream stable 1.0.3 and carries the complete changes to
the library, command and documentation through upstream commit
`a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988`. The release archive and patches
are checked by pkgsrc. The public library and header retain the upstream API;
include `<stddef.h>` before `<sha1dc/sha1.h>`.

After a native pkgsrc `package`, run the installed-interface checks with the
selected native Python and compiler. `STAGE` is the staged package prefix
inside `work/.destdir`, and `SOURCE` is the patched `WRKSRC`:

```
"$PYTHON" files/test-native.py --stage "$STAGE" --source "$SOURCE" --cc "$CC"
```

This tests both commands, static and shared consumers, both safe-hash modes,
collision detection and an ASan/UBSan build of the changed library sources.
It does not establish a target build or target execution.
