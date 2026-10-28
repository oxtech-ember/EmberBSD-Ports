# Shared BoringSSL source

This is the common source and Ports patch owner for BoringSSL. Upstream does
not provide versioned stable releases; this package pins current upstream
commit `df870ed7fa51110edb872beb3357a44d20e1ce56` and verifies its Git tree
before producing a deterministic archive. Consumers compile their own host
or target ABI artifact. This package installs no OpenSSL headers or libraries.

The compatibility patch set preserves Electron BoringSSL commits
`bb964822a48b02fb7d9276dc6661761b29de14fd` by Jeremy Apthorp (RIPEMD-160
EVP support) and `dc51d5fe267522baa3adf95e2fbf482833f8ba15` by Shelley Vohr
(additional cipher APIs). The existing
RIPEMD, Blowfish and CFB implementations are compiled into crypto once, outside
the FIPS module, so the Electron-compatible lookup APIs link without depending
on decrepit. Upstream's generators own the source and prefix-symbol metadata.
The NetBSD AArch64
adaptations come from pkgsrc www/chromium, based on OpenBSD Chromium and pkgsrc
qt5-qtwebengine patches. Upstream LICENSE and component licenses remain in the
prepared source. Source publication alone does not establish runtime, target,
FIPS, Chromium graph, or consumer ABI acceptance.
