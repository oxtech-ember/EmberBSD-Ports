#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise patched miette, its derive macro, and selected unicode-width offline."""
import argparse
from pathlib import Path
import subprocess
import tempfile

SOURCE = r'''use miette::{Diagnostic, NamedSource, SourceSpan};
#[derive(Debug, Diagnostic)]
#[diagnostic(code(ember::example), help("try again"))]
struct Example {
    #[source_code]
    src: NamedSource<String>,
    #[label("here")]
    span: SourceSpan,
}
impl std::fmt::Display for Example {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("example")
    }
}
impl std::error::Error for Example {}
fn main() {
    let e = Example { src: NamedSource::new("example.rs", "é界".to_string()), span: (0, 2).into() };
    assert_eq!(e.code().unwrap().to_string(), "ember::example");
    assert_eq!(e.help().unwrap().to_string(), "try again");
    let label = e.labels().unwrap().next().unwrap();
    assert_eq!(label.label(), Some("here"));
    assert_eq!(label.len(), 2);
    let wide = Example {
        src: NamedSource::new("bad_file.rs", "source\n  👼🏼text\n    here".to_string()),
        span: (9, 6).into(),
    };
    let mut report = String::new();
    miette::NarratableReportHandler::new().render_report(&mut report, &wide).unwrap();
    let expected = "example\n    Diagnostic severity: error\nBegin snippet for bad_file.rs starting at line 1, column 1\n\nsnippet line 1: source\nsnippet line 2:   👼🏼text\n    label at line 2, columns 3 to 6: here\nsnippet line 3:     here\ndiagnostic help: try again\ndiagnostic code: ember::example\n";
    assert_eq!(report, expected);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prefix', 'cargo-home', 'vendor', 'unicode-width', 'sdkroot'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    if not args.target.endswith("-apple-darwin"):
        parser.error("this test requires a Darwin host target")
    prefix = args.prefix.resolve(strict=True)
    vendor = args.vendor.resolve(strict=True)
    unicode_width = args.unicode_width.resolve(strict=True)
    # JSON strings are also valid TOML strings and safely handle spaces.
    import json
    with tempfile.TemporaryDirectory(prefix='miette-consumer-') as temp:
        root = Path(temp)
        (root / 'src').mkdir()
        (root / 'src/main.rs').write_text(SOURCE)
        (root / 'Cargo.toml').write_text(
            '[package]\nname = "miette-consumer"\nversion = "0.1.0"\nedition = "2021"\n'
            '[dependencies]\nmiette = { path = ' + json.dumps(str(vendor / 'miette-7.6.0')) + ' }\n'
            '[patch.crates-io]\n'
            'miette-derive = { path = ' + json.dumps(str(vendor / 'miette-derive-7.6.0')) + ' }\n'
            'unicode-width = { path = ' + json.dumps(str(unicode_width)) + ' }\n')
        env = dict(PATH=str(prefix / 'bin'), CARGO_HOME=str(args.cargo_home.resolve(strict=True)),
                   SDKROOT=str(args.sdkroot.resolve(strict=True)),
                   CARGO_ENCODED_RUSTFLAGS='-C\x1flink-arg=--ld-path=' + str(prefix / 'bin/ld64.lld'))
        env['CARGO_TARGET_' + args.target.upper().replace('-', '_') + '_LINKER'] = str(prefix / 'bin/clang')
        subprocess.run([str(prefix / 'bin/cargo'), 'run', '--offline', '--target', args.target,
                        '--manifest-path', str(root / 'Cargo.toml')], env=env, check=True)
    print('miette derive and Unicode width: PASS')


if __name__ == '__main__':
    main()
