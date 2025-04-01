from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *

# import common.utils as utils


def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = var_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId("$main")
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), "i64") for x in vars]
    return WasmModule(
        imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)],
    )


def identToWasmId(x: Ident) -> WasmId:
    return WasmId(f"${x.name}")


def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    instructions: list[WasmInstr] = []

    for stmt in stmts:
        instructions.append(compileStmt(stmt))

    return instructions


def compileStmt(stmt: stmt) -> WasmInstr:

    match stmt:
        case Assign(x,IntConst(n)):
            print(f"Assign: {x} = {n}")
            instruction = WasmInstrComment(f"Assign: {x} = {n}")
        case Assign(_,_):
            print(f"Assign")
            instruction = WasmInstrComment(f"Assign")
        case StmtExp(e):
            print(f"StmtExp: {x} = {n}")
            instruction = Stm
        

    return instruction

    # for statement in stmts:
    #     if isinstance(statement, Assign):
    #         left = statement.var
    #         right = statement.right
    #         a = Assign(left, right)
    #         print(a.var)
