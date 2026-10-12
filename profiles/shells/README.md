# Interactive shells profile

Selected by the project owner on 2026-10-10: **dash, zsh, mksh** (bash
deliberately excluded). Roles: mksh is the interactive shell on devices,
dash is the lightweight scripting shell, zsh is the desktop interactive
shell with its completion plugins. The system `/bin/sh`, rc scripts and
agent scenarios stay strictly POSIX and are not part of this profile.

## Versions

| Package | Version | Recipe |
| --- | --- | --- |
| `dash` | 0.5.13.5 | pinned quarterly pkgsrc `shells/dash` — already current upstream |
| `zsh` | 5.9.2 | pinned quarterly pkgsrc `shells/zsh` — already current upstream (`zsh.org/pub` ships 5.9.2) |
| `mksh` | 59c | local recipe `pkgsrc/local-shells/mksh` — upstream R59c while the pinned pkgsrc carries R59b |

Version comparison made on 2026-10-12 against the pinned submodule
(pkgsrc-2026Q3 `fff4deb63`), pkgsrc HEAD and the upstream distribution
sites. No patches to upstream sources are required.

For the desktop profile, `zsh-completions` and `zsh-autosuggestions` are
taken from the pinned pkgsrc as optional additions.

## Build

Prepare a tree with the overlay and build natively on the target:

```sh
git clone --recurse-submodules --shallow-submodules \
  https://github.com/oxtech-ember/EmberBSD-Ports.git
cd EmberBSD-Ports
sh scripts/prepare-pkgsrc.sh "$PWD/../pkgsrc-shells"
cd ../pkgsrc-shells/local-shells/mksh && bmake install
cd ../../shells/dash && bmake install
cd ../zsh && bmake install
```

`mksh` needs only a C compiler; `dash` needs the usual autotools flow that
pkgsrc drives; `zsh` needs curses/terminfo from the base system.

## Validation record

- 2026-10-12, upstream source: `mksh-R59c.tgz` fetched from
  `https://www.mirbsd.org/MirOS/dist/mir/mksh/`, SHA512 recorded in
  `distinfo`. The manual page carries the R59c marker; the runtime banner
  keeps the base `R59 2020/10/31` string, which is how mksh point releases
  identify themselves.
- 2026-10-12, target build probe: R59c built natively on
  `ember-vm-01` (EmberBSD/NetBSD 11.0 EMBER64 kernel, aarch64, base cc)
  via `sh Build.sh -r`; `./mksh -c 'echo $KSH_VERSION'` printed the
  expected banner. This validates upstream code on the target OS, not the
  pkgsrc packaging itself.
- Not yet done: pkgsrc packaging build of all three recipes on the target,
  `pkg_admin` verification, joint install, `chsh` switch and the upstream
  `check.t` regression suite. The suite needs Perl, which the minimal
  build VM and this profile do not carry yet; upstream pkgsrc keeps
  mksh's `do-test` disabled for the same reason.

Packaging acceptance and the signed pkgin channel belong to the project's
binary-distribution milestone.
