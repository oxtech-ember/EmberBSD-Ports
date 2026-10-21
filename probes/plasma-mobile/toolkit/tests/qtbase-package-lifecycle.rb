#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native pkgtools lifecycle on labelled fixtures.
require 'fileutils'
require 'digest'
require 'find'
require 'open3'
abort 'Usage: qtbase-package-lifecycle.rb HOST_PREFIX SPLIT_FIXTURE NEW_OUTPUT' unless ARGV.length == 3
host, fixture = ARGV.first(2).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[2])
abort 'new absolute output required' unless ARGV[2].start_with?('/') && !File.exist?(work)
Dir.mkdir(work)
tools = %w[pkg_create pkg_add pkg_info pkg_delete].to_h { |name| [name, host + '/sbin/' + name] }
run = lambda do |label, tool, *arguments, expect: true|
  output, status = Open3.capture2e({'PKG_PATH' => nil}, tools.fetch(tool), *arguments, chdir: work)
  File.write(work + '/' + label + '.log', output)
  abort label + ': ' + output unless status.success? == expect
  output
end
version = run.call('pkgtools-version', 'pkg_create', '-V').strip
abort 'actual pkg_create version missing' unless version.match?(/\A[0-9]{8}\z/)
File.write(work + '/BUILD_INFO', <<~INFO)
  OPSYS=NetBSD
  OS_VERSION=11.0
  MACHINE_ARCH=x86_64
  OBJECT_FMT=ELF
  LICENSE=2-clause-bsd
  PKGTOOLS_VERSION=#{version}
  EMBERBSD_TEST_FIXTURE=yes
INFO
File.write(work + '/COMMENT', 'Labelled Qtbase package partition fixture')
File.write(work + '/DESCR', "Synthetic text payloads for pkgtools contracts. This is not a Qt binary package.\n")
old = 'qt6-qtbase-6.12.0'
runtime = 'qt6-qtbase-6.12.0nb3'
sdk = 'qt6-qtbase-devel-6.12.0nb4'
packages = {}
{
  old => ['normalized-full', 'full', nil],
  runtime => ['runtime-stage', 'runtime', nil],
  sdk => ['devel-stage', 'devel', runtime]
}.each do |name, (stage, manifest, dependency)|
  prefix = fixture + '/' + stage + '/usr/pkg'
  abort 'prepared source-contract fixture required' unless File.directory?(prefix)
  files = File.read(fixture + '/' + manifest + '/.PLIST_nokeywords')
  text = "@name #{name}\n@cwd /usr/pkg\n"
  text += "@pkgdep #{dependency}\n@pkgcfl qt6-qtbase<6.12.0nb3\n" if dependency
  text += files
  list = work + '/' + name + '.plist'
  File.write(list, text)
  archive = work + '/' + name + '.tgz'
  run.call('create-' + name, 'pkg_create', '-l', '-U', '-p', prefix, '-I', '/usr/pkg',
    '-K', work + '/creation-pkgdb', '-B', work + '/BUILD_INFO', '-f', list,
    '-c', work + '/COMMENT', '-d', work + '/DESCR', archive)
  packages[name] = archive
end
destination = work + '/root'
Dir.mkdir(destination)
database = destination + '/usr/pkg/pkgdb'
install = ['-K', '/usr/pkg/pkgdb', '-P', destination, '-m', 'NetBSD/x86_64 11.0']
remove = ['-K', '/usr/pkg/pkgdb', '-P', destination]
snapshot = lambda do |prefix, installed: false|
  files = {}
  Find.find(prefix) do |path|
    if installed && path == database
      Find.prune
    elsif !File.directory?(path) || File.symlink?(path)
      files[path.delete_prefix(prefix + '/')] = File.symlink?(path) ?
        ['symlink', File.readlink(path)] : ['file', Digest::SHA256.file(path).hexdigest]
    end
  end
  files
end
full_bytes = snapshot.call(fixture + '/normalized-full/usr/pkg')
runtime_bytes = snapshot.call(fixture + '/runtime-stage/usr/pkg')
verify_installed = lambda do |expected|
  abort 'installed payload differs from the selected stage' unless snapshot.call(destination + '/usr/pkg', installed: true) == expected
end
registered = lambda do |name|
  run.call('registered-' + name, 'pkg_info', '-K', database, '-e', name).strip == name
end
run.call('install-old-full', 'pkg_add', *install, packages.fetch(old))
verify_installed.call(full_bytes)
abort 'old complete fixture absent' unless File.file?(destination + '/usr/pkg/qt6/bin/qmake') && registered.call(old)
run.call('replace-with-runtime', 'pkg_add', '-u', *install, packages.fetch(runtime))
verify_installed.call(runtime_bytes)
abort 'runtime replacement retained SDK files' if File.exist?(destination + '/usr/pkg/qt6/bin/qmake')
abort 'runtime replacement lost qtpaths or registration' unless File.file?(destination + '/usr/pkg/qt6/bin/qtpaths') && registered.call(runtime)
run.call('install-sdk', 'pkg_add', *install, packages.fetch(sdk))
verify_installed.call(full_bytes)
abort 'SDK package not registered' unless registered.call(sdk)
abort 'SDK manifest omitted target tools' unless File.file?(destination + '/usr/pkg/qt6/libexec/moc')
deps = run.call('sdk-dependencies', 'pkg_info', '-K', database, '-q', '-n', sdk)
abort 'SDK exact runtime dependency not registered' unless deps.lines.map(&:strip).include?(runtime)
run.call('refuse-runtime-delete', 'pkg_delete', *remove, runtime, expect: false)
run.call('delete-sdk', 'pkg_delete', *remove, sdk)
verify_installed.call(runtime_bytes)
abort 'deleting SDK removed runtime qtpaths' unless File.file?(destination + '/usr/pkg/qt6/bin/qtpaths')
run.call('delete-runtime', 'pkg_delete', *remove, runtime)
verify_installed.call({})
abort 'runtime files survived deletion' if File.exist?(destination + '/usr/pkg/qt6/bin/qtpaths')
run.call('reinstall-runtime', 'pkg_add', *install, packages.fetch(runtime))
verify_installed.call(runtime_bytes)
abort 'runtime reinstall restored development tools' if File.exist?(destination + '/usr/pkg/qt6/bin/qmake')
run.call('delete-reinstalled-runtime', 'pkg_delete', *remove, runtime)
verify_installed.call({})
puts 'PASS: normal pkg_create/pkg_add replace a full fixture with runtime, add/remove SDK, enforce dependencies and reinstall runtime'
puts 'SCOPE: private synthetic text fixtures; no compiled Qt, target execution or shared package database changes'
