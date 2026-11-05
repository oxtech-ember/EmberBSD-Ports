# Estimator failure regression

This explicit host test builds the actual Telegram `passcode_strength.cpp` and
`passcode_strength_translit.cpp` using selected SDK QtCore, injecting a failed
zxcvbn dictionary creation and match. A long synthetic repeated string checks
that an estimator error cannot become a positive strength through the tail
correction. No real account, password, application settings, or device is used.

Run `run.py` with absolute selected native SDK compiler and pkg-config paths,
SDK prefix, patched Telegram SourceFiles, shared zxcvbn headers, and a writable
output directory. `PKG_CONFIG_LIBDIR` or the SDK's own pkg-config configuration
must select the matching native QtCore.
