#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Causal fixtures, not a Plasma runtime test.
require 'fileutils'
require 'open3'
require 'rbconfig'
require 'tmpdir'

source = File.expand_path(__dir__)
checks = 0
perl = ENV.fetch('PERL', 'perl')
if RUBY_PLATFORM.include?('darwin') && RbConfig.ruby.start_with?('/System/')
  abort 'Use native Ruby and Perl on macOS. SIP hides system interpreter environments from ps.'
end
run = lambda do |expected, *args|
  out, status = Open3.capture2e(*args)
  unless status.exitstatus == expected
    warn "Command: #{args.inspect}"
    args.grep(String).select { |a| File.directory?(a) }.each do |directory|
      Dir.glob("#{directory}/*.{log,status}").each { |f| warn "#{File.basename(f)}:\n#{File.read(f)}" }
    end
    abort "Expected #{expected}, got #{status.exitstatus}: #{out}"
  end
  checks += 1
end
Dir.mktmpdir('plasma-session-host-', '/tmp') do |temp|
  run.call(2, '/bin/sh', "#{source}/run.sh")
  run.call(2, '/bin/sh', "#{source}/run.sh", 'relative')
  run.call(2, '/bin/sh', "#{source}/run.sh", temp)
  File.symlink("#{temp}/absent", "#{temp}/link")
  run.call(2, '/bin/sh', "#{source}/run.sh", "#{temp}/link")
  foreign = Process.spawn(RbConfig.ruby, '-e', 'sleep 90')
  begin
    %w[normal failure deadline detached force ps_failure ps_timeout].each do |mode|
      work = "#{temp}/#{mode}"
      Dir.mkdir(work)
      fixture = <<~RUBY
        require 'rbconfig'
        mode = #{mode.inspect}
        if %w[detached force].include?(mode)
          Process.spawn(RbConfig.ruby, '-e', <<~'CHILD', out: File::NULL, err: File::NULL)
            Process.setsid
            trap('TERM') { #{mode == 'force' ? 'nil' : "File.write('#{work}/terminated', 'yes'); exit 0"} }
            File.write('#{work}/child.pid', Process.pid.to_s)
            loop { sleep 0.1 }
          CHILD
          100.times { break if File.file?('#{work}/child.pid'); sleep 0.01 }
          abort 'Child did not start' unless File.file?('#{work}/child.pid')
        end
        if %w[ps_failure ps_timeout].include?(mode)
          trap('TERM') { File.write('#{work}/terminated', 'yes'); exit 0 }
          File.write('#{work}/started', Process.pid.to_s)
          sleep 90
        end
        sleep 90 if mode == 'deadline'
        exit(mode == 'failure' ? 7 : 0)
      RUBY
      File.write("#{work}/fixture.rb", fixture)
      expected = {'normal'=>0, 'failure'=>7, 'deadline'=>124, 'detached'=>0,
                  'force'=>1, 'ps_failure'=>1, 'ps_timeout'=>1}.fetch(mode)
      guard = "#{source}/guard.pl"
      if %w[ps_failure ps_timeout].include?(mode)
        File.write("#{work}/ps", "#!#{perl}\nif (-f '#{work}/started') { " +
          (mode == 'ps_failure' ? 'exit 2' : "exec '/bin/sleep', '60'") + " }\nexec '/bin/ps', @ARGV;\n")
        File.chmod(0o700, "#{work}/ps")
        File.write("#{work}/guard.pl", File.read(guard).sub("'/bin/ps'", "'#{work}/ps'"))
        guard = "#{work}/guard.pl"
      end
      began = Process.clock_gettime(Process::CLOCK_MONOTONIC)
      run.call(expected, perl, guard, work, mode == 'deadline' ? '2' : '15', '--', RbConfig.ruby, "#{work}/fixture.rb")
      if %w[ps_failure ps_timeout].include?(mode)
        abort 'Inventory failure stranded the known child' unless File.file?("#{work}/terminated")
        abort 'Inventory failure was not bounded' if Process.clock_gettime(Process::CLOCK_MONOTONIC) - began > 10
        checks += 1
      end
      abort 'Foreign process was stopped' unless Process.kill(0, foreign) == 1
      checks += 1
      abort 'Detached child did not receive TERM' if mode == 'detached' && !File.file?("#{work}/terminated")
      if File.file?("#{work}/child.pid")
        state, = Open3.capture2('/bin/ps', '-p', File.read("#{work}/child.pid").strip, '-o', 'state=')
        abort 'A detached fixture process is still running' unless state.strip.empty? || state.strip.start_with?('Z')
      end
      abort 'Guard did not record its status' unless File.read("#{work}/guard.status").to_i == expected
    end
  ensure
    Process.kill('TERM', foreign) rescue Errno::ESRCH
    Process.wait(foreign) rescue Errno::ECHILD
    Dir.glob("#{temp}/*/child.pid").each do |file|
      pid = File.read(file).to_i
      command, = Open3.capture2('/bin/ps', '-p', pid.to_s, '-o', 'command=')
      # A fixture can fail before cleanup. Do not signal a reused foreign PID.
      Process.kill('KILL', pid) if command.include?(temp)
    rescue Errno::ESRCH
      nil
    end
  end
  %w[ready wrong_session old_method wrong_property].each do |mode|
    work = "#{temp}/#{mode}"
    %w[runtime tmp].each { |dir| FileUtils.mkdir_p("#{work}/#{dir}", mode: 0o700) }
    FileUtils.cp(["#{source}/../plasma-desktop/layout.js", "#{source}/../plasma-desktop/check-results.sh"], work)
    File.write("#{work}/bus.log", '')
    File.write("#{work}/runtime/xauth_fixture", 'fixture')
    File.chmod(0o600, "#{work}/runtime/xauth_fixture")
    File.write("#{work}/timeout", "#!/bin/sh\nshift 3\nexec \"$@\"\n")
    File.write("#{work}/sleep", "#!/bin/sh\nexec /bin/sleep 0.02\n")
    File.write("#{work}/date", <<~RUBY)
      #!#{RbConfig.ruby}
      n = File.file?('clock') ? File.read('clock').to_i : 0
      File.write('clock', (n + 1).to_s)
      puts(#{mode != 'ready'} && n > 0 && File.file?('readiness-error.log') ? 200 : 0)
    RUBY
    File.write("#{work}/wrapper", <<~RUBY)
      #!#{RbConfig.ruby}
      require 'socket'
      File.write('wrapper-arguments', ARGV.join("\n"))
      socket = UNIXServer.new(ENV.fetch('XDG_RUNTIME_DIR') + '/wayland-0')
      File.write('display-env', "wayland-0\n:77\n" + ENV.fetch('XDG_RUNTIME_DIR') + "/xauth_fixture\n")
      sleep 0.01 until File.file?('logout.request')
      socket.close
      File.unlink(ENV.fetch('XDG_RUNTIME_DIR') + '/wayland-0')
    RUBY
    File.write("#{work}/startplasma", <<~RUBY)
      #!#{RbConfig.ruby}
      abort 'Unexpected arguments' unless ARGV.empty?
      STDOUT.sync = true
      puts '[' + File.read('wrapper.pid').strip + '] qt.rhi.general: OpenGL VENDOR: Broadcom RENDERER: V3D 7.1 VERSION: 3.1'
      sleep 0.01 until File.file?('logout.request')
    RUBY
    File.write("#{work}/qdbus", <<~RUBY)
      #!#{RbConfig.ruby}
      method = ARGV[2]
      case method
      when 'org.freedesktop.DBus.GetConnectionUnixProcessID'
        puts File.read('wrapper.pid')
      when 'org.kde.KSMServerInterface.isShuttingDown'
        puts #{mode == 'wrong_session' ? 'true' : 'false'}.to_s
      when 'org.kde.KSMServerInterface.currentSession'
        puts 'default'
      when 'org.kde.ActivityManager.Activities.CurrentActivity', 'org.kde.ActivityManager.Activities.ListActivities'
        puts '12345678-1234-1234-1234-123456789abc'
      when 'org.freedesktop.DBus.Properties.Get'
        expected = ['org.kde.plasmashell', '/PlasmaShell', 'org.freedesktop.DBus.Properties.Get',
                    'org.kde.PlasmaShell', 'shell']
        abort 'Unexpected property query: ' + ARGV.inspect unless ARGV == expected
        puts 'org.kde.plasma.desktop'
      when 'org.kde.PlasmaShell.evaluateScript'
        puts 'PASS: default desktop, panel and six applet models on 1280x1024'
      when 'org.kde.KWin.supportInformation'
        puts "Compositing is active\nCompositing Type: OpenGL ES\nOpenGL renderer string: V3D 7.1\n"
      when 'org.kde.Shutdown.logout'
        File.write('logout.request', 'yes')
      else
        abort 'Unexpected D-Bus method: ' + ARGV.inspect
      end
    RUBY
    File.write("#{work}/ps", <<~SH)
      #!/bin/sh
      pid=$(cat wrapper.pid)
      echo "$pid $pid /usr/pkg/bin/Xwayland"
    SH
    %w[timeout sleep date wrapper startplasma qdbus ps].each { |f| File.chmod(0o700, "#{work}/#{f}") }
    controller = File.read("#{source}/controller.sh")
      .gsub('/usr/pkg/bin/perl', perl).gsub('/usr/bin/timeout', "#{work}/timeout")
      .gsub('/usr/pkg/bin/kwin_wayland_wrapper', "#{work}/wrapper")
      .gsub('/usr/pkg/bin/startplasma-wayland', "#{work}/startplasma")
      .gsub('/usr/pkg/qt6/bin/qdbus', "#{work}/qdbus")
    # Keep the negative readiness fixtures fast. Civil query timestamps no
    # longer control the controller's startup deadline.
    clock = /^monotonic_seconds\(\)\n\{\n.*?^\}\n/m
    abort 'Missing monotonic fixture boundary' unless controller.match?(clock)
    controller = controller.sub(clock, "monotonic_seconds()\n{\n    if [ -f readiness-error.log ] && [ '#{mode}' != ready ]; then echo 200; else echo 0; fi\n}\n")
    if mode == 'old_method'
      original = "org.freedesktop.DBus.Properties.Get \\\n        org.kde.PlasmaShell shell"
      abort 'Missing property query mutation point' unless controller.include?(original)
      controller = controller.sub(original, 'org.kde.PlasmaShell.shell')
    elsif mode == 'wrong_property'
      original = 'org.kde.PlasmaShell shell > shell.txt'
      abort 'Missing property name mutation point' unless controller.include?(original)
      controller = controller.sub(original, 'org.kde.PlasmaShell missing > shell.txt')
    end
    File.write("#{work}/controller.sh", controller)
    environment = {'EMBER_PLASMA_OUTPUT'=>work, 'XDG_RUNTIME_DIR'=>"#{work}/runtime",
                   'TMPDIR'=>"#{work}/tmp", 'PATH'=>"#{work}:#{ENV.fetch('PATH')}"}
    run.call(mode == 'ready' ? 0 : 1, environment, perl, "#{source}/guard.pl", work, '30', '--', '/bin/sh', "#{work}/controller.sh")
    if mode == 'ready'
      abort 'Logout API was not used' unless File.file?("#{work}/logout.requested")
      abort 'startplasma exit status is missing' unless File.read("#{work}/startplasma.status").strip == '0'
      abort 'Unexpected exit-with-session coupling' if File.read("#{work}/wrapper-arguments").include?('exit-with-session')
      phases = File.readlines("#{work}/phases.tsv", chomp: true).map { |line| line.split("\t", -1) }
      expected_phases = %w[controller-start compositor-ready session-ready logout-requested session-stopped]
      abort 'Missing or unordered monotonic phases' unless phases.map(&:first) == expected_phases && phases.all? { |fields| fields.length == 2 }
      times = phases.map { |fields| Float(fields.last) }
      abort 'Invalid monotonic times' unless times.all? { |time| time.finite? && time.positive? } && times.each_cons(2).all? { |a, b| b >= a }
      readiness = Float(File.read("#{work}/readiness-seconds.txt"))
      abort 'Readiness interval does not match the recorded phases' unless readiness.finite? && readiness.positive? && (readiness - (times[2] - times[0])).abs <= 0.000002
      checks += 4
    else
      abort 'A failed session requested logout acceptance' if File.file?("#{work}/logout.requested")
      if mode == 'old_method'
        expected = 'Unexpected D-Bus method: ["org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.shell"]'
        abort 'Old method did not fail at the protocol boundary' unless File.read("#{work}/readiness-error.log").include?(expected)
        checks += 1
      elsif mode == 'wrong_property'
        expected = 'Unexpected property query: ["org.kde.plasmashell", "/PlasmaShell", "org.freedesktop.DBus.Properties.Get", "org.kde.PlasmaShell", "missing"]'
        abort 'Wrong property did not fail at the protocol boundary' unless File.read("#{work}/readiness-error.log").include?(expected)
        checks += 1
      end
      checks += 1
    end
  end
end
puts "PASS: #{checks} host controls; no Plasma or target runtime executed"
