"""Inject a metadata value in the stopped diagnostic process only."""
import lldb

def inject(debugger, command, result, internal_dict):
    name, value = command.split()
    target = debugger.GetSelectedTarget()
    symbols = target.FindSymbols('v8dbg_' + name)
    if not symbols.GetSize():
        result.SetError('metadata symbol not found: ' + name)
        return
    address = symbols.GetContextAtIndex(0).GetSymbol().GetStartAddress().GetLoadAddress(target)
    error = lldb.SBError()
    order = 'little' if target.GetByteOrder() == lldb.eByteOrderLittle else 'big'
    data = int(value).to_bytes(4, order, signed=True)
    written = target.GetProcess().WriteMemory(address, data, error)
    if error.Fail() or written != len(data):
        result.SetError('metadata injection failed: ' + str(error))

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f metadata_fault.inject ember-metadata-fault')
