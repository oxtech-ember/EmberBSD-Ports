class EmberSpill {}
const sample = new EmberSpill();
sample.a = 1; sample.b = 2; sample.c = 3; sample.d = 4;
sample.e = 5; sample.f = 6; sample.g = 7; sample.h = 8;
sample.spillNumber = 4242; sample.spillString = 'out-of-object';
sample.when = new Date(1700000000123);
sample.array = ['array-value', 77, 'third'];
sample.outNumber = 9876; sample.outString = 'actual-spill';
globalThis.emberSpill = sample;
%DebugPrint(sample);
const stop = () => process.kill(process.pid, 'SIGSTOP');
stop();
