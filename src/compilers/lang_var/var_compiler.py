from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *
import common.utils as utils

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = var_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64') for x in vars]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
    exports=[WasmExport("main", WasmExportFunc(idMain))],
    globals=[],
    data=[],
    funcTable=WasmFuncTable([]),
    funcs=[WasmFunc(idMain, [], None, locals, instrs)])