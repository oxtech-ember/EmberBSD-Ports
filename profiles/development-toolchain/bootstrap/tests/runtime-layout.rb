#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Execute the install-directory decisions from the actual prepared configure scripts.
require 'open3'
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
puts 'PASS: actual upstream libgcc/libstdc++ configure defaults differ; explicit canonical layout agrees for both targets'
