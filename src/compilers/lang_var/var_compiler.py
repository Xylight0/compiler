from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *

#! I added comments throughout the code to explain my thought process and understanding.

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
    """Converts an Lvar Identifier to a WasmId."""
    return WasmId(f"${x.name}")


def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    """Compiles a list of Lvar statements into a list of Wasm instructions."""
    instructions: list[WasmInstr] = []

    for stmt in stmts:
        # Each statement compilation can produce multiple instructions
        instructions.extend(compileStmt(stmt))

    return instructions


def compileStmt(stmt: stmt) -> list[WasmInstr]:
    """Compiles a single Lvar statement into a list of Wasm instructions."""

    match stmt:
        case Assign(var, right):
            # 1. Compile the right-hand side expression. Its value will be on the stack.
            instrs = compileExp(right)
            # 2. Store the value from the stack into the local variable.
            instrs.append(WasmInstrVarLocal("set", identToWasmId(var)))
            return instrs

        case StmtExp(e):
            # 1. Compile the expression.
            expInstrs, leavesValueOnStack = compileExpValue(e)
            # 2. If the expression leaves a value on the stack (e.g., input_int(), x + y),
            #    and the statement context doesn't use it, we must drop it ensuring the stack is in the correct state (cleared) for the next operation.
            #    Functions like print() consume their argument and don't leave a value.
            if leavesValueOnStack:
                expInstrs.append(WasmInstrDrop())
            return expInstrs


def compileExpValue(e: exp) -> tuple[list[WasmInstr], bool]:
    """
    Compiles an expression and returns the instructions and a boolean
    indicating if a value is left on the Wasm stack.
    """
    instrs = compileExp(e)

    # Determine if a value is left based on the expression type
    match e:
        case Call(Ident("print"), _):
            # The 'call $print_i64' instruction consumes the argument and pushes no result.
            return instrs, False
        case (
            IntConst(_)
            | Name(_)
            | UnOp(_, _)
            | BinOp(_, _, _)
            | Call(Ident("input_int"), _)
        ):
            # All other currently supported expressions leave an i64 value on the stack.
            return instrs, True
        case Call(name, _):
            raise Exception(f"Unsupported function call in expression: {name.name}")


def compileExp(e: exp) -> list[WasmInstr]:
    """Compiles an Lvar expression into Wasm instructions that leave the result on the stack."""
    match e:
        case IntConst(n):
            # Push an i64 constant onto the stack
            return [WasmInstrConst("i64", n)]

        case Name(name):
            # Get the value of a local variable and push it onto the stack
            return [WasmInstrVarLocal("get", identToWasmId(name))]

        case UnOp(USub(), arg):
            # Compile negation (0 - arg)
            # 1. Compile the argument
            instrs = compileExp(arg)
            # 2. Prepend 0
            instrs.insert(0, WasmInstrConst("i64", 0)) 
            # 3. Subtract (stack is now: 0, arg_value)
            instrs.append(WasmInstrNumBinOp("i64", "sub"))
            return instrs

        case BinOp(left, op, right):
            # Compile binary operations
            # 1. Compile left operand
            instrs = compileExp(left)
            # 2. Compile right operand (stack: left_val, right_val)
            instrs.extend(compileExp(right))
            # 3. Perform the operation
            match op:
                case Add():
                    instrs.append(WasmInstrNumBinOp("i64", "add"))
                case Sub():
                    instrs.append(WasmInstrNumBinOp("i64", "sub"))
                case Mul():
                    instrs.append(WasmInstrNumBinOp("i64", "mul"))
            return instrs

        case Call(Ident("print"), [arg]):
            # Compile the argument
            instrs = compileExp(arg)
            # Call the imported $print_i64 function
            instrs.append(WasmInstrCall(WasmId("$print_i64")))
            # $print_i64 takes i64, returns nothing. It consumes the stack value (stack: arg_value).
            return instrs

        case Call(Ident("input_int"), []):
            # Call the input function
            # $input_i64 takes nothing, returns i64. It pushes a value.
            return [WasmInstrCall(WasmId("$input_i64"))]

        case Call(name, args):
            # only 'print' and 'input_int' are known functions
            numArgs = len(args)

            if name.name == "print":
                raise Exception(
                    f"'print' called with {numArgs} arguments, expected 1."
                )
            elif name.name == "input_int":
                raise Exception(
                    f"'input_int' called with {numArgs} arguments, expected 0."
                )
            else:
                raise Exception(f"Unsupported function call: {name.name}")
