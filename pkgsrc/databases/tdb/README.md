# TDB package options

The default package includes the Python extension. Select `-python` in
`PKG_OPTIONS.tdb` for applications that need only the C library and utilities.
The C-only build still runs upstream Waf with the selected build-host Python;
it does not add the target Python extension or its runtime dependency.
