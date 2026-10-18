#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; execute the actual upstream layout and recursion decisions.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import re
import shlex
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'runtime/recipe/files'))
import sdk_source
args=sdk_source.arguments(sys.argv[1:])
for path in (Path(__file__).resolve().parents[2],Path(__file__).resolve().parents[1]):sys.path.insert(0,str(path))
from host import capture, require
from pipeline import Bootstrap


def main(args):
    require(len(args)==1,'Usage: runtime-layout.py PREPARED_GCC_SOURCE --sdk-source SOURCE')
    source=Path(args[0])
    gcc=re.search(r'# Check whether --with-toolexeclibdir was given\..*?(?=# Command-line options\.)',(source/'libgcc/configure').read_text(),re.S)
    cxx=re.search(r'# Check whether --with-toolexeclibdir was given\..*?(?=  \{ \$as_echo "\$as_me:.*?checking for install location)',(source/'libstdc++-v3/configure').read_text(),re.S)
    require(gcc and cxx,'Upstream configure layout sections changed')
    for target in ('x86_64--netbsd','aarch64--netbsd'):
        for override in (None,'/usr/pkg/gcc16/lib'):
            initial='version_specific_libs=no\nwith_cross_host=build-host\ngxx_include_dir=/usr/pkg/gcc16/include/c++\nglibcxx_toolexecdir=no\nCXX=multios\nmultios() { echo .; }\nhost_alias='+target+'\ntarget_alias='+target+'\n'
            if override:initial+='with_toolexeclibdir='+override+'\n'
            result=capture(['sh','-eu'],input=(initial+gcc[0]+cxx[0]+'printf "%s\\n%s\\n" "$slibdir" "$glibcxx_toolexeclibdir"\n').encode())
            expected=[override,override] if override else ['$(exec_prefix)/$(host_noncanonical)/lib','${toolexecdir}/lib']
            require(result.splitlines()==expected,'Actual upstream install layout differs')
    top=(source/'configure').read_text()
    parser=re.search(r'^  -no-recursion \|.*?no_recursion=yes ;;',top,re.M|re.S)
    removal=re.search(r'^extrasub_build=\n.*?(?=^# Do the final fixup)',top,re.M|re.S)
    require(parser and removal,'Upstream recursion decisions changed')
    for resume in ('no','yes','runtime'):
        with tempfile.TemporaryDirectory(prefix='gcc-layout-') as temporary:
            work=Path(temporary).resolve()
            preserved=['build-host/libiberty/Makefile','gcc/Makefile','libcpp/Makefile']
            for name in preserved:
                (work/name).parent.mkdir(parents=True,exist_ok=True);(work/name).write_text('completed host configuration')
            state=Bootstrap.__new__(Bootstrap)
            state.triplet='x86_64--netbsd';state.sysroot=Path('/sysroot');state.math=Path('/math');state.tools={'as':'/kernel/bin/as','ld':'/kernel/bin/ld'};state.target='amd64';state.gomp=False;state.atomic=False;state.resume=resume
            initial='set -- '+' '.join(shlex.quote(value) for value in state.configure_args())+'\nno_recursion=\nfor ac_option; do\ncase $ac_option in\n'+parser[0]+'\n*) : ;;\nesac\ndone\n'
            initial+="build_configdirs=libiberty\nbuild_subdir=build-host\nconfigdirs='gcc libcpp'\ntarget_configdirs='libgcc libstdc++-v3'\ntarget_subdir=target\nbootstrap_fixincludes=no\nbootstrap_suffix=no-bootstrap\nbootstrap_target_libs=\n"
            capture(['sh','-eu'],cwd=work,input=(initial+removal[0]).encode())
            for name in preserved:
                require((work/name).is_file()==(resume=='runtime'),'Host Makefile preservation differs')
                if (work/name).exists():require((work/name).read_text()=='completed host configuration','Host configuration changed')
            require(not (work/'target/libgcc/Makefile').exists() and not (work/'target/libstdc++-v3/Makefile').exists(),'Target metadata restored')
    naming=re.search(r'\tsunos\)\n\s+major="\.\$current"\n\s+versuffix="\.\$current\.\$revision"\n\s+;;',(source/'ltmain.sh').read_text())
    require(naming,'Actual NetBSD libtool branch changed')
    for name,expected in {'libgomp':('1:0:0','.1','.1.0'),'libatomic':('3:0:2','.3','.3.0')}.items():
        configure=(source/name/'configure').read_text()
        version=re.findall(r'^libtool_VERSION=([0-9]+:[0-9]+:[0-9]+)$',configure,re.M)
        require(version==[expected[0]] and re.search(r'^netbsd\*\)\n  version_type=sunos$',configure,re.M),'NetBSD runtime naming changed')
        current,revision,age=expected[0].split(':')
        result=capture(['sh','-eu'],input=('current='+current+'\nrevision='+revision+'\nage='+age+'\ncase sunos in\n'+naming[0]+'\nesac\nprintf "%s\\n%s\\n" "$major" "$versuffix"\n').encode())
        require(result.splitlines()==list(expected[1:]),'Actual NetBSD SONAME calculation differs')
    print('PASS: actual upstream install layout, runtime recursion and NetBSD optional SONAME branches')

if __name__=='__main__':
    try:
        sdk_source.install_signal_handlers()
        main(args)
    except Exception as error:
        print(str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
