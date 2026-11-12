#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the real anonymous-file allocation of Xwayland.
require 'open3'
require 'json'
require 'fileutils'

abort 'Usage: shm-fallocate.rb UPSTREAM_C PATCHED_C NEW_RESULTS' unless ARGV.size == 3
before, after, work = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(work)
native = ENV.fetch('HOST_CC', '/usr/bin/cc')
target = ENV['TARGET_CC']&.split # compiler and its target selection, e.g. "clang --target=x86_64--netbsd"
sysroot = ENV['TARGET_SYSROOT']

# Extract the real functions; nothing of the allocation logic is re-implemented.
def extract(path)
  source = File.read(path, encoding: 'UTF-8')
  parts = {
    tmpfile: source[/^static int\ncreate_tmpfile_cloexec\(char \*tmpname\)\n\{.*?^\}\n/m],
    anonymous: source[/^static int\nos_create_anonymous_file\(off_t size\)\n\{.*?^\}\n/m],
    cloexec: source[/^#ifndef HAVE_MKOSTEMP\nstatic int\nset_cloexec_or_close\(int fd\)\n\{.*?^\}\n#endif\n/m],
  }
  raise "Missing real function in #{path}" unless parts[:tmpfile] && parts[:anonymous] && parts[:cloexec]
  raise "Ambiguous os_create_anonymous_file in #{path}" unless source.scan('os_create_anonymous_file(off_t size)').size == 1
  raise "posix_fallocate call missing in #{path}" unless parts[:anonymous].scan('posix_fallocate(fd, 0, size)').size == 1
  parts
end

# Result of the stubbed posix_fallocate() per case, and the expected outcome of
# os_create_anonymous_file(): "fd" (a file of the requested size) or an errno name.
CASES = [
  # name,            stub result, upstream expects, patched expects
  ['einval',        'EINVAL',     'EINVAL',  'fd'],     # memfd on NetBSD/EmberBSD
  ['eopnotsupp',    'EOPNOTSUPP', 'EOPNOTSUPP', 'fd'],  # file system without fallocate
  ['enosys',        'ENOSYS',     'ENOSYS',  'fd'],
  ['enospc',        'ENOSPC',     'ENOSPC',  'ENOSPC'], # real failures are still errors
  ['eio',           'EIO',        'EIO',     'EIO'],
  ['efbig',         'EFBIG',      'EFBIG',   'EFBIG'],
  ['ebadf',         'EBADF',      'EBADF',   'EBADF'],
  ['ok',            '0',          'fd',      'fd'],
  # NetBSD posix_fallocate(2): success without a change of the file size
  ['ok-no-resize',  'OK_NOSIZE',  'size0',   'fd'],
  ['eintr-then-ok', 'EINTR_ONCE', 'fd',      'fd'],
].freeze

def harness(parts)
  <<~C
    #define _GNU_SOURCE
    #include <errno.h>
    #include <fcntl.h>
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    #include <sys/mman.h>
    #include <sys/stat.h>
    #include <sys/types.h>
    #include <unistd.h>
    #define HAVE_MEMFD_CREATE 1
    #define HAVE_POSIX_FALLOCATE 1
    #define HAVE_MKOSTEMP 1
    static int os_move_fd(int fd) { return fd; }
    static void OsBlockSignals(void) {}
    static void OsReleaseSignals(void) {}
    static int stub_result;
    static int stub_calls;
    /* The harness replaces only the libc call whose result the cases control. */
    static int
    stub_posix_fallocate(int fd, off_t offset, off_t len)
    {
        (void)offset;
        stub_calls++;
        if (stub_result == -1 && stub_calls == 1)
            return EINTR;
        if (stub_result > 0)
            return stub_result;
        if (stub_result == -2)
            return 0;
        /* A successful allocation leaves a file of the requested size. */
        return ftruncate(fd, len) == 0 ? 0 : errno;
    }
    #ifndef REAL_POSIX_FALLOCATE
    #define posix_fallocate stub_posix_fallocate
    #endif
    #{parts[:cloexec]}
    #{parts[:tmpfile]}
    #{parts[:anonymous]}
    #ifdef REAL_POSIX_FALLOCATE
    /* Run the unmodified libc call: report what this system does with a memfd. */
    int
    main(void)
    {
        int fd = memfd_create("test", MFD_CLOEXEC | MFD_ALLOW_SEALING);
        if (fd < 0) { printf("memfd_create failed: errno %d\\n", errno); return 2; }
        int ret = posix_fallocate(fd, 0, 4096);
        printf("posix_fallocate(memfd) = %d\\n", ret);
        close(fd);
        fd = os_create_anonymous_file(4096);
        if (fd < 0) { printf("os_create_anonymous_file = -1, errno %d\\n", errno); return 1; }
        struct stat st;
        if (fstat(fd, &st) != 0 || st.st_size != 4096) { printf("size %lld\\n", (long long)st.st_size); return 3; }
        char *map = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (map == MAP_FAILED) { printf("mmap failed: errno %d\\n", errno); return 4; }
        memset(map, 0x5a, 4096);
        if (map[4095] != 0x5a) return 5;
        printf("os_create_anonymous_file = %d, 4096 bytes mapped and written\\n", fd);
        return 0;
    }
    #else
    int
    main(int argc, char **argv)
    {
        static const struct { const char *name; int value; } errors[] = {
            {"EINVAL", EINVAL}, {"EOPNOTSUPP", EOPNOTSUPP}, {"ENOSYS", ENOSYS},
            {"ENOSPC", ENOSPC}, {"EIO", EIO}, {"EFBIG", EFBIG}, {"EBADF", EBADF},
            {"0", 0}, {"EINTR_ONCE", -1}, {"OK_NOSIZE", -2}, {NULL, 0}
        };
        const char *stub = argv[1], *expect = argv[2];
        if (argc != 3) return 64;
        int known = 0;
        for (int i = 0; errors[i].name; ++i)
            if (strcmp(errors[i].name, stub) == 0) { stub_result = errors[i].value; known = 1; }
        if (!known) return 64;
        errno = 0;
        int fd = os_create_anonymous_file(8192);
        int saved = errno;
        if (strcmp(expect, "size0") == 0) {
            struct stat st;
            if (fd < 0 || fstat(fd, &st) != 0 || st.st_size != 0) { printf("expected an unsized descriptor\\n"); return 1; }
            close(fd);
            printf("descriptor with 0 bytes (file not sized)\\n");
            return 0;
        }
        if (strcmp(expect, "fd") == 0) {
            struct stat st;
            if (fd < 0) { printf("expected a descriptor, got -1 errno %d\\n", saved); return 1; }
            if (fstat(fd, &st) != 0 || st.st_size != 8192) { printf("wrong size %lld\\n", (long long)st.st_size); return 1; }
            if (strcmp(stub, "EINTR_ONCE") == 0 && stub_calls != 2) { printf("EINTR not retried (%d calls)\\n", stub_calls); return 1; }
            close(fd);
            printf("descriptor with 8192 bytes\\n");
            return 0;
        }
        for (int i = 0; errors[i].name; ++i)
            if (strcmp(errors[i].name, expect) == 0) {
                if (fd == -1 && saved == errors[i].value) { printf("-1 with errno %s\\n", expect); return 0; }
                printf("expected -1/%s, got fd %d errno %d\\n", expect, fd, saved);
                return 1;
            }
        return 64;
    }
    #endif
  C
end

commands = []
[before, after].each_with_index do |input, index|
  version = index.zero? ? 'upstream' : 'patched'
  file = File.join(work, version + '.c')
  File.write(file, harness(extract(input)))
  # Native run with the stubbed libc result (warnings are errors; ASan/UBSan are
  # used when the host compiler has them).
  executable = File.join(work, version)
  flags = ['-std=gnu99', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-Wno-unused-parameter']
  sanitize = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
  command = [native, *flags, *sanitize, file, '-o', executable]
  out, err, status = Open3.capture3(*command)
  unless status.success?
    command = [native, *flags, file, '-o', executable]
    out, err, status = Open3.capture3(*command)
    sanitize = []
  end
  File.write(executable + '-compile.log', command.inspect + "\n" + out + err)
  raise "Native compile failed: #{version}: #{err}" unless status.success?
  commands << {directory: work, file: file, arguments: command}
  CASES.each do |name, stub, upstream, patched|
    expect = index.zero? ? upstream : patched
    out, err, status = Open3.capture3({'ASAN_OPTIONS' => 'halt_on_error=1', 'UBSAN_OPTIONS' => 'halt_on_error=1'}, executable, stub, expect)
    File.write("#{executable}-#{name}.log", out + err)
    raise "Unexpected result: #{version} #{name}: #{out}#{err}" unless status.success? && err.empty?
    puts "PASS: #{version} #{name}: #{out.strip}"
  end
  next unless target && sysroot
  # The same source must compile strictly for the target. Both variants are
  # linked for execution on the target (see tests/README.md): "stubbed" takes
  # the case and expectation as arguments like the native run, "real" uses the
  # unmodified libc call.
  %w[stubbed real].each do |kind|
    extra = kind == 'real' ? ['-DREAL_POSIX_FALLOCATE'] : []
    obj = File.join(work, "#{version}-target-#{kind}")
    cross = [*target, '--sysroot=' + sysroot, '-fuse-ld=lld', '-std=gnu99', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-Wno-unused-parameter', *extra, file, '-o', obj]
    out, err, status = Open3.capture3(*cross)
    File.write(obj + '-compile.log', cross.inspect + "\n" + out + err)
    raise "Target compile failed: #{version} #{kind}: #{err}" unless status.success?
    puts "PASS: #{version} target #{kind} build (#{File.basename(obj)})"
  end
end
File.write(File.join(work, 'compile_commands.json'), JSON.pretty_generate(commands))
