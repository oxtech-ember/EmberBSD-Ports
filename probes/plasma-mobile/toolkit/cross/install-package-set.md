# Install a prepared Plasma package set

Prepare the runtime closure with `prepare-package-set.rb` first.
Pass each exact root package name once. Duplicate roots are rejected before output is created.
Copy its complete output directory to the target.
Keep `packages/`, `packages.sha256`, `install-order.txt`, `roots.txt` and `target.txt` together.
Select `--target aarch64|amd64`; the default is `aarch64`.
The selected ABI retains upstream `NetBSD 11.0` package identifiers.
The amd64 target uses `MACHINE_ARCH=x86_64`; AArch64 uses `aarch64`.
A matching package ABI does not establish the provenance of the board's base system.

Verification is the default action and works on macOS with native pkgtools:

```sh
PKG_INFO=/absolute/native/pkg_info PKG_ADMIN=/absolute/native/pkg_admin \
    sh install-package-set.sh --verify-only /absolute/package-set
```

For an amd64 set, add `--target amd64` before `--verify-only`.

The target can use installed `pkg_info`, `pkg_admin` and `sha256` from `PATH`.
The macOS fallback is `shasum -a 256`.
Verification checks every archive SHA256 before reading package metadata.
It rejects missing, extra, duplicate and symlinked archives or manifest entries.
It checks each package identity, target metadata, roots and dependency order.
The target receipt must exactly match the selected ABI. The original four-line
AArch64 receipt is accepted. Missing, extra or duplicated fields are rejected.
Every dependency receives the same metadata check. The auditor checks ELF
headers during preparation; SHA256 then preserves those audited archive bytes.
Dependency resolution uses the real pkgtools matcher with a private temporary metadata database.
Verification does not install packages or change the installed package database.

Stop the Plasma session before installation.
Run the following command as root on the selected EmberBSD target:

```sh
sh install-package-set.sh --install /absolute/package-set /absolute/new-install.log
```

For amd64, add `--target amd64` before `--install`. Both mode and target
options must precede the package-set path.

Installation requires an explicit mode and a new log path.
The script rejects other operating systems, other architectures and an active `plasmashell`.
Before installation, `uname -p` must match `aarch64` or `x86_64`, as selected.
An AArch64 receipt cannot be selected for amd64 installation.
It uses `pkg_add -U` in the verified dependency order.
New dependencies use `-A` and are marked automatic.
Existing dependencies keep their manual or automatic status, including version upgrades.
Selected roots are marked manual after their successful installation.
This also promotes a root that was previously installed as a dependency.
Verification files and the log use a private `077` umask.
Each `pkg_add` invocation uses `022`, so ordinary users can traverse package directories.
Package installation scripts stay enabled, including Workspace configuration-file installation.
It uses the local package directory and rechecks each archive immediately before installation.
It then runs `pkg_admin check` for every installed package in the closure.
The log keeps the archive hashes, package-tool versions and installation output.

A package failure stops the sequence and returns nonzero.
There is no automatic rollback of packages installed before that failure.
Inspect the log and correct the cause before retrying.
The helper does not configure device ownership, enable services, create users or start a session.
Package-provided install scripts still perform their normal package configuration.
The accelerated Plasma session and physical display remain separate acceptance checks.

## Host checks

Run the data-only package regression with real native pkgtools:

```sh
PKG_CREATE=/absolute/native/pkg_create PKG_INFO=/absolute/native/pkg_info \
PKG_ADMIN=/absolute/native/pkg_admin PKG_ADD=/absolute/native/pkg_add \
    ruby ../tests/install-package-set.rb /absolute/new-results
```

The regression creates actual package archives with `pkg_create`.
It checks valid verification and causal failures before installation.
The macOS run also checks that the explicit install mode rejects the host.
Two native data-only fixtures also exercise the exact installation helper in private prefixes and package databases.
The original `077` control creates a `0700` payload directory; the fixed helper creates `0755`.
Both real package installations retain install scripts and pass `pkg_admin check`.
Three more native fixtures check first installation, version upgrades and same-version reinstalls.
They check new automatic dependencies, preserved manual/automatic dependencies and previously automatic roots.
These fixtures use the production installation helpers and pass installed-payload checks.
The helpers use `pkg_info -E` and `pkg_info -q -Q automatic` to read existing state.
They use `pkg_admin unset automatic` to mark successfully installed roots manual.
The regression does not install target packages or alter the host package prefix/database.
It does not claim target installation or desktop acceptance.
