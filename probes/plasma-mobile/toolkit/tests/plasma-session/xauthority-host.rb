#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual controller checks with real BSD stat.
require 'fileutils'
require 'open3'
require 'rbconfig'
require 'socket'
require 'tmpdir'

source = File.read(File.join(__dir__, 'controller.sh'))
first = source.index('# KWin 6.8 creates xauth_XXXXXX') or abort 'Missing Xauthority contract'
last = source.index('export WAYLAND_DISPLAY DISPLAY XAUTHORITY', first) or abort 'Missing contract end'
contract = source[first...last]
baseline, status = Open3.capture2('git', '-C', __dir__, 'show',
  '2fe393d675d29ca8c2261c4a2eda1a98e0526498:probes/plasma-mobile/toolkit/tests/plasma-session/controller.sh')
abort 'Cannot read pinned baseline' unless status.success?
first = baseline.index('case "$XAUTHORITY"') or abort 'Missing baseline start'
last = baseline.index('export WAYLAND_DISPLAY DISPLAY XAUTHORITY', first) or abort 'Missing baseline end'
baseline = baseline[first...last]
checks = 0
Dir.mktmpdir('plasma-xauth-', '/tmp') do |temp|
  helper = File.join(temp, 'stat')
  File.write(helper, <<~RUBY)
    #!#{RbConfig.ruby}
    result = IO.popen(['/usr/bin/stat', *ARGV], &:read)
    exit 1 unless $?.success?
    # Keep actual mode/type formatting. Model a foreign UID without chown.
    if ARGV.last == ENV['XAUTH_FOREIGN_OWNER']
      result = result.sub(/\\A[0-9]+:/, (Process.uid + 1).to_s + ':')
    end
    print result
  RUBY
  File.chmod(0o700, helper)
  cases = %w[ready arbitrary_name outside prefix_collision traversal nested_file nested_symlink
             file_symlink file_dangling file_directory file_missing file_mode file_sticky file_owner
             runtime_mode runtime_owner runtime_symlink runtime_outside parent_mode parent_owner parent_symlink
             empty_name dot_name parent_name old_runner]
  cases.each do |mode|
    work = File.join(temp, mode)
    FileUtils.mkdir_p("#{work}/runtime", mode: 0o700)
    FileUtils.mkdir_p("#{work}/tmp", mode: 0o700)
    runtime = "#{work}/runtime"
    authority = "#{runtime}/xauth_fixture"
    File.write(authority, 'fixture, not a real cookie')
    File.chmod(0o600, authority)
    socket = UNIXServer.new("#{runtime}/wayland-0")
    foreign = nil
    expected_error = nil
    case mode
    when 'arbitrary_name'
      changed = "#{runtime}/ordinary-name.with.dots"
      File.rename(authority, changed)
      authority = changed
    when 'outside', 'prefix_collision'
      directory = mode == 'outside' ? "#{work}/tmp" : "#{work}/runtime-other"
      FileUtils.mkdir_p(directory, mode: 0o700)
      changed = "#{directory}/xauth_fixture"
      File.rename(authority, changed)
      authority = changed
      expected_error = 'outside the private runtime directory'
    when 'traversal'
      File.rename(authority, "#{work}/tmp/xauth_fixture")
      authority = "#{runtime}/../tmp/xauth_fixture"
      expected_error = 'not a direct runtime file'
    when 'nested_file', 'nested_symlink'
      FileUtils.mkdir_p("#{work}/nested", mode: 0o700)
      if mode == 'nested_symlink'
        File.symlink("#{work}/nested", "#{runtime}/child")
      else
        Dir.mkdir("#{runtime}/child", 0o700)
      end
      changed = "#{runtime}/child/xauth_fixture"
      File.rename(authority, changed)
      authority = changed
      expected_error = 'not a direct runtime file'
    when 'file_symlink', 'file_dangling'
      File.rename(authority, "#{work}/saved-authority")
      File.symlink(mode == 'file_symlink' ? "#{work}/saved-authority" : "#{work}/absent", authority)
      expected_error = 'unsafe private Xauthority file'
    when 'file_directory', 'file_missing'
      File.unlink(authority)
      Dir.mkdir(authority, 0o700) if mode == 'file_directory'
      expected_error = 'unsafe private Xauthority file'
    when 'file_mode', 'file_sticky'
      File.chmod(mode == 'file_mode' ? 0o644 : 0o1600, authority)
      expected_error = 'unsafe private Xauthority file'
    when 'file_owner'
      foreign = authority
      expected_error = 'unsafe private Xauthority file'
    when 'runtime_mode', 'parent_mode'
      File.chmod(0o755, mode == 'runtime_mode' ? runtime : work)
      expected_error = 'unsafe private Xauthority directory'
    when 'runtime_owner', 'parent_owner'
      foreign = mode == 'runtime_owner' ? runtime : work
      expected_error = 'unsafe private Xauthority directory'
    when 'runtime_symlink', 'parent_symlink'
      path = mode == 'runtime_symlink' ? runtime : work
      File.rename(path, "#{path}-saved")
      File.symlink("#{path}-saved", path)
      expected_error = 'unsafe private Xauthority directory'
    when 'runtime_outside'
      runtime = "#{work}/tmp"
      expected_error = 'does not belong to this session'
    when 'empty_name', 'dot_name', 'parent_name'
      authority = runtime + '/' + {'empty_name'=>'', 'dot_name'=>'.', 'parent_name'=>'..'}.fetch(mode)
      expected_error = 'not a direct runtime file'
    when 'old_runner'
      expected_error = 'outside the private temporary directory'
    end
    test = mode == 'old_runner' ? baseline : contract
    script = "#{temp}/check.sh"
    File.write(script, "#!/bin/sh\nset -eu\n" + test.gsub('/usr/bin/stat', helper))
    env = {'EMBER_PLASMA_OUTPUT'=>work, 'XDG_RUNTIME_DIR'=>runtime,
           'TMPDIR'=>"#{work}/tmp", 'XAUTHORITY'=>authority, 'WAYLAND_DISPLAY'=>'wayland-0',
           'XAUTH_FOREIGN_OWNER'=>foreign}
    output, status = Open3.capture2e(env, '/bin/sh', script)
    expected = expected_error ? 1 : 0
    abort "#{mode}: expected #{expected}, got #{status.inspect}: #{output}" unless status.exitstatus == expected
    abort "#{mode}: wrong failure: #{output}" if expected_error && !output.include?(expected_error)
    checks += 1
  ensure
    socket&.close
  end
end
puts "PASS: #{checks} actual Xauthority controls with BSD stat; no KWin or target session"
