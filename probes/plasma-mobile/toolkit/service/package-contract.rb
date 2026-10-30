#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual pkgtools and generated rc.d hooks.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: package-contract.rb HOST_PREFIX WRKDIR STAGED_PREFIX DEPENDS_FILE NEW_OUTPUT' unless ARGV.size == 5
host, built, staged = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[4])
abort 'Select a new absolute output directory' unless ARGV[4].start_with?('/') && !File.exist?(work)
Dir.mkdir(work, 0700)
tools = %w[pkg_create pkg_add pkg_delete pkg_info].to_h { |name| [name, host + '/sbin/' + name] }
prefix = work + '/prefix'
database = work + '/pkgdb'
FileUtils.mkdir_p([prefix, database])
config = work + '/pkg_install.conf'
File.write(config, "PKG_DBDIR=#{database}\nPKG_REFCOUNT_DBDIR=#{work}/refcount\n")
environment = {'PKG_PATH'=>nil, 'PKG_DBDIR'=>database,
  'PKG_REFCOUNT_DBDIR'=>work + '/refcount', 'LC_ALL'=>'C', 'TMPDIR'=>work}
commands = []
run = lambda do |label, argv, expect: true, env: {}, cwd: work|
  # -P has different meanings in pkg_create and pkg_add. Do not use it here.
  raise 'Unexpected destination-root flag' if argv.include?('-P')
  out, err, status = Open3.capture3(environment.merge(env), *argv, chdir: cwd)
  File.write(work + '/' + label + '.stdout', out)
  File.write(work + '/' + label + '.stderr', err)
  commands << {label:label, argv:argv, exit:status.exitstatus,
    stdout_sha256:Digest::SHA256.hexdigest(out), stderr_sha256:Digest::SHA256.hexdigest(err)}
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  raise "#{label}: #{out}#{err}" unless status.success? == expect
  out + err
end
version = run.call('version', [tools['pkg_create'], '-V']).strip
raise 'Missing pkgtools version' unless version.match?(/\A\d{8}\z/)
File.write(work + '/BUILD_INFO', "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=aarch64\nOBJECT_FMT=ELF\nLICENSE=2-clause-bsd\nPKGTOOLS_VERSION=#{version}\nEMBERBSD_TEST_FIXTURE=yes\n")
File.write(work + '/COMMENT', 'Labelled Plasma service lifecycle fixture')
File.write(work + '/DESCR', "Real canonical service bytes with synthetic dependency providers. No desktop is executed.\n")
files = %w[libexec/ember-plasma-service share/examples/rc.d/ember_plasma]
plist = File.readlines(built + '/.PLIST', chomp:true).reject { |line| line.start_with?('@') || line.empty? }
raise 'Unexpected actual staged manifest' unless plist.sort == files.sort
files.each { |file| raise 'Missing actual staged service' unless File.file?(staged + '/' + file) }
hooks = %w[+INSTALL +DEINSTALL].to_h do |file|
  path = built + '/.pkgdb/' + file
  text = File.read(path)
  raise 'Host path in target hook' if text.match?(%r{/(?:Volumes|Users|private/tmp|opt/homebrew)/})
  run.call('syntax-' + file.delete_prefix('+'), ['/bin/sh', '-n', path])
  [file, path]
end
minimum = {
  'plasma6-plasma-desktop'=>'6.8.2', 'plasma6-plasma-workspace'=>'6.8.2nb3',
  'plasma6-kwin'=>'6.8.2nb2', 'qt6-qtbase'=>'6.12.0nb3', 'perl'=>'5.44.0',
  'dbus'=>'1.16.2', 'xwayland'=>'24.1.14nb3'
}
dependencies = {}
File.read(ARGV[3]).split.each do |dependency|
  match = /\A([\w+.-]+)>=(\d[\w.]*)\.?:\.\.\/\.\.\/[\w+.-]+\/[\w+.-]+\z/.match(dependency)
  raise 'Unexpected actual recipe dependency: ' + dependency unless match
  raise 'Duplicate dependency' if dependencies.key?(match[1])
  dependencies[match[1]] = match[2]
end
minimum.each { |base, rev| raise 'Missing current dependency: ' + base unless dependencies[base] == rev }
create = lambda do |name, source, paths, deps: {}, scripts: false|
  list = work + '/' + name + '.plist'
  File.write(list, "@name #{name}\n@cwd /usr/pkg\n" + deps.map { |n,v| "@pkgdep #{n}>=#{v}\n" }.join + paths.join("\n") + "\n")
  archive = work + '/' + name + '.tgz'
  argv = [tools['pkg_create'], '-l', '-U', '-K', database, '-p', source, '-I', '/usr/pkg',
    '-B', work + '/BUILD_INFO', '-f', list, '-c', work + '/COMMENT', '-d', work + '/DESCR']
  argv += ['-i', hooks['+INSTALL'], '-k', hooks['+DEINSTALL']] if scripts
  run.call('create-' + name, argv + [archive])
  archive
end
name = 'ember-plasma-session-1.0nb1'
archive = create.call(name, staged, files, deps:dependencies, scripts:true)
install = [tools['pkg_add'], '-I', '-C', config, '-K', database, '-p', prefix, '-m', 'NetBSD/aarch64 11.0']
remove = [tools['pkg_delete'], '-D', '-K', database]
reject = run.call('reject-no-providers', install + [archive], expect:false)
raise 'Wrong failure cause for missing providers' unless reject.include?('plasma6-plasma-desktop') && !File.exist?(prefix + '/' + files.first)
archives = {}
(dependencies.to_a + [['qt6-qtbase','6.12.0nb2']]).each do |base, rev|
  pkg = base + '-' + rev
  source = work + '/provider-' + pkg
  FileUtils.mkdir_p(source + '/share/ember-service-fixture')
  payload = 'share/ember-service-fixture/' + base
  File.write(source + '/' + payload, "Synthetic provider #{pkg}; no runtime implementation.\n")
  archives[pkg] = create.call(pkg, source, [payload])
end
dependencies.each do |base, rev|
  selected = base == 'qt6-qtbase' ? '6.12.0nb2' : rev
  pkg = base + '-' + selected
  run.call('seed-' + pkg, install + [archives.fetch(pkg)])
end
reject = run.call('reject-old-qt', install + [archive], expect:false)
raise 'Old Qt did not cause rejection' unless reject.include?('qt6-qtbase>=6.12.0nb3') && !File.exist?(prefix + '/' + files.first)
run.call('upgrade-provider-qt', install + ['-u', archives.fetch('qt6-qtbase-6.12.0nb3')])
2.times do |cycle|
  run.call("install-session-#{cycle}", install + [archive])
  files.each do |file|
    raise 'Installed service differs' unless File.binread(prefix + '/' + file) == File.binread(staged + '/' + file)
    raise 'Unexpected installed file mode' unless File.stat(prefix + '/' + file).mode & 0777 == 0755
  end
  registered = run.call("registered-#{cycle}", [tools['pkg_info'], '-K', database, '-e', name])
  raise 'Registration missing' unless registered.strip == name
  text = File.read(database + '/' + name + '/+CONTENTS')
  raise 'Prefix relocation missing' unless text.include?("@cwd #{prefix}\n")
  dependencies.each { |base, rev| raise 'Dependency missing' unless text.include?("@pkgdep #{base}>=#{rev}\n") }
  run.call("refuse-needed-qt-#{cycle}", remove + ['qt6-qtbase-6.12.0nb3'], expect:false)
  run.call("delete-session-#{cycle}", remove + [name])
  raise 'Service payload survived removal' if files.any? { |file| File.exist?(prefix + '/' + file) }
end
dependencies.each { |base, rev| run.call('delete-provider-' + base, remove + [base + '-' + rev]) }
raise 'Fixture registrations survived removal' if Dir.children(database).any? { |path| File.directory?(database + '/' + path) }

# Native data lifecycle suppresses target hooks. Exercise the actual generated
# hook separately. Relocate only its one managed data record into this fixture.
metadata = work + '/hook-metadata'
hook_prefix = work + '/hook-prefix'
FileUtils.mkdir_p([metadata, hook_prefix + '/etc/rc.d', hook_prefix + '/share/examples/rc.d'])
hooks.each { |file, path| FileUtils.cp(path, metadata + '/' + file) }
env = {'PKG_PREFIX'=>hook_prefix, 'PKG_METADATA_DIR'=>metadata,
  'PKG_REFCOUNT_DBDIR'=>work + '/hook-refcount', 'PKG_RCD_SCRIPTS'=>nil}
run.call('unpack-files-hook', ['/bin/sh', './+INSTALL', name, 'UNPACK', '+FILES'], env:env, cwd:metadata)
path = metadata + '/+FILES'
text = File.read(path)
expected = "# FILE: /etc/rc.d/ember_plasma cr share/examples/rc.d/ember_plasma 0755\n"
raise 'Unexpected managed file records' unless text.lines.grep(/^# FILE: /) == [expected]
File.write(path, text.sub(expected, expected.sub('/etc/', 'etc/')))
sample = hook_prefix + '/share/examples/rc.d/ember_plasma'
target = hook_prefix + '/etc/rc.d/ember_plasma'
FileUtils.cp(staged + '/' + files.last, sample)
invoke = lambda do |label, action, enabled|
  run.call(label, ['/bin/sh', './+FILES', action, metadata], env:env.merge('PKG_RCD_SCRIPTS'=>enabled), cwd:metadata)
end
invoke.call('hook-default-disabled', 'ADD', nil)
raise 'Default installed service' if File.exist?(target)
2.times do |cycle|
  %w[ADD PERMS CHECK-ADD CHECK-PERMS].each { |action| invoke.call("hook-#{cycle}-#{action}", action, 'yes') }
  raise 'Generated hook installed wrong bytes or mode' unless File.binread(target) == File.binread(sample) && File.stat(target).mode & 0777 == 0755
  invoke.call("hook-#{cycle}-repeat-ADD", 'ADD', 'yes')
  File.open(target, 'a') { |file| file.puts '# local change' } if cycle == 1
  invoke.call("hook-#{cycle}-REMOVE", 'REMOVE', 'yes')
  raise 'Unmodified rc.d file survived removal' if cycle.zero? && File.exist?(target)
  raise 'Modified rc.d file was removed' if cycle == 1 && !File.read(target).end_with?("# local change\n")
end
receipt = {status:'PASS', pkgtools_version:version, commands:commands.size,
  staged_files:files.to_h { |file| [file,Digest::SHA256.file(staged + '/' + file).hexdigest] },
  archive_sha256:Digest::SHA256.file(archive).hexdigest,
  native_lifecycle:'Actual pkg_create/pkg_add/pkg_delete with absolute private -K and relocated -p. No -P. Target hooks suppressed with -I/-D.',
  hooks:'Actual generated +FILES. Only its single data record is relocated to private prefix. Default off, explicit install, repeated install, removal and local change preservation.',
  limitations:'Synthetic dependency providers. No target service, desktop or GPU execution. No shared or host package database changes.'}
File.write(work + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
puts "PASS: #{commands.size} actual native package and generated hook commands"
