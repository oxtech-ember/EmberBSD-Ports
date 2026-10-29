# Common libxml2 source

Prepare and verify the complete shared `textproc/libxml2` release archive,
patches and recipe-owned test support files. Consumers choose build options;
this source producer does not configure, build or install a library.

Use `source.py --sdk-source SDK --git GIT prepare --archive ARCHIVE --patch
PATCH --scoped-identity --output SOURCE` and `verify-source --source SOURCE
--patch PATCH`; pass the archive when verification requires payload comparison.
The archive and every recipe patch and support file are checked before use.
