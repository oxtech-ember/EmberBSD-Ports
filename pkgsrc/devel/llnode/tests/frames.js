globalThis.emberSample = {answer: 42, message: 'ordinary-object'};
const stop = () => process.kill(process.pid, 'SIGSTOP');
const inferredArrow = () => stop();
function namedFrame() { inferredArrow(); }
namedFrame();
