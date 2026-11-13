#!/usr/bin/env python3
import argparse
import hashlib
import subprocess
import tempfile
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--python',required=True);p.add_argument('--script',required=True);p.add_argument('--generator',required=True);a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='node-undici-projection-', dir='/private/tmp') as tmp:
    root=Path(tmp); prefix=root/'prefix'; db=prefix/'pkgdb'; pkg=db/'undici-8.12.4';pkg.mkdir(parents=True)
    rel=Path('lib/node_modules/undici/loader.js'); loader=prefix/rel;loader.parent.mkdir(parents=True)
    runtime=Path('/selected/runtime'); data=f'createRequire("{runtime / rel}")'.encode(); loader.write_bytes(data)
    info=f'PKGPATH=www/undici\nEMBERBSD_UNDICI_RUNTIME_PREFIX={runtime}\n'; (pkg/'+BUILD_INFO').write_text(info)
    contents=f'{rel}\n@comment MD5:{hashlib.md5(data,usedforsecurity=False).hexdigest()}\n';(pkg/'+CONTENTS').write_text(contents)
    fake=root/'pkg-info';fake.write_text('#!/bin/sh\ncase "$4" in undici*) echo undici-8.12.4;; llhttp*) echo llhttp-wasi-9.4.4;; *) exit 1;; esac\n');fake.chmod(0o755)
    recipe=root/'recipe';(recipe/'files').mkdir(parents=True)
    names=('Makefile','distinfo','files/generate-wasm.py')
    for name in names: (recipe/name).write_text('selected '+name)
    (recipe/'files/generate-wasm.py').write_bytes(Path(a.generator).read_bytes())
    (pkg/'+BUILD_VERSION').write_text(''.join(f'www/undici/{name}: {hashlib.sha256((recipe/name).read_bytes()).hexdigest()}\n' for name in names))
    wasi=db/'llhttp-wasi-9.4.4';wasi.mkdir();(wasi/'+BUILD_INFO').write_text('PKGPATH=www/llhttp-wasi\n')
    wasm_dir=prefix/'share/llhttp-wasi';wasm_dir.mkdir(parents=True)
    wasi_contents=''
    for name in ('llhttp.wasm','llhttp_simd.wasm'):
        wasm=b'\0asm\x01\0\0\0';(wasm_dir/name).write_bytes(wasm)
        wasi_contents+=f'share/llhttp-wasi/{name}\n@comment MD5:{hashlib.md5(wasm,usedforsecurity=False).hexdigest()}\n'
    (wasi/'+CONTENTS').write_text(wasi_contents)
    out=root/'out';out.mkdir()
    cmd=[a.python,'-B',a.script,'--pkg-info',str(fake),'--pkgdb',str(db),'--prefix',str(prefix),'--runtime-prefix',str(runtime),'--out',str(out),'--recipe',str(recipe),'--python',a.python]
    def run(ok):
        r=subprocess.run(cmd,capture_output=True,text=True)
        assert (r.returncode==0)==ok,(r.returncode,r.stdout,r.stderr)
    run(True);assert str(prefix / rel).encode() in (out/rel).read_bytes();run(True)
    loader.write_bytes(b'changed');run(False);loader.write_bytes(data)
    (pkg/'+CONTENTS').write_text(contents+contents);run(False);(pkg/'+CONTENTS').write_text(contents)
    (pkg/'+BUILD_INFO').write_text(info.replace('www/undici','other/undici'));run(False);(pkg/'+BUILD_INFO').write_text(info)
    (recipe/'Makefile').write_text('changed');run(False);(recipe/'Makefile').write_text('selected Makefile')
    (out/rel).write_bytes(b'foreign');run(False)
    print('selected/replay and changed/unowned/ambiguous/foreign rejection PASS')
