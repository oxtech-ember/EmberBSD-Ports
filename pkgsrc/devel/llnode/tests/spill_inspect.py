import lldb, re

def check(debugger, command, result, internal_dict):
    interpreter = debugger.GetCommandInterpreter()
    out = lldb.SBCommandReturnObject()
    interpreter.HandleCommand('v8 findjsinstances -v EmberSpill', out)
    text = out.GetOutput()
    result.PutCString(text)
    match = re.search(r'\.array=(0x[0-9a-f]+):<Array:', text)
    if not match:
        result.SetError('array address missing')
        return
    out = lldb.SBCommandReturnObject()
    interpreter.HandleCommand('v8 inspect ' + match.group(1), out)
    result.PutCString(out.GetOutput())
    if not out.Succeeded():
        result.SetError(out.GetError())

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f spill_inspect.check ember-spill-check')
