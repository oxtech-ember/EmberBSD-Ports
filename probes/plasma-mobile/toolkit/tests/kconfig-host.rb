#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real native KConfig builder.
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'

abort 'Usage: kconfig-host.rb DISTFILES INSTALLED_HOST_QT ECM_CMAKE_DIR NEW_WORK' unless ARGV.length == 4
dist, qt, ecm, work = ARGV.map { |p| File.expand_path(p) }
abort 'This regression requires an installed Qt prefix' if File.exist?(File.join(qt, 'CMakeCache.txt'))
Dir.mkdir(work)
builder = File.expand_path('../cross/build-kconfig-tool.sh', __dir__)
cmake = ENV.fetch('CMAKE')
log = File.join(work, 'cmake-calls.jsonl')
observer = File.join(work, 'cmake-observer')
File.write(observer, <<~CODE)
  #!#{RbConfig.ruby}
  require 'json'
  File.open(ENV.fetch('KCONFIG_CMAKE_LOG'), 'a') { |f| f.puts(JSON.generate(ARGV)) }
  exec(ENV.fetch('KCONFIG_REAL_CMAKE'), *ARGV)
CODE
File.chmod(0755, observer)
environment = { 'CMAKE' => observer, 'KCONFIG_CMAKE_LOG' => log, 'KCONFIG_REAL_CMAKE' => cmake }
run = lambda do |name, prefix, output, env = environment|
  out, err, status = Open3.capture3(env, 'sh', builder, dist, prefix, ecm, output)
  File.write(File.join(work, name + '.log'), out + err)
  [out + err, status]
end
built = File.join(work, 'built')
out, status = run.call('installed', qt, built)
raise "Installed Qt failed: #{out}; inspect #{built}" unless status.success?
calls = File.readlines(log).map { |line| JSON.parse(line) }
raise 'The installed Qt prefix was sent to cmake --build' if calls.any? { |args| args[0, 2] == ['--build', qt] }
raise 'The real KConfig build was not invoked' unless calls.any? { |args| args[0, 2] == ['--build', File.join(built, 'build')] }
puts 'PASS: build native KConfig with the selected installed Qt'

generator = File.join(built, 'build/bin/kconfig_compiler_kf6')
consumer = File.join(work, 'consumer')
Dir.mkdir(consumer)
File.write(File.join(consumer, 'settings.kcfg'), <<~XML)
  <?xml version="1.0" encoding="UTF-8"?>
  <kcfg xmlns="http://www.kde.org/standards/kcfg/1.0">
    <kcfgfile name="native-kconfig-contract"/>
    <group name="Test"><entry name="Value" type="Int"><default>42</default></entry></group>
  </kcfg>
XML
File.write(File.join(consumer, 'settings.kcfgc'), "File=settings.kcfg\nClassName=Settings\nInherits=KCoreConfigSkeleton\nMutators=true\n")
out, err, status = Open3.capture3(generator, 'settings.kcfg', 'settings.kcfgc', chdir: consumer)
raise "Valid KConfig input failed: #{out}#{err}" unless status.success?
header = File.read(File.join(consumer, 'settings.h'))
source = File.read(File.join(consumer, 'settings.cpp'))
raise 'The requested configuration class was not generated' unless header.include?('class Settings') && header.include?('KCoreConfigSkeleton')
raise 'The requested integer default was not generated' unless source.match?(/ItemInt\([^;]*\b42\b/m)
puts 'PASS: generate the requested class and integer default'
bad = File.join(work, 'invalid')
Dir.mkdir(bad)
File.write(File.join(bad, 'settings.kcfg'), '<kcfg><broken></kcfg>')
FileUtils.cp(File.join(consumer, 'settings.kcfgc'), bad)
out, err, status = Open3.capture3(generator, 'settings.kcfg', 'settings.kcfgc', chdir: bad)
File.write(File.join(bad, 'diagnostic.log'), out + err)
raise 'Invalid XML was accepted' if status.success?
raise 'Invalid XML failed for a different cause' unless (out + err).include?('Parse error in settings.kcfg')
raise 'Invalid XML generated output' unless Dir[File.join(bad, '*.{h,cpp}')].empty?
puts 'PASS: reject malformed XML without generated output'

# A selected incomplete prefix must not silently use another installed Qt.
missing = File.join(work, 'missing-xml')
FileUtils.mkdir_p(File.join(missing, 'lib/cmake'))
File.symlink(File.join(qt, 'bin'), File.join(missing, 'bin'))
%w[Qt6 Qt6Core Qt6LinguistTools].each do |name|
  File.symlink(File.join(qt, 'lib/cmake', name), File.join(missing, 'lib/cmake', name))
end
out, status = run.call('missing-xml', missing, File.join(work, 'missing-output'))
raise 'Missing selected Qt Xml was accepted' if status.success?
raise "Missing Xml failed for a different cause: #{out}" unless out.include?('Missing native Qt module: Xml')
raise 'Missing Xml reached CMake' unless File.readlines(log).map { |line| JSON.parse(line) } == calls
puts 'PASS: reject missing selected Xml before CMake fallback'

# Preserve the original build-tree contract. Stop at the actual Xml build call.
build_qt = File.join(work, 'build-tree-qt')
Dir.mkdir(build_qt)
File.symlink(File.join(qt, 'bin'), File.join(build_qt, 'bin'))
File.symlink(File.join(qt, 'lib'), File.join(build_qt, 'lib'))
File.write(File.join(build_qt, 'CMakeCache.txt'), "# Dispatch fixture; not a Qt build.\n")
probe = File.join(work, 'observe-xml-build')
File.write(probe, <<~CODE)
  #!#{RbConfig.ruby}
  abort 'Unexpected CMake request' unless ARGV == ['--build', ENV.fetch('KCONFIG_BUILD_QT'), '--target', 'Xml', '--parallel', ENV.fetch('JOBS', '2')]
  warn 'Observed required Qt Xml build'
  exit 73
CODE
File.chmod(0755, probe)
output = File.join(work, 'build-tree-output')
_, status = run.call('build-tree', build_qt, output, { 'CMAKE' => probe, 'KCONFIG_BUILD_QT' => build_qt })
raise 'The Xml build failure was ignored' unless status.exitstatus == 73
raise 'The build-tree Xml request changed' unless File.read(File.join(output, 'qt-xml-build.log')).include?('Observed required Qt Xml build')
puts 'PASS: preserve build-tree Xml build and propagate its failure'
puts "PASS: five native KConfig builder and generator cases; tooling=#{built}/tooling"
