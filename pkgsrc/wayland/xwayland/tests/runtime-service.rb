#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual service with controlled credentials.
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'tmpdir'

recipe = File.expand_path('..', __dir__)
service_source = File.read("#{recipe}/files/x11_runtime.sh")
runner_source = File.read(File.expand_path('../../../../probes/plasma-mobile/toolkit/tests/plasma-session/run.sh', __dir__))
checks = 0
Dir.mktmpdir('xwayland-runtime-', ENV.fetch('TMPDIR', '/tmp')) do |work|
  root = "#{work}/root"
  commands = "#{work}/commands"
  FileUtils.mkdir_p(commands)
  state_path = "#{work}/state.json"
  state = nil
  save = -> { File.write(state_path, JSON.generate(state)) }
  reset = lambda do
    FileUtils.rm_rf(root)
    FileUtils.mkdir_p("#{root}/tmp")
    File.chmod(0o1777, "#{root}/tmp")
    state = {'uid'=>0, 'owners'=>{}, 'calls'=>[], 'fail'=>nil}
    save.call
  end
  helper = <<~'HELPER'
    require 'json'
    state_path = ENV.fetch('XR_STATE')
    state = JSON.parse(File.read(state_path))
    name = File.basename($PROGRAM_NAME)
    state['calls'] << [name, *ARGV]
    File.write(state_path, JSON.generate(state))
    exit 1 if state['fail'] == name
    case name
    when 'id'
      abort 'bad id arguments' unless ARGV == ['-u']
      puts state.fetch('uid')
    when 'stat'
      abort 'bad stat arguments' unless ARGV.length == 3 && ARGV[0] == '-f' && %w[%u:%g:%p %u:%g:%Lp].include?(ARGV[1])
      # Keep the real BSD stat mode formatter. Only credentials are controlled.
      # %Lp strips the sticky bit; a Ruby mode mask hid that target defect.
      result = IO.popen(['/usr/bin/stat', *ARGV], &:read)
      exit 1 unless $?.success?
      fields = result.strip.split(':')
      abort 'BSD stat with numeric mode output is required' unless fields.length == 3 && fields[2].match?(/\A[0-7]+\z/)
      uid, gid = state.fetch('owners').fetch(ARGV[2], [0, 0])
      puts "#{uid}:#{gid}:#{fields[2]}"
    when 'mkdir'
      abort 'bad mkdir arguments' unless ARGV.length == 3 && ARGV[0,2] == ['-m', '1777']
      exit(system('/bin/mkdir', *ARGV) ? 0 : 1)
    when 'chown'
      abort 'bad chown arguments' unless ARGV.length == 3 && ARGV[0,2] == ['-h', 'root:wheel']
      abort 'chown on a link or non-directory' if File.symlink?(ARGV[2]) || !File.directory?(ARGV[2])
      state['owners'][ARGV[2]] = [0, 0]
      File.write(state_path, JSON.generate(state))
    else
      abort "Unexpected command: #{name}"
    end
  HELPER
  %w[id stat mkdir chown].each do |name|
    File.write("#{commands}/#{name}", "#!#{RbConfig.ruby}\n" + helper)
    File.chmod(0o700, "#{commands}/#{name}")
  end
  File.write("#{work}/rc.subr", <<~'SH')
    load_rc_config() { :; }
    warn() { echo "$*" >&2; }
    run_rc_command() {
      case "$1" in
      start) "$start_cmd" ;;
      stop) "$stop_cmd" ;;
      *) return 2 ;;
      esac
    }
  SH
  # Rewrite only fixture paths and the explicit kernel/user identity boundary.
  # The production directory checks and lifecycle functions run unchanged.
  prepare = lambda do |source, path, service|
    text = source.gsub('/tmp/.X11-unix', "#{root}/tmp/.X11-unix")
                 .gsub('/tmp/.ICE-unix', "#{root}/tmp/.ICE-unix")
    text = text.sub('x11_runtime_check /tmp ', "x11_runtime_check #{root}/tmp ") if service
    text = text.sub('for directory in /tmp ', "for directory in #{root}/tmp ") unless service
    text = text.sub('@RCD_SCRIPTS_SHELL@', '/bin/sh').sub('/etc/rc.subr', "#{work}/rc.subr")
    {'/usr/bin/id'=>'id', '/usr/bin/stat'=>'stat', '/bin/mkdir'=>'mkdir', '/sbin/chown'=>'chown'}.each do |old, name|
      text = text.gsub(old, "#{commands}/#{name}")
    end
    File.write(path, text)
  end
  service = "#{work}/service.sh"
  prepare.call(service_source, service, true)
  invoke = lambda do |expected, path, *args|
    output, status = Open3.capture2e({'XR_STATE'=>state_path, 'PATH'=>"#{commands}:#{ENV.fetch('PATH')}"}, '/bin/sh', path, *args)
    abort "Expected #{expected}, got #{status.exitstatus}: #{output}" unless status.exitstatus == expected
    state = JSON.parse(File.read(state_path))
    checks += 1
    output
  end
  reset.call
  invoke.call(0, service, 'start')
  %w[.X11-unix .ICE-unix].each do |name|
    dir = "#{root}/tmp/#{name}"
    abort 'wrong permissions or ownership' unless File.stat(dir).mode & 0o7777 == 0o1777 && state['owners'][dir] == [0, 0]
  end
  marker = "#{root}/tmp/.X11-unix/existing-socket-marker"
  File.write(marker, 'retain')
  creates = state['calls'].count { |call| call[0] == 'mkdir' }
  invoke.call(0, service, 'start')
  invoke.call(0, service, 'stop')
  abort 'restart or stop changed a live directory' unless File.read(marker) == 'retain' && state['calls'].count { |call| call[0] == 'mkdir' } == creates
  # Model cleartmp, then execute the same boot service again.
  FileUtils.rm_rf(["#{root}/tmp/.X11-unix", "#{root}/tmp/.ICE-unix"])
  invoke.call(0, service, 'stop')
  abort 'stop created directories' if File.exist?("#{root}/tmp/.X11-unix")
  invoke.call(0, service, 'start')
  abort 'boot did not recreate both directories' unless File.directory?("#{root}/tmp/.ICE-unix")

  %w[symlink dangling file owner group mode parent_mode parent_owner parent_symlink nonroot mkdir chown stat].each do |failure|
    reset.call
    path = "#{root}/tmp/.X11-unix"
    case failure
    when 'symlink', 'dangling'
      FileUtils.mkdir_p("#{root}/untouched") if failure == 'symlink'
      File.symlink("#{root}/untouched", path)
    when 'file'
      File.write(path, 'unchanged')
    when 'owner', 'group', 'mode'
      Dir.mkdir(path, 0o1777)
      File.chmod(failure == 'mode' ? 0o755 : 0o1777, path)
      state['owners'][path] = failure == 'owner' ? [1000,0] : failure == 'group' ? [0,1000] : [0,0]
    when 'parent_mode'
      File.chmod(0o777, "#{root}/tmp")
    when 'parent_owner'
      state['owners']["#{root}/tmp"] = [1000,0]
    when 'parent_symlink'
      File.rename("#{root}/tmp", "#{root}/other-tmp")
      File.symlink("#{root}/other-tmp", "#{root}/tmp")
    when 'nonroot'
      state['uid'] = 1000
    else
      state['fail'] = failure
    end
    save.call
    invoke.call(1, service, 'start')
    abort "failure continued: #{failure}" if File.exist?("#{root}/tmp/.ICE-unix")
    abort 'symlink followed' if %w[symlink dangling].include?(failure) && state['calls'].any? { |c| c[0] == 'chown' }
    abort 'foreign directory was changed' if %w[owner group mode].include?(failure) && state['calls'].any? { |c| %w[chown mkdir].include?(c[0]) }
  end
  # The actual full-session runner must fail before launching any processes.
  reset.call
  state['uid'] = 1000
  save.call
  runner = "#{work}/run.sh"
  prepare.call(runner_source, runner, false)
  output = invoke.call(2, runner, "/tmp/xwayland-preflight-#{Process.pid}")
  abort 'missing service diagnostic' unless output.include?('Missing or unsafe X11 runtime directory:') && output.include?('/etc/rc.d/x11_runtime start')

  # Check the actual preflight block separately so an unsafe parent cannot
  # pass merely because both child directories have root ownership.
  start = runner_source.index('for directory in /tmp /tmp/.X11-unix /tmp/.ICE-unix; do') or abort 'missing parent preflight'
  finish = runner_source.index("\ndone", start) or abort 'missing preflight end'
  preflight = runner_source[start..finish + 4]
  prepare.call("#!/bin/sh\nset -eu\n#{preflight}\n", "#{work}/preflight.sh", false)
  reset.call
  invoke.call(0, service, 'start')
  invoke.call(0, "#{work}/preflight.sh")
  # Reproduce the nb2 formatter failure with real BSD stat, not a mode mock.
  old_service = service_source.gsub("'%u:%g:%p'", "'%u:%g:%Lp'").gsub("'0:0:41777'", "'0:0:1777'")
  old_preflight = preflight.gsub("'%u:%g:%p'", "'%u:%g:%Lp'").gsub("'0:0:41777'", "'0:0:1777'")
  abort 'missing mode mutation points' if old_service == service_source || old_preflight == preflight
  prepare.call(old_service, "#{work}/old-stat-service.sh", true)
  prepare.call("#!/bin/sh\nset -eu\n#{old_preflight}\n", "#{work}/old-stat-preflight.sh", false)
  output = invoke.call(1, "#{work}/old-stat-service.sh", 'start')
  abort 'wrong old-stat service failure' unless output.include?("#{root}/tmp must have root:wheel ownership and mode 1777.")
  output = invoke.call(2, "#{work}/old-stat-preflight.sh")
  abort 'wrong old-stat preflight failure' unless output.include?("Missing or unsafe X11 runtime directory: #{root}/tmp")
  %w[parent x11 ice].each do |target|
    failures = target == 'parent' ? %w[owner group mode symlink] : %w[owner group mode symlink dangling file]
    failures.each do |failure|
      reset.call
      %w[.X11-unix .ICE-unix].each do |name|
        path = "#{root}/tmp/#{name}"
        Dir.mkdir(path)
        File.chmod(0o1777, path)
      end
      path = target == 'parent' ? "#{root}/tmp" : "#{root}/tmp/#{target == 'x11' ? '.X11-unix' : '.ICE-unix'}"
      case failure
      when 'owner' then state['owners'][path] = [1000, 0]
      when 'group' then state['owners'][path] = [0, 1000]
      when 'mode' then File.chmod(target == 'parent' ? 0o777 : 0o755, path)
      when 'symlink'
        File.rename(path, "#{root}/displaced")
        File.symlink("#{root}/displaced", path)
      when 'dangling'
        Dir.rmdir(path)
        File.symlink("#{root}/absent", path)
      when 'file'
        Dir.rmdir(path)
        File.write(path, 'unchanged')
      end
      save.call
      output = invoke.call(2, "#{work}/preflight.sh")
      abort "wrong rejected path: #{target}/#{failure}" unless output.include?("Missing or unsafe X11 runtime directory: #{path}")
      abort 'preflight mutated a directory' if state['calls'].any? { |c| %w[chown mkdir].include?(c[0]) }
      next unless target == 'parent' && failure == 'mode'
      # This is the exact previous loop from commit 27ca2e9: no /tmp entry.
      baseline = preflight.sub('for directory in /tmp ', 'for directory in ')
      prepare.call("#!/bin/sh\nset -eu\n#{baseline}\n", "#{work}/preflight-baseline.sh", false)
      invoke.call(0, "#{work}/preflight-baseline.sh")
    end
  end

  # A missing create step reproduces the original boot-lifecycle failure.
  reset.call
  mutant = service_source.sub(%r{\t\t/bin/mkdir -m 1777 "\$directory" \|\| return 1}, '\t\t:'.gsub('\\t', "\t"))
  abort 'missing creation mutation point' if mutant == service_source
  prepare.call(mutant, "#{work}/mutant.sh", true)
  invoke.call(1, "#{work}/mutant.sh", 'start')
  abort 'mutant unexpectedly prepared sockets' if File.directory?("#{root}/tmp/.ICE-unix")
end
puts "PASS: #{checks} actual Xwayland rc.d/preflight controls (controlled credentials; no target boot)"
