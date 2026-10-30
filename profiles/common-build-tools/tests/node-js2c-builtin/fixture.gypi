{
  'target_defaults': {
    'target_conditions': [
      ['_target_name=="node_base"', {
        'defines': [ 'NODE_EMBEDDER_BUILTINS=1' ],
        'sources': [ '<(ember_test_generated_source)' ],
      }],
      ['_target_name=="cctest"', {
        'defines': [ 'NODE_EMBEDDER_BUILTINS=1' ],
      }],
    ],
  },
}
