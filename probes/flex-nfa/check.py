#!/usr/bin/env python3
"""Check Flex's actual epsilon-closure function with an independent oracle.

Run compilation on the selected build host. This script does not fetch sources.
"""
import argparse
import pathlib
import re
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument("source", type=pathlib.Path)
p.add_argument("--cc", default="cc")
p.add_argument("--structure-only", action="store_true")
p.add_argument("--sanitize", action="store_true")
a = p.parse_args()
source = a.source.read_text()
start = source.index("void    mark_beginning_as_normal (int mach)")
opening = source.index("{", start)
depth = 1
end = opening + 1
while depth:
    depth += (source[end] == "{") - (source[end] == "}")
    end += 1
function = source[start:end]
code = re.sub(r'"(?:\\.|[^"\\])*"', '""', function)
if len(re.findall(r"\bmark_beginning_as_normal\s*\(", code)) != 1:
    raise SystemExit("FAIL: production epsilon closure still recurses")
if a.structure_only:
    print("PASS: production epsilon closure does not recurse")
    raise SystemExit(0)

prefix = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define STATE_NORMAL 1
#define STATE_TRAILING_CONTEXT 2
#define SYM_EPSILON 0
#define NO_TRANSITION 0
#define _(s) (s)
static int current_mns;
static int *state_type, *transchar, *trans1, *trans2;
static void flexerror(const char *message) { fprintf(stderr, "%s\n", message); exit(2); }
static int *allocate_integer_array(int count) {
    int *v = calloc((size_t)count, sizeof(*v));
    if (!v) flexerror("allocation failed");
    return v;
}
'''
suffix = r'''
static unsigned rng = 17;
static unsigned next_random(void) { rng = rng * 1664525u + 1013904223u; return rng; }
static void init(int count) {
    current_mns = count + 1;
    state_type = allocate_integer_array(current_mns);
    transchar = allocate_integer_array(current_mns);
    trans1 = allocate_integer_array(current_mns);
    trans2 = allocate_integer_array(current_mns);
    for (int i = 1; i < current_mns; ++i) state_type[i] = STATE_TRAILING_CONTEXT;
}
static void cleanup(void) { free(state_type); free(transchar); free(trans1); free(trans2); }
/* The oracle computes reachability first and mutates the expected result last. */
static void check(int first) {
    int *seen = allocate_integer_array(current_mns);
    int *queue = allocate_integer_array(current_mns);
    int *expected = allocate_integer_array(current_mns);
    memcpy(expected, state_type, (size_t)current_mns * sizeof(*expected));
    int head = 0, tail = 0;
    seen[first] = 1; queue[tail++] = first;
    while (head < tail) {
        int state = queue[head++];
        if (state_type[state] == STATE_NORMAL) continue;
        expected[state] = STATE_NORMAL;
        if (transchar[state] != SYM_EPSILON) continue;
        int edges[2] = {trans1[state], trans2[state]};
        for (int j = 0; j < 2; ++j) {
            int dest = edges[j];
            if (dest < 0 || dest >= current_mns) flexerror("invalid oracle edge");
            if (dest && !seen[dest]) {
                if (tail >= current_mns) flexerror("oracle queue overflow");
                seen[dest] = 1; queue[tail++] = dest;
            }
        }
    }
    mark_beginning_as_normal(first);
    if (memcmp(expected, state_type, (size_t)current_mns * sizeof(*expected)))
        flexerror("closure differs from independent reachability oracle");
    free(seen); free(queue); free(expected);
}
int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "invalid") == 0) {
        init(1); state_type[1] = 99; mark_beginning_as_normal(1); return 3;
    }
    init(3); state_type[1] = STATE_NORMAL; trans1[1] = 2; check(1); cleanup();
    init(3); transchar[1] = 97; trans1[1] = 2; check(1); cleanup();
    init(4); trans1[1] = 2; trans2[1] = 3; trans1[2] = 4; trans2[3] = 4;
    check(1); check(1); cleanup();
    init(3); trans1[1] = 2; trans1[2] = 3; trans1[3] = 1; check(1); cleanup();
    for (int trial = 0; trial < 1000; ++trial) {
        init(128);
        for (int i = 1; i < current_mns; ++i) {
            state_type[i] = next_random() % 7 ? STATE_TRAILING_CONTEXT : STATE_NORMAL;
            transchar[i] = next_random() % 5 ? SYM_EPSILON : 97;
            trans1[i] = (int)(next_random() % (unsigned)current_mns);
            trans2[i] = (int)(next_random() % (unsigned)current_mns);
        }
        check(1); cleanup();
    }
    init(200000);
    for (int i = 1; i < current_mns - 1; ++i) trans1[i] = i + 1;
    check(1); cleanup();
    puts("PASS: 1006 closure cases (barrier, terminal, diamond, repeat, cycle, random, large graph)");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="flex-nfa-check-") as work:
    work = pathlib.Path(work)
    test = work / "closure.c"
    binary = work / "closure"
    test.write_text(prefix + function + suffix)
    flags = ["-std=c99", "-O2", "-g", "-Wall", "-Wextra", "-Werror", "-fanalyzer"]
    if a.sanitize:
        flags += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    subprocess.run([a.cc, *flags, str(test), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
    invalid = subprocess.run([str(binary), "invalid"], capture_output=True, text=True, timeout=10)
    assert invalid.returncode == 2 and "bad state type" in invalid.stderr, invalid
    print("PASS: invalid state remains an explicit error")
