#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual render-health predicate and caller controls.
require 'digest'
require 'fileutils'
require 'open3'
require 'timeout'
require 'tmpdir'

source = File.expand_path(ARGV.fetch(0, __dir__))
abort 'Run host fixtures as an ordinary user' if Process.uid.zero?
controller = File.read("#{source}/controller.sh")
pins = %w[controller.sh render-health-host.rb].to_h { |name| [name, Digest::SHA256.file("#{source}/#{name}").hexdigest] }
health = controller[/^render_health\(\)\n\{\n.*?^\}\n/m] or abort 'Missing actual render-health predicate'
ready = controller[/^ready\(\)\n\{\n.*?^\}\n/m] or abort 'Missing actual ready function'
root, status = Open3.capture2('git', '-C', source, 'rev-parse', '--show-toplevel')
abort 'Cannot locate Ports' unless status.success?
relative = source.delete_prefix(root.strip + '/')
baseline = '499b4af4f9c50b75ab3a892b791647d846a96fcf'
old, status = Open3.capture2('git', '-C', root.strip, 'show', "#{baseline}:#{relative}/controller.sh")
abort 'Cannot read the pinned baseline' unless status.success?
old_ready = old[/^ready\(\)\n\{\n.*?^\}\n/m] or abort 'Missing baseline ready function'
checks = 0
assert = lambda do |condition, message|
  abort message unless condition
  checks += 1
end
logs = %w[bus.log compositor.log plasma-session.log]
errors = ['MESA: error: Draw call returned Input/output error. Expect corruption.',
          'MESA: error: Failed to submit TFU job: -1']
query = <<~'SH'
  query()
  {
      case "$3" in
          org.kde.KSMServerInterface.isShuttingDown) echo false ;;
          org.kde.KSMServerInterface.currentSession) echo default ;;
          org.kde.ActivityManager.Activities.CurrentActivity|org.kde.ActivityManager.Activities.ListActivities)
              echo 12345678-1234-1234-1234-123456789abc ;;
          org.freedesktop.DBus.Properties.Get) echo org.kde.plasma.desktop ;;
          org.kde.PlasmaShell.evaluateScript) echo 'PASS: default desktop, panel and six applet models on 1280x1024' ;;
          org.kde.Shutdown.logout) : > logout.call ;;
          *) echo 'Unexpected query' >&2; return 99 ;;
      esac
  }
SH
Dir.mktmpdir('plasma-render-health-', ENV.fetch('TMPDIR', '/tmp')) do |temp|
  number = 0
  run = lambda do |body, files = {}, setup = nil|
    number += 1
    directory = "#{temp}/case-#{number}"
    Dir.mkdir(directory, 0o700)
    logs.each { |name| File.write("#{directory}/#{name}", files.fetch(name, '')) }
    File.write("#{directory}/layout.js", 'fixture layout')
    setup&.call(directory)
    script = "#{directory}/test.sh"
    File.write(script, "#!/bin/sh\nset -eu\ncd '#{directory}'\nphase=fixture\n" + health + query + body)
    output = nil
    child_status = nil
    Open3.popen2e('/bin/sh', script, pgroup: true) do |stdin, pipe, wait|
      stdin.close
      begin
        Timeout.timeout(3) { output = pipe.read; child_status = wait.value }
      rescue Timeout::Error
        Process.kill('KILL', -wait.pid) rescue Errno::ESRCH
        abort "Render-health fixture exceeded its bound: #{body}"
      end
    end
    [output, child_status, directory]
  end
  ["", "MESA: warning: optional feature unavailable\n", "[123] qt.rhi.general: OpenGL RENDERER: V3D 7.1\n",
   "MESA: errors are absent\n"].each do |line|
    out, status = run.call("render_health\necho accepted\n", logs.to_h { |name| [name, line] })
    assert.call(status.success? && out == "accepted\n", "Clean/expected warning log failed: #{out}")
  end
  logs.product(errors).each do |name, error|
    content = "expected warning\n#{error}\n#{errors.last}\n"
    out, status, directory = run.call("render_health\necho accepted\n", {name=>content})
    assert.call(!status.success? && !out.include?('accepted'), "Mesa error accepted from #{name}")
    assert.call(out.include?("#{name}:2:#{error}\n") && out.scan(error).length == 1 &&
                out.include?("log=#{name} status=1"), "Missing original error file/row or duplicate report: #{out}")
    assert.call(File.read("#{directory}/#{name}") == content, 'Predicate changed a source log')
  end
  logs.each do |name|
    %i[missing unreadable directory symlink].each do |mode|
      setup = lambda do |directory|
        path = "#{directory}/#{name}"
        File.unlink(path) unless mode == :unreadable
        case mode
        when :unreadable then File.chmod(0, path)
        when :directory then Dir.mkdir(path)
        when :symlink
          File.write("#{directory}/owned-target", '')
          File.symlink('owned-target', path)
        end
      end
      out, status, directory = run.call("render_health\necho accepted\n", {}, setup)
      assert.call(!status.success? && !out.include?('accepted') && out.include?("unreadable regular log=#{name}"),
                  "Unsafe/unavailable #{name} #{mode} did not fail closed: #{out}")
      File.chmod(0o600, "#{directory}/#{name}") if mode == :unreadable
    end
  end
  # Simulate an input read failure after the regular/readable precheck.
  setup = lambda do |directory|
    File.write("#{directory}/awk", "#!/bin/sh\necho 'fixture input read error' >&2\nexit 2\n")
    File.chmod(0o700, "#{directory}/awk")
  end
  out, status = run.call("PATH=\"$PWD:$PATH\"\nexport PATH\nrender_health\necho accepted\n", {}, setup)
  assert.call(!status.success? && out.include?('log=bus.log status=2') && !out.include?('accepted'), 'Input read error was accepted')
  # bus.log also captures controller stderr. The scanner must exit after the
  # first matching row instead of reading its own newly appended diagnostic.
  out, status, directory = run.call("render_health 2>> bus.log\necho accepted\n", {'bus.log'=>errors.first + "\n"})
  feedback = File.read("#{directory}/bus.log")
  assert.call(!status.success? && feedback.lines.length == 3 && feedback.scan(errors.first).length == 2,
              'First-match scanner fed diagnostics back into its own input')

  logs.each do |name|
    [[ready, false], [old_ready, true]].each do |function, is_old|
      out, status = run.call(function + "if ready; then echo accepted; else exit 1; fi\n", {name=>errors.first + "\n"})
      assert.call(status.success? == is_old && out.include?('accepted') == is_old, 'Actual ready caller failed to detect the baseline cause')
    end
  end
  # A ready() call in a shell condition disables implicit errexit in its
  # functions. Removing explicit error returns must reproduce false success.
  mutant = health.gsub('return 1', ':')
  out, status = run.call(mutant + ready + "if ready; then echo accepted; else exit 1; fi\n",
                         {'compositor.log'=>errors.first + "\n"})
  assert.call(status.success? && out.include?('accepted'), 'Explicit-return omission control did not reproduce shell conditional semantics')
  startup = controller[/^phase=startup-readiness\nwhile ! ready.*?^done\n/m] or abort 'Missing actual startup loop'
  liveness = controller[/^count=0\nwhile \[.*?^done\n/m] or abort 'Missing actual liveness loop'
  logout = controller[/^phase=logout\n.*?^stamp logout-requested\n/m] or abort 'Missing actual logout boundary'
  final = controller[/^\[ ! -S .*?^echo 'PASS: full session.*?\n/m] or abort 'Missing actual final acceptance boundary'
  callers = {
    'startup'=>["deadline=0\nwrapper=1\nplasma=1\nready() { return 1; }\nmonotonic_seconds() { echo 1; }\nkill() { return 0; }\nsleep() { echo slept; }\n" + startup, '    render_health || exit 1' + "\n"],
    'liveness'=>[ready + "services=fixture\nprintf '1\\n' > fixture.pid\nprintf '1\\n' > xwayland.pid\nwrapper=1\nplasma=1\nkill() { return 0; }\nsleep() { :; }\nowner() { echo 1; }\n" + liveness, '    render_health || return $?' + "\n"],
    'logout'=>["stamp() { :; }\n" + logout, 'render_health || exit 1' + "\n"],
    'final'=>["XDG_RUNTIME_DIR=$PWD\nWAYLAND_DISPLAY=not-a-socket\nstamp() { :; }\n" + final, 'render_health || exit 1' + "\n"]
  }
  callers.each do |name, (body, call)|
    [false, true].each do |omit|
      abort "Missing unique #{name} causal call" unless body.scan(call).length == 1
      body_under_test = omit ? body.sub(call, '') : body
      out, status, directory = run.call(body_under_test + "echo accepted\n", {'compositor.log'=>errors.last + "\n"})
      if omit && name == 'startup'
        assert.call(!out.include?('FAIL: render health') && out.include?('readiness deadline'), "Omitted startup control did not reach its original failure: #{out.inspect}")
      else
        assert.call(status.success? == omit && out.include?('accepted') == omit, "#{name} omit=#{omit} false acceptance: #{out}")
      end
      unless omit
        assert.call(out.include?('FAIL: render health') && !File.exist?("#{directory}/logout.requested") &&
                    !File.exist?("#{directory}/logout.call"), "#{name} continued past a Mesa error")
      end
    end
    out, status = run.call(body.sub('ready() { return 1; }', 'ready() { return 0; }') + "echo accepted\n")
    assert.call(status.success? && out.include?('accepted'), "Healthy actual #{name} caller failed: #{out}")
  end
  before = controller.index(': > plasma-session.log')
  launch = controller.index('/usr/pkg/bin/startplasma-wayland > plasma-session.log')
  assert.call(before && launch && before < launch, 'Parent did not create the log before background launch')
  # Execute the real post-wait status recording and final acceptance body.
  # A failed first operand in an AND-list does not trigger shell errexit.
  postwait = controller[/^wrapper_status=0\n.*\z/m] or abort 'Missing actual post-wait block'
  old_postwait = old[/^wrapper_status=0\n.*\z/m] or abort 'Missing baseline post-wait block'
  [[postwait, false], [old_postwait, true]].each do |body, is_old|
    [[0, 0], [7, 0], [0, 9], [137, 0], [0, 137]].each do |wrapper_result, plasma_result|
      services = "wrapper=1\nplasma=2\nXDG_RUNTIME_DIR=$PWD\nWAYLAND_DISPLAY=not-a-socket\nstamp() { :; }\n" +
        "wait() { if [ \"$1\" = 1 ]; then return #{wrapper_result}; else return #{plasma_result}; fi; }\n"
      out, status, directory = run.call(services + body)
      expected_success = is_old ? plasma_result.zero? : wrapper_result.zero? && plasma_result.zero?
      assert.call(status.success? == expected_success && out.include?('PASS: full session') == expected_success,
                  "Post-wait false result old=#{is_old} wrapper=#{wrapper_result} plasma=#{plasma_result}: #{out}")
      assert.call(File.read("#{directory}/wrapper.status").strip == wrapper_result.to_s &&
                  File.read("#{directory}/startplasma.status").strip == plasma_result.to_s, 'Original process exit status was lost')
    end
  end
end
assert.call(pins.all? { |name, hash| Digest::SHA256.file("#{source}/#{name}").hexdigest == hash }, 'Inputs changed during the regression')
puts "PASS: #{checks} render-health controls; baseline ready false PASS and four omitted caller controls reproduced; no target runtime executed"
