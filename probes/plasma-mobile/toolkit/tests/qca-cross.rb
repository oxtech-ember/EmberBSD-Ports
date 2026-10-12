#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual recipe and upstream certstore selection.
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'Usage: qca-cross.rb PKGSRC MAKECONF CONFIGURED_QCA_SOURCE NEW_WORK' unless ARGV.size == 4
pkgsrc, config, source, work = ARGV.map { |p| File.expand_path(p) }
Dir.mkdir(work)
bmake = ENV.fetch('BMAKE', 'bmake')
cmake = ENV.fetch('CMAKE', 'cmake')
query = lambda do |mode, variable|
  text, status = Open3.capture2e({'MAKECONF' => config}, bmake, '-C', "#{pkgsrc}/security/qca2-qt6", "USE_CROSS_COMPILE=#{mode}", '-V', "${#{variable}}")
  abort text unless status.success?
  File.write("#{work}/#{mode}-#{variable}.txt", text)
  Shellwords.split(text)
end
%w[yes no].each do |mode|
  args = query.call(mode, 'CMAKE_CONFIGURE_ARGS')
  abort 'OpenSSL plugin disabled' unless args.include?('-DBUILD_PLUGINS=ossl')
  abort 'Upstream tests disabled' unless args.include?('-DBUILD_TESTS=ON')
end
args = query.call('yes', 'CMAKE_CONFIGURE_ARGS')
target = args.grep(/\A-Dqca_CERTSTORE=/).last&.split('=', 2)&.last
abort 'Missing target certstore' unless target&.end_with?('/share/mozilla-rootcerts/cacert.pem')
env = query.call('yes', 'CONFIGURE_ENV').grep(/\AQC_CERTSTORE_PATH=/)
abort 'Certstore environment differs from target' unless env == ["QC_CERTSTORE_PATH=#{target}"]
abort 'Cross install prefix is not explicit' unless args.include?('-DQCA_INSTALL_IN_QT_PREFIX=OFF')
abort 'CMake exports are not relocatable' unless args.include?('-DUSE_RELATIVE_PATHS=ON')
prefix = args.grep(/\A-DQCA_PREFIX_INSTALL_DIR=/).last&.split('=', 2)&.last
abort 'Certstore and installation prefix disagree' unless target == prefix + '/share/mozilla-rootcerts/cacert.pem'
body = File.read("#{source}/CMakeLists.txt")
block = body[/message\(STATUS "Checking for certstore\.\."\).*?(?=add_definitions\( -DQCA_SYSTEMSTORE_PATH)/m]
abort 'Upstream selection block changed' unless block
# Keep upstream control flow; substitute only the host candidates with a
# deterministic existing host fixture, independent of the runner's CA store.
host_cert = "#{work}/host-cacert.pem"
File.write(host_cert, "host fixture\n")
abort 'Upstream host candidate list changed' unless block.sub!(/set\( toTry\s+.*?\n    \)/m, "set( toTry \"#{host_cert}\" )")
script = "set(qca_CERTSTORE \"#{target}\" CACHE PATH \"target trust store\")\n" + block + "\nfile(WRITE \"#{work}/selected.txt\" \"${qca_CERTSTORE}\")\n"
File.write("#{work}/select.cmake", script)
[[nil, host_cert, 'negative'], [target, target, 'configured']].each do |value, expected, name|
  output, status = Open3.capture2e({'QC_CERTSTORE_PATH' => value}, cmake, '-P', "#{work}/select.cmake")
  File.write("#{work}/#{name}.log", output)
  abort output unless status.success?
  abort "Unexpected #{name} selection" unless File.read("#{work}/selected.txt") == expected
end
puts 'PASS: actual native/cross QCA recipe, OpenSSL and tests; host CA override reproduces and configured target CA wins'
