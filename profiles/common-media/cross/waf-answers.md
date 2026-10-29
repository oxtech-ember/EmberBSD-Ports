# Stored Waf cross answers (talloc, tdb)

Samba's Waf build (`devel/talloc`, `databases/tdb`) compiles small feature
probes during configure and runs them. A cross build cannot run them, so
Waf takes the results from a cross answers file instead
(`--cross-answers`). The recipes keep one answers file per target platform:

```
pkgsrc/devel/talloc/files/cross-answers/NetBSD-11.0-aarch64.txt
pkgsrc/databases/tdb/files/cross-answers/NetBSD-11.0-aarch64.txt
```

The shared fragment
[devel/talloc/waf-cross.mk](../../../pkgsrc/devel/talloc/waf-cross.mk) and
its helper [waf_answers.py](../../../pkgsrc/devel/talloc/files/waf_answers.py)
select the mode with `EMBERBSD_WAF_ANSWERS_MODE`:

| Mode | Target | Inputs | Result |
|------|--------|--------|--------|
| `replay` (default) | none | none | configure with the stored answers only |
| `capture` | yes | `EMBERBSD_GI_QUERY_CONFIG`, `EMBERBSD_SDK_SOURCE`, `EMBERBSD_CROSS_BUILD_PYTHON`, `EMBERBSD_WAF_ANSWERS_CAPTURE_DIR` | probes run on the target; normalized answers are stored |

In replay, `pre-configure` copies the stored file to
`${WRKDIR}/.cross-answers.txt` and Waf runs with `--cross-compile
--cross-answers` and no `--cross-execute`. A probe without a stored answer
makes Waf stop with "Cross answers file ... is incomplete", so a build never
falls back to a target. A missing stored file stops configure with a hint
to this page. Fetch, checksum and extract never need the answers.

## Stored file format

Waf ignores lines that start with `#`, so the identity header stays in the
file that Waf reads:

```
# EmberBSD Waf cross answers 1
# platform: NetBSD-11.0-aarch64
# recipe: databases/tdb
# package: tdb-1.4.15
# answers-sha256: <SHA-256 of the answer lines below>
Checking simple C program: "NetBSD"
rpath library support: OK
...
```

Answers use Waf's forms: `OK`, `NO`, `"string"` or `(status, "string")`.
Replay refuses a file for another platform, recipe or package version
(`PKGNAME_NOREV`, so `PKGREVISION` bumps keep the answers), a body that
differs from its checksum and a file that is not normalized. A new source
release needs a new capture.

## Capturing

Capture uses the same private query configuration and target executor as
the GI dumps ([gi-dumps.md](../../common-graphics/cross/gi-dumps.md)): any
EmberBSD target, named only in a query file outside the Git tree. Each
probe uses its own remote `mktemp` directory that is removed afterwards;
nothing is installed on the target.

```sh
mkdir /absolute/waf-capture
bmake EMBERBSD_WAF_ANSWERS_MODE=capture \
  EMBERBSD_GI_QUERY_CONFIG=/absolute/private/query.json \
  EMBERBSD_WAF_ANSWERS_CAPTURE_DIR=/absolute/waf-capture configure
```

Waf asks the target for every probe and appends each answer. After
configure, `emberbsd-waf-capture` refuses a recorded transport failure,
an `UNKNOWN` or malformed answer, conflicting duplicates and answers that
contain a build path. It writes
`/absolute/waf-capture/PLATFORM/CATEGORY_NAME.txt` and never overwrites one.
Review it and copy it to `pkgsrc/CATEGORY/NAME/files/cross-answers/PLATFORM.txt`.

## Tests

```sh
python3.15 profiles/common-media/tests/waf-answers.py --bmake BMAKE \
  --pkgsrc PKGSRC --makeconf CROSS_MAKECONF \
  --samba-cross WRKSRC/buildtools/wafsamba/samba_cross.py
```

It checks the helper (normalization, refusals, round trip read back by
Waf's own `samba_cross.py`) and the recipe wiring with a real cross
MAKECONF: default replay without `--cross-execute` or a query configuration,
the replay target, opt-in capture inputs, the failure gate and native mode.
