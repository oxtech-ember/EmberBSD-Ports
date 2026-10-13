#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Host checks; these do not run Plasma.
require 'fileutils'
require 'open3'
require 'rbconfig'
require 'socket'
require 'tmpdir'

source = File.expand_path(__dir__)
checks = 0
run = lambda do |expected, *command|
  output, status = Open3.capture2e(*command)
  passed = expected == :ok ? status.success? : !status.success?
  abort "Unexpected result #{status.exitstatus}: #{command.inspect}\n#{output}" unless passed
  checks += 1
  output
end
Dir.mktmpdir('ember-plasma-host-', '/tmp') do |temp|
  # The runner must reject invalid paths before it creates output or runs tools.
  run.call(:fail, '/bin/sh', "#{source}/run.sh")
  run.call(:fail, '/bin/sh', "#{source}/run.sh", 'relative-output')
  run.call(:fail, '/bin/sh', "#{source}/run.sh", temp)
  File.symlink("#{temp}/absent", "#{temp}/dangling")
  run.call(:fail, '/bin/sh', "#{source}/run.sh", "#{temp}/dangling")
  checker = "#{source}/check-results.sh"
  support = "Compositing is active\nCompositing Type: OpenGL\nOpenGL renderer string: V3D 7.1.10.2\n"
  File.write("#{temp}/support", support)
  run.call(:ok, '/bin/sh', checker, 'support', "#{temp}/support")
  ['Compositing is active', 'Compositing Type: OpenGL', 'V3D '].each do |required|
    File.write("#{temp}/support", support.sub(required, 'invalid'))
    run.call(:fail, '/bin/sh', checker, 'support', "#{temp}/support")
  end
  renderer = 'qt.rhi.general: OpenGL VENDOR: Broadcom RENDERER: V3D 7.1.10.2 VERSION: 3.1'
  File.write("#{temp}/renderer", renderer)
  run.call(:ok, '/bin/sh', checker, 'renderer', "#{temp}/renderer")
  File.write("#{temp}/renderer", renderer.sub('V3D', 'llvmpipe'))
  run.call(:fail, '/bin/sh', checker, 'renderer', "#{temp}/renderer")
  ['module org.kde.missing is not installed',
   'error when loading applet org.kde.plasma.kickoff'].each do |diagnostic|
    File.write("#{temp}/renderer", "#{renderer}\n#{diagnostic}\n")
    run.call(:fail, '/bin/sh', checker, 'renderer', "#{temp}/renderer")
  end
  png_header = ['89504e470d0a1a0a0000000d494844520000014000000100'].pack('H*')
  File.binwrite("#{temp}/image", png_header)
  run.call(:ok, '/bin/sh', checker, 'png', "#{temp}/image")
  [png_header[0...-1], png_header.sub("IHDR", "IDAT")].each do |bad_header|
    File.binwrite("#{temp}/image", bad_header)
    run.call(:fail, '/bin/sh', checker, 'png', "#{temp}/image")
  end
  # Execute the actual assertion script with a bounded model of its KDE API.
  node_test = <<~'JS'
    const fs = require('fs');
    const vm = require('vm');
    const script = fs.readFileSync(process.argv[2], 'utf8');
    function context() {
      return {
        screenCount: 1, screenGeometry: () => ({width: 1280, height: 1024}),
        desktops: () => [{screen: 0, type: 'org.kde.plasma.folder'}],
        panels: () => [{screen: 0, type: 'org.kde.panel', widgets: () =>
          ['kickoff', 'pager', 'icontasks', 'systemtray', 'digitalclock', 'showdesktop']
            .map(name => ({type: 'org.kde.plasma.' + name}))}],
        print: text => { if (!text.startsWith('PASS:')) throw Error('Wrong evidence'); }
      };
    }
    vm.runInNewContext(script, context(), {timeout: 1000});
    const changes = [
      ctx => ctx.screenCount = 0,
      ctx => ctx.screenGeometry = () => ({width: 1920, height: 1080}),
      ctx => ctx.desktops = () => [],
      ctx => ctx.desktops = () => [{screen: 1, type: 'org.kde.plasma.folder'}],
      ctx => ctx.desktops = () => [{screen: 0, type: 'missing'}],
      ctx => ctx.panels = () => [],
      ctx => ctx.panels = () => [{screen: 0, type: 'org.kde.panel', widgets: () => []}]
    ];
    for (const change of changes) {
      const ctx = context(); change(ctx);
      let rejected = false;
      try { vm.runInNewContext(script, ctx, {timeout: 1000}); } catch (_) { rejected = true; }
      if (!rejected) throw Error('A broken layout was accepted');
    }
    console.log('PASS: layout assertions and seven rejection controls');
  JS
  File.write("#{temp}/layout-test.js", node_test)
  run.call(:ok, 'node', "#{temp}/layout-test.js", "#{source}/layout.js")
  # Run the real shell cleanup path after a forced startup failure. Only the
  # external graphics programs and clock are replaced in this temporary copy.
  %w[term kill].each do |mode|
    work = "#{temp}/cleanup-#{mode}"
    FileUtils.mkdir_p("#{work}/runtime")
    socket = UNIXServer.new("#{work}/runtime/wayland-0")
    begin
      FileUtils.cp(["#{source}/check-results.sh", "#{source}/layout.js"], work)
      File.write("#{work}/timeout", "#!/bin/sh\nshift 3\nexec \"$@\"\n")
      File.write("#{work}/date", "#!/bin/sh\nif [ -e date-used ]; then echo 100; else touch date-used; echo 0; fi\n")
      child = <<~RUBY
        #!#{RbConfig.ruby}
        trap('TERM') { #{mode == 'term' ? 'exit 0' : 'nil'} }
        File.write('child-ready', Process.pid.to_s)
        loop { sleep 0.1 }
      RUBY
      File.write("#{work}/plasmashell", child)
      # Wait for the child to install its signal handler before returning from
      # the failed D-Bus query. The fixture itself has a bounded wait.
      File.write("#{work}/qdbus", <<~SH)
        #!/bin/sh
        case "$1" in
        org.kde.KWin) cat <<'END'
        #{support}END
        ;;
        *) tries=0; while [ ! -f child-ready ] && [ "$tries" -lt 20 ]; do
            sleep 0.1; tries=$((tries + 1))
           done
           exit 1 ;;
        esac
      SH
      %w[timeout qdbus date plasmashell].each { |name| File.chmod(0o700, "#{work}/#{name}") }
      session = File.read("#{source}/session.sh")
      session = session.gsub('/usr/bin/timeout', "#{work}/timeout")
                       .gsub('/usr/pkg/qt6/bin/qdbus', "#{work}/qdbus")
                       .gsub('/usr/pkg/bin/plasmashell', "#{work}/plasmashell")
      File.write("#{work}/session.sh", session)
      run.call(:fail, {'EMBER_PLASMA_OUTPUT' => work,
                      'XDG_RUNTIME_DIR' => "#{work}/runtime",
                      'PATH' => "#{work}:#{ENV.fetch('PATH')}"}, '/bin/sh', "#{work}/session.sh")
      abort 'Failure status was lost' if File.read("#{work}/client.status").strip == '0'
      expected = mode == 'term' ? 0 : 137
      abort 'Unexpected shutdown status' unless File.read("#{work}/plasmashell.status").to_i == expected
      pid = File.read("#{work}/plasmashell.pid").to_i
      begin
        Process.kill(0, pid)
        abort "Cleanup leaked child #{pid}"
      rescue Errno::ESRCH
        checks += 1
      end
    ensure
      socket.close
      # A failed assertion must not leave a host fixture running.
      if File.file?("#{work}/plasmashell.pid")
        begin
          Process.kill('KILL', File.read("#{work}/plasmashell.pid").to_i)
        rescue Errno::ESRCH
          nil
        end
      end
    end
  end
end
puts "PASS: #{checks} host checks; no target Plasma or GPU execution"
