#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted actual patched Meson/Python and recipe guards.
# This executes production fragments with explicit host tool/metadata boundaries.
require 'fileutils'
require 'open3'
abort 'Usage: configuration.rb PATCHED_MESA NEW_WORK' unless ARGV.size == 2
source, work = ARGV.map { |p| File.expand_path(p) }
Dir.mkdir(work)
profile=File.expand_path('..', __dir__)
python=ENV.fetch('TEST_PYTHON')
meson=ENV.fetch('TEST_MESON')
make=ENV.fetch('BMAKE','bmake')
def run!(log, *cmd, ok: true, env: {})
  out,status=Open3.capture2e(env,*cmd)
  File.write(log,out)
  abort "Unexpected result #{status.exitstatus}: #{log}" unless status.success? == ok
  out
end
patched=File.read("#{source}/meson.build")
block=patched[/python_version_req = .*?(?=\nif cc.get_id\(\))/m]
abort 'Missing production Python block' unless block && block.include?("python_exec_list = ['@PYTHONBIN@']")
# Reuse upstream option declarations. This is not a complete Mesa configuration.
FileUtils.mkdir_p("#{work}/project")
FileUtils.cp("#{source}/meson.options", "#{work}/project/meson.options")
File.write("#{work}/project/meson.build", "project('mesa-package-source-check', version: '26.2.4')\n"+block.gsub('@PYTHONBIN@',python)+"\nmessage('SELECTED_PYTHON=' + prog_python.full_path())\n")
recipe=File.read("#{profile}/recipes/graphics/MesaLib/Makefile")
# Only actual recipe option assignments, not wrapper/compiler flags.
args=recipe.lines.grep(/^MESON_ARGS\+=/).flat_map { |l| l.split[1..] }
# pkgsrc's Meson integration supplies --buildtype=plain itself. Supplying the
# same option a second time in recipe arguments is rejected by current Meson.
run!("#{work}/python-positive.log",python,meson,'setup',"#{work}/build", "#{work}/project",'--wrap-mode=nodownload','--buildtype=plain',*args)
run!("#{work}/options.json",python,meson,'introspect','--buildoptions',"#{work}/build")
# Each wrapper runs the real selected interpreter with one actual failed import.
%w[mako packaging yaml].each do |mod|
  Dir.mkdir("#{work}/bad-#{mod}")
  File.write("#{work}/bad-#{mod}/#{mod}.py", "raise ImportError('injected missing #{mod}')\n")
  path="#{work}/python-no-#{mod}"
  File.write(path,"#!/bin/sh\nexec env PYTHONPATH='#{work}/bad-#{mod}:#{ENV.fetch('PYTHONPATH','')}' '#{python}' \"$@\"\n")
  FileUtils.chmod(0755,path)
  File.write("#{work}/project/meson.build", "project('mesa-package-source-check', version: '26.2.4')\n"+block.gsub('@PYTHONBIN@',path))
  run!("#{work}/missing-#{mod}.log",python,meson,'setup',"#{work}/build-no-#{mod}","#{work}/project",ok:false)
end
%w[missing wrong].each do |kind|
  path="#{work}/python-#{kind}"
  if kind=='wrong'
    File.write(path,"#!/bin/sh\nprintf 'Python 3.13.0\\n'\n"); FileUtils.chmod(0755,path)
  end
  File.write("#{work}/project/meson.build", "project('mesa-package-source-check', version: '26.2.4')\n"+block.gsub('@PYTHONBIN@',path))
  run!("#{work}/python-#{kind}.log",python,meson,'setup',"#{work}/build-#{kind}","#{work}/project",ok:false)
end
# Extract the actual production recipe pre-configure target without rewriting it.
commands=recipe[/^pre-configure:\n(.*?)(?=^\.include)/m,1]
abort 'Missing production tool guards' unless commands
config="#{work}/llvm-config"
File.write(config, <<'SH')
#!/bin/sh
case "$*" in
  --version) echo "${TEST_LLVM_VERSION:-23.1.3}" ;;
  '--shared-mode --link-shared') echo "${TEST_LLVM_SHARED:-shared}" ;;
  --has-rtti) echo YES ;;
  '--link-shared --libs core executionengine orcjit native') echo '-lLLVM-23' ;;
  *) exit 2 ;;
esac
SH
FileUtils.chmod(0755,config)
File.write("#{work}/guards.mk", "TEST=test\nUSE_CROSS_COMPILE=no\nTOOL_PYTHONBIN=#{python}\nLLVM_CONFIG_PATH=#{config}\npre-configure:\n"+commands)
run!("#{work}/llvm-metadata-positive.log",make,'-r','-m','/','-f',"#{work}/guards.mk",'pre-configure')
run!("#{work}/llvm-missing.log",make,'-r','-m','/','-f',"#{work}/guards.mk",'pre-configure',"LLVM_CONFIG_PATH=#{work}/absent",ok:false)
run!("#{work}/llvm-version.log",make,'-r','-m','/','-f',"#{work}/guards.mk",'pre-configure',ok:false,env:{'TEST_LLVM_VERSION'=>'13.0.1'})
run!("#{work}/llvm-static.log",make,'-r','-m','/','-f',"#{work}/guards.mk",'pre-configure',ok:false,env:{'TEST_LLVM_SHARED'=>'static'})
# Execute upstream installation logic against source-derived dummy staging only.
FileUtils.mkdir_p("#{work}/stage/lib/dri")
File.write("#{work}/stage/lib/dri/libdril_dri.so",'dummy master, not a DSO')
run!("#{work}/megadriver.log",python,"#{source}/bin/install_megadrivers.py",'libdril_dri.so','lib/dri','swrast_dri.so','kms_swrast_dri.so','virtio_gpu_dri.so','--libname-suffix','so',env:{'MESON_INSTALL_DESTDIR_PREFIX'=>"#{work}/stage"})
%w[swrast kms_swrast virtio_gpu].each { |d| abort 'Wrong upstream driver target' unless File.readlink("#{work}/stage/lib/dri/#{d}_dri.so")=='libdril_dri.so' }
abort 'Master removed' unless File.file?("#{work}/stage/lib/dri/libdril_dri.so")
puts 'PASS: production Python import/version selection, actual recipe LLVM guards, upstream driver symlinks (host tools/metadata; no native Mesa configuration)'
