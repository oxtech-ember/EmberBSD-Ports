#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Execute the install-directory decisions from the actual prepared configure scripts.
require 'open3'
require 'tmpdir'
require 'fileutils'
abort 'Usage: runtime-layout.rb PREPARED_GCC_SOURCE' unless ARGV.length == 1
source = ARGV.fetch(0)
gcc = File.read(source + '/libgcc/configure')
cxx = File.read(source + '/libstdc++-v3/configure')
gcc = gcc[/# Check whether --with-toolexeclibdir was given\..*?(?=# Command-line options\.)/m]
cxx = cxx[/# Check whether --with-toolexeclibdir was given\..*?(?=  \{ \$as_echo "\$as_me:.*?checking for install location)/m]
abort 'FAIL: upstream configure layout sections changed' unless gcc && cxx
%w[x86_64--netbsd aarch64--netbsd].each do |target|
  [nil, '/usr/pkg/gcc16/lib'].each do |override|
    initial = "version_specific_libs=no\nwith_cross_host=build-host\ngxx_include_dir=/usr/pkg/gcc16/include/c++\nglibcxx_toolexecdir=no\nCXX=multios\nmultios() { echo .; }\n"
    initial += "host_alias=#{target}\ntarget_alias=#{target}\n"
    initial += "with_toolexeclibdir=#{override}\n" if override
    output, status = Open3.capture2('sh', '-eu', stdin_data: initial + gcc + cxx + 'printf "%s\n%s\n" "$slibdir" "$glibcxx_toolexeclibdir"' + "\n")
    expected = override ? [override, override] : ['$(exec_prefix)/$(host_noncanonical)/lib', '${toolexecdir}/lib']
    abort "FAIL: #{target} actual upstream configure install layout" unless status.success? && output.lines.map(&:strip) == expected
  end
end
top = File.read(source + '/configure')
arguments = File.read(File.expand_path('../build.sh', __dir__))[/^set -- --target=.*?(?=^# Preserve)/m]
parser = top[/^  -no-recursion \|.*?no_recursion=yes ;;/m]
removal = top[/^extrasub_build=\n.*?(?=^# Do the final fixup)/m]
abort 'FAIL: upstream configure recursion decisions changed' unless arguments && parser && removal
%w[no yes runtime].each do |resume|
  Dir.mktmpdir('ember-runtime-configure-', '/tmp') do |work|
    preserved = %w[build-host/libiberty/Makefile gcc/Makefile libcpp/Makefile]
    preserved.each do |name|
      FileUtils.mkdir_p(File.dirname(work + '/' + name))
      File.write(work + '/' + name, 'completed host configuration')
    end
    # Target metadata has already been moved by backup_runtime_resume.
    initial = "target=amd64\ntriplet=x86_64--netbsd\nkernel=/kernel\nsysroot=/sysroot\nmath=/math\nresume=#{resume}\nruntime_gomp=no\nruntime_atomic=no\n"
    initial += arguments + "\nno_recursion=\nfor ac_option; do\ncase $ac_option in\n" + parser + "\n*) : ;;\nesac\ndone\n"
    initial += "build_configdirs=libiberty\nbuild_subdir=build-host\nconfigdirs='gcc libcpp'\ntarget_configdirs='libgcc libstdc++-v3'\ntarget_subdir=target\nbootstrap_fixincludes=no\nbootstrap_suffix=no-bootstrap\nbootstrap_target_libs=\n"
    _, stderr, status = Open3.capture3('sh', '-eu', stdin_data: initial + removal, chdir: work)
    abort "FAIL: actual upstream configure recursion decision: #{stderr}" unless status.success?
    preserved.each do |name|
      exists = File.file?(work + '/' + name)
      abort "FAIL: #{resume} recovery changed upstream host Makefile preservation: #{name}" unless exists == (resume == 'runtime')
      abort 'FAIL: completed host configuration changed' if exists && File.read(work + '/' + name) != 'completed host configuration'
    end
    abort 'FAIL: target configure metadata was restored' if File.exist?(work + '/target/libgcc/Makefile') || File.exist?(work + '/target/libstdc++-v3/Makefile')
  end
end
puts 'PASS: actual upstream recursion parser/removal preserves host Makefiles only for runtime recovery'
puts 'PASS: actual upstream libgcc/libstdc++ configure defaults differ; explicit canonical layout agrees for both targets'

# GCC's bundled NetBSD libtool uses current, not current-age, as the SONAME.
# Execute its actual sunos branch; do not substitute Linux's libatomic ABI.
libtool = File.read(source + '/ltmain.sh')
naming = libtool[/\tsunos\)\n\s+major="\.\$current"\n\s+versuffix="\.\$current\.\$revision"\n\s+;;/]
abort 'FAIL: actual libtool sunos version branch changed' unless naming
{'libgomp' => ['1:0:0', '.1', '.1.0'], 'libatomic' => ['3:0:2', '.3', '.3.0']}.each do |name, expected|
  configure = File.read(source + '/' + name + '/configure')
  version = configure[/^libtool_VERSION=([0-9]+:[0-9]+:[0-9]+)$/, 1]
  abort "FAIL: #{name} pinned version or NetBSD naming changed" unless version == expected[0] && configure.match?(/^netbsd\*\)\n  version_type=sunos$/)
  current, revision, age = version.split(':')
  initial = "current=#{current}\nrevision=#{revision}\nage=#{age}\ncase sunos in\n"
  out, err, status = Open3.capture3('sh', '-eu', stdin_data: initial + naming + "\nesac\nprintf '%s\\n%s\\n' \"$major\" \"$versuffix\"\n")
  abort "FAIL: actual #{name} NetBSD SONAME calculation: #{err}" unless status.success? && out.lines.map(&:chomp) == expected.drop(1)
end
puts 'PASS: actual GCC16 NetBSD libtool selects libgomp.so.1 and libatomic.so.3; no target runtime execution'
