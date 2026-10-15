#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
require 'fileutils'
require 'open3'
require 'tmpdir'

abort "Usage: #{$PROGRAM_NAME} INSTALL_SCRIPT EXAMPLE_PREFIX" unless ARGV.length == 2
installer, examples = ARGV.map { |path| File.realpath(path) }
def check(condition, message)
  abort "FAIL: #{message}" unless condition
end
def run(env, *command, **options)
  output, status = Open3.capture2e(env, *command, **options)
  puts output unless output.empty?
  check(status.success?, "#{command.join(' ')} exited #{status.exitstatus}")
end
def relative_path?(path)
  path.match?(%r{\A[A-Za-z0-9_+./-]+\z}) &&
    !path.start_with?('/') && !path.split('/').include?('..')
end

source = File.read(installer)
# Run only the real configuration helpers. Other POST-INSTALL hooks execute
# target programs and are outside this host test.
files = source.lines.grep(/^# FILE: /).map { |line| line.split.drop(2) }
dirs = source.lines.grep(/^# DIR: /).map { |line| line.split.drop(2) }
check(!files.empty? && !dirs.empty?, 'Generated configuration records are missing')
files.each do |row|
  check(row.length == 4 && row[1] == 'c' && row[3] == '0644' &&
    relative_path?(row[0]) && relative_path?(row[2]), "Unsafe FILE record: #{row.inspect}")
  path = File.join(examples, row[2])
  check(File.file?(path) && !File.symlink?(path), "Missing regular example: #{row[2]}")
end
dirs.each do |row|
  check(row.length == 2 && row[1] == 'm' && relative_path?(row[0]),
    "Unsafe DIR record: #{row.inspect}")
end
menu = 'etc/xdg/menus/plasma-applications.menu'
check(files.any? { |row| row[0] == menu }, 'Workspace menu record is missing')

Dir.mktmpdir('workspace-config-') do |root|
  prefix = File.join(root, 'prefix')
  metadata = File.join(root, 'pkgdb', 'workspace-config-test')
  FileUtils.mkdir_p([prefix, metadata])
  FileUtils.cp(installer, File.join(metadata, '+INSTALL'))
  files.each do |row|
    destination = File.join(prefix, row[2])
    FileUtils.mkdir_p(File.dirname(destination))
    FileUtils.cp(File.join(examples, row[2]), destination)
  end
  env = {'PKG_PREFIX' => prefix, 'PKG_METADATA_DIR' => metadata,
    'PKG_DBDIR' => File.join(root, 'pkgdb'),
    'PKG_REFCOUNT_DBDIR' => File.join(root, 'refcount'),
    'PKG_CONFIG' => 'yes', 'PKG_CONFIG_PERMS' => 'yes', 'PKG_RCD_SCRIPTS' => 'no'}
  %w[+DIRS +FILES].each do |helper|
    run(env, '/bin/sh', './+INSTALL', 'workspace-config-test', 'UNPACK', helper, chdir: metadata)
    check(File.file?(File.join(metadata, helper)), "#{helper} was not unpacked")
    run(env, '/bin/sh', '-n', "./#{helper}", chdir: metadata)
  end
  action = lambda do |helper, operation|
    run(env, '/bin/sh', "./#{helper}", operation, metadata, chdir: metadata)
  end
  install = lambda do
    action.call('+DIRS', 'ADD')
    action.call('+DIRS', 'PERMS')
    action.call('+FILES', 'ADD')
    action.call('+FILES', 'PERMS')
    # pkgsrc helpers can print an error and return zero. Assert real results.
    files.each do |row|
      file = File.join(prefix, row[0])
      check(File.file?(file), "Installed configuration missing: #{row[0]}")
      check((File.stat(file).mode & 0o777) == 0o644, "Wrong mode: #{row[0]}")
    end
    action.call('+DIRS', 'CHECK-ADD')
    action.call('+FILES', 'CHECK-ADD')
    action.call('+FILES', 'CHECK-PERMS')
  end
  remove = lambda do
    # Match DEINSTALL then POST-DEINSTALL: remove files before directories.
    action.call('+FILES', 'REMOVE')
    action.call('+DIRS', 'REMOVE')
  end
  defaults_match = lambda do
    files.each do |row|
      check(File.binread(File.join(prefix, row[0])) == File.binread(File.join(prefix, row[2])),
        "Installed default differs: #{row[0]}")
    end
  end
  install.call
  defaults_match.call
  remove.call
  check(files.none? { |row| File.exist?(File.join(prefix, row[0])) }, 'Unedited configuration survived removal')
  check(!File.exist?(File.join(prefix, 'etc/xdg/menus')), 'Empty menu directory survived removal')
  install.call
  defaults_match.call
  menu_path = File.join(prefix, menu)
  edited = File.binread(menu_path) + "\n<!-- locally edited configuration -->\n"
  File.binwrite(menu_path, edited)
  remove.call
  check(File.binread(menu_path) == edited, 'Removal changed the edited menu')
  check(files.reject { |row| row[0] == menu }.none? { |row| File.exist?(File.join(prefix, row[0])) },
    'Removal retained another unedited configuration')
  install.call
  check(File.binread(menu_path) == edited, 'Reinstallation changed the edited menu')
  remove.call
  check(File.binread(menu_path) == edited, 'Repeated removal changed the edited menu')
end
puts 'PASS: generated configuration helpers install, remove, reinstall and preserve edited menu'
