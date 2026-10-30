#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
require 'fileutils'
require 'open3'
require 'tmpdir'
source = File.read(__dir__ + '/../cross/run-powervr-offscreen.sh')
Dir.mktmpdir('ember-pvr-offscreen-runner-') do |root|
  bin = root + '/bin'; FileUtils.mkdir_p(bin)
  write = lambda do |path, text|
    File.write(path, text); File.chmod(0755, path)
  end
  write.call(bin + '/uname', "#!/bin/sh\ncase \"$1\" in -s) echo NetBSD;; -p) echo aarch64;; *) echo EmberBSD-test;; esac\n")
  write.call(bin + '/pkg_info', <<'SH')
#!/bin/sh
case "$2" in MesaLib-*) echo "${TEST_MESA:-MesaLib-26.2.6nb10}";; libdrm-2.4.134nb2) echo libdrm-2.4.134nb2;; *) exit 9;; esac
SH
  write.call(bin + '/ldd', "#!/bin/sh\nprintf '%s\\n' \"$1: modeled installed closure\"\n")
  write.call(bin + '/timeout', "#!/bin/sh\n[ \"$1\" = 60 ] || exit 8\nshift\nexec \"$@\"\n")
  write.call(root + '/powervr-offscreen', <<'SH')
#!/bin/sh
[ "$#" = 1 ] && [ "$1" = /dev/dri/renderD128 ] || exit 10
[ "$VK_DRIVER_FILES" = "$TEST_MANIFEST" ] || exit 11
[ "${LD_LIBRARY_PATH+x}${LD_PRELOAD+x}${VK_ICD_FILENAMES+x}${VK_ADD_DRIVER_FILES+x}${VK_ADDITIONAL_DRIVER_FILES+x}" = '' ] || exit 12
printf '%s\n' 'MODELED OFFSCREEN RUN'
exit "${TEST_STATUS:-0}"
SH
  manifest = root + '/icd.json'; File.write(manifest, '{}')
  replacements = {
    '/usr/pkg/share/vulkan/icd.d/powervr_mesa_icd.json' => manifest,
    '/usr/pkg/lib/libvulkan_powervr_mesa.so' => root + '/icd.so',
    '/usr/bin/timeout' => bin + '/timeout'
  }
  replacements.each do |from, to|
    abort 'Runner location changed: ' + from unless source.scan(from).length == 1
    source = source.sub(from, to)
  end
  runner = root + '/run-powervr-offscreen.sh'; File.write(runner, source)
  env = {'PATH' => bin + ':' + ENV.fetch('PATH'), 'PVR_I_WANT_A_BROKEN_VULKAN_DRIVER' => '1',
    'TEST_MANIFEST' => manifest, 'LD_LIBRARY_PATH' => 'unexpected', 'LD_PRELOAD' => 'unexpected',
    'VK_ICD_FILENAMES' => 'unexpected', 'VK_ADD_DRIVER_FILES' => 'unexpected', 'VK_ADDITIONAL_DRIVER_FILES' => 'unexpected'}
  run = lambda do |name, overrides, expected|
    directory = root + '/' + name
    out, err, status = Open3.capture3(env.merge(overrides), 'sh', runner, '/dev/dri/renderD128', directory)
    abort "#{name}: expected #{expected}, got #{status.exitstatus}: #{out} #{err}" unless status.exitstatus == expected
    [directory, out, err]
  end
  dir, out, = run.call('accepted', {}, 0)
  abort 'Consumer was not called' unless out.include?('MODELED OFFSCREEN RUN')
  abort 'Wrong recorded identity' unless File.read(dir + '/mesa-package.txt') == "MesaLib-26.2.6nb10\n"
  abort 'Wrong exit record' unless File.read(dir + '/exit-status.txt') == "0\n"
  dir, = run.call('pending', {'TEST_STATUS' => '3'}, 3)
  abort 'Lost uncertain completion status' unless File.read(dir + '/exit-status.txt') == "3\n"
  _, out, err = run.call('wrong-version', {'TEST_MESA' => 'MesaLib-26.2.5nb10'}, 2)
  abort 'Wrong package was executed' if out.include?('MODELED OFFSCREEN RUN')
  abort 'Missing version diagnostic' unless err.include?('Require MesaLib-26.2.6nb10')
  run.call('no-opt-in', {'PVR_I_WANT_A_BROKEN_VULKAN_DRIVER' => nil}, 2)
  File.unlink(manifest)
  _, out, = run.call('missing-manifest', {}, 1)
  abort 'Missing ICD was executed' if out.include?('MODELED OFFSCREEN RUN')
end
puts 'PASS: actual runner identity, environment, package, opt-in, missing ICD and exit-status contracts'
