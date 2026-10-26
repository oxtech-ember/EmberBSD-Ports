#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run selected C/C++ preprocessors through Cargo wrappers; no Rust crate runs."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import tomllib

HELPER=Path(__file__).resolve().parents[1]/'cargo-config.py'
spec=importlib.util.spec_from_file_location('cargo_config',HELPER)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('cc','cxx','ar','tool-path'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--shell',type=Path,required=True)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='cargo-cppflags-') as temporary:
        root=Path(temporary).resolve()
        rustc=root/'rustc'
        rustc.write_text('#!'+sys.executable+'\nprint("host: aarch64-apple-darwin")\n');rustc.chmod(0o755)
        vendor=root/'vendor';vendor.mkdir()
        inputs={}
        for side,number in (('host',42),('target',73)):
            directory=root/(side+' headers with spaces');directory.mkdir()
            (directory/'cpp_only.h').write_text('#define HEADER_SIDE '+str(number)+'\n')
            source=root/(side+'.c')
            source.write_text('#include <cpp_only.h>\n#ifndef CPP_ONLY\n#error missing_cpp_only\n#endif\n#if CPP_ONLY != HEADER_SIDE\n#error wrong_side\n#endif\n#if ORDER != 2\n#error wrong_flag_order\n#endif\nTEXT CPP_ONLY ORDER\n')
            inputs[side]=(source,shlex.join(['-I'+str(directory),'-DCPP_ONLY='+str(number),'-DORDER=1','-DTEXT="text with spaces"']),number)
        counts={'passed':0,'missing_cppflags_refused':0,'missing_define_refused':0}
        for control in ('fixed','no_cppflags','no_define'):
            cppflags={side:value[1] for side,value in inputs.items()}
            if control=='no_cppflags':
                cppflags={side:'' for side in inputs}
            elif control=='no_define':
                cppflags={side:shlex.join([word for word in shlex.split(value) if not word.startswith('-DCPP_ONLY=')]) for side,value in cppflags.items()}
            config=root/control/'config.toml'
            flags='-UORDER -DORDER=2'
            module.configure(config=config,vendor=vendor,output=root/'out',rustc=rustc,shell=args.shell,
                             tool_path=args.tool_path,mode='cross',target='x86_64-apple-darwin',
                             host_cc=args.cc,host_cxx=args.cxx,host_ar=args.ar,
                             target_cc=args.cc+' --target=x86_64-apple-darwin',
                             target_cxx=args.cxx+' --target=x86_64-apple-darwin',target_ar=args.ar,
                             host_cppflags=cppflags['host'],target_cppflags=cppflags['target'],
                             host_cflags=flags,host_cxxflags=flags,target_cflags=flags,target_cxxflags=flags)
            data=tomllib.loads(config.read_text())
            for side,triple in (('host','aarch64-apple-darwin'),('target','x86_64-apple-darwin')):
                for role,language in (('CC','c'),('CXX','c++')):
                    wrapper=data['env'][role+'_'+triple]['value']
                    selected_flags=data['env'][('CFLAGS' if role=='CC' else 'CXXFLAGS')+'_'+triple]['value']
                    argv=[wrapper,*shlex.split(selected_flags),'-x',language,'-E','-P',str(inputs[side][0])]
                    result=subprocess.run(argv,text=True,capture_output=True)
                    if control=='fixed':
                        expected='"text with spaces" '+str(inputs[side][2])+' 2'
                        assert result.returncode==0 and result.stdout.strip()==expected,(argv,result.stdout,result.stderr)
                        counts['passed']+=1
                    else:
                        assert result.returncode!=0,(argv,result.stdout,result.stderr)
                        if control=='no_cppflags':
                            assert 'cpp_only.h' in result.stderr,result.stderr
                            counts['missing_cppflags_refused']+=1
                        else:
                            assert 'missing_cpp_only' in result.stderr,result.stderr
                            counts['missing_define_refused']+=1
        print(json.dumps(dict(counts,scope='actual selected C/C++ preprocessing; Rust identity is a fixture; no cc crate or target binary execution')))


if __name__=='__main__':
    main()
