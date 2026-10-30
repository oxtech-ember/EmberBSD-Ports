require('module').registerHooks({
  resolve(specifier, context, next) {
    if (specifier === 'embedder-test')
      return {url: 'embedder-test:fixture', shortCircuit: true};
    return next(specifier, context);
  },
  load(url, context, next) {
    if (url === 'embedder-test:fixture')
      return {format: 'module', shortCircuit: true,
              source: 'export const answer = 42; export default answer;'};
    return next(url, context);
  }
});
