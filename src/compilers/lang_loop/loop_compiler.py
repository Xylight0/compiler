from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as loop_tychecker
from common.compilerSupport import *

#! I added comments throughout the code to explain my thought process and understanding.

labelCounter = 0


def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = loop_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId("$main")
    locals: list[tuple[WasmId, WasmValtype]] = [
        (identToWasmId(x), tyToWasmValueType(y.ty)) for (x, y) in vars.items()
    ]

    return WasmModule(
        imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)],
    )


def tyToWasmValueType(y: ty) -> Literal["i32", "i64"]:
    """Converts a ty to a value type."""
    match y:
        case Bool():
            return "i32"
        case Int():
            return "i64"


def identToWasmId(x: Ident) -> WasmId:
    """Converts an Lvar Identifier to a WasmId."""
    return WasmId(f"${x.name}")


def newLabel(prefix: str) -> WasmId:
    """Generates a new WasmId label."""
    global labelCounter
    labelCounter += 1
    return WasmId(f"${prefix}_{labelCounter}")


def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    """Compiles a list of Lvar statements into a list of Wasm instructions."""
    instructions: list[WasmInstr] = []

    for stmt in stmts:
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
            instrs, leavesValueOnStack = compileExpValue(e)
            # 2. If the expression leaves a value on the stack (e.g., input_int(), x + y),
            #    and the statement context doesn't use it, we must drop it ensuring the stack is in the correct state (cleared) for the next operation.
            #    Functions like print() consume their argument and don't leave a value.
            if leavesValueOnStack:
                instrs.append(WasmInstrDrop())
            return instrs

        case IfStmt(cond, thenBody, elseBody):
            # 1. Compile condition
            instrs = compileExp(cond)
            # 2. Compile the branches separately
            instrs_then = compileStmts(thenBody)
            instrs_else = compileStmts(elseBody)
            # 3. Create the Wasm If instruction
            instrs.append(WasmInstrIf(None, instrs_then, instrs_else))
            return instrs

        case WhileStmt(cond, body):
            # 1. generate unique labels
            block_label = newLabel("while_block")
            loop_label = newLabel("while_loop")
            # 2. Compile body statements separately
            instrs_body = compileStmts(body)
            # assemble the loop body instructions
            loop_body_instrs = [
                # Evaluate condition again inside the loop
                *compileExp(cond),  # Returns i32 for evalaution
                # check if condition is false
                WasmInstrConst("i32", 0),  # Push 0
                WasmInstrIntRelOp("i32", "eq"),  # Compare cond result with 0
                # If condition was false (eq result is 1), branch to the END of the block
                WasmInstrBranch(
                    target=block_label, conditional=True
                ),  # br_if $block_label_X (branches if eq result is 1)
                # if condition was true (eq result was 0), execute the body
                *instrs_body,
                # Unconditionaly jump back to the beginning of the loop
                WasmInstrBranch(
                    target=loop_label, conditional=False
                ),  # br $loop_label_X
            ]

            loop_instr = WasmInstrLoop(loop_label, loop_body_instrs)
            block_instr = WasmInstrBlock(block_label, None, [loop_instr])
            return [block_instr]


def tyOfExp(e: exp) -> ty:
    """Extracts the type (Int or Bool) from an expression."""
    if e.ty is None:
        raise Exception(f"Compiler Error: Expression missing type annotation: {e}")
    match e.ty:
        case NotVoid(t):
            if (t, (Int, Bool)):
                return t
            else:
                raise Exception(
                    f"Compiler Error: Expression has unexpected NotVoid type '{type(t)}': {e}"
                )
        case Void():
            raise Exception(
                f"Compiler Error: Expression has Void type where Int or Bool was expected: {e}"
            )


def compileExpValue(e: exp) -> tuple[list[WasmInstr], bool]:
    """
    Compiles an expression and returns the instructions and a boolean
    indicating if a value is left on the Wasm stack.
    """
    instrs = compileExp(e)
    # Determine if a value is left based on the expression type
    expTy = e.ty
    if expTy is None:
        raise Exception(f"Compiler Error: Expression missing type annotation: {e}")
    match expTy:
        case Void():
            return instrs, False
        case NotVoid(_):  # matches NotVoid(Int()) or NotVoid(Bool())
            return instrs, True


def compileExp(e: exp) -> list[WasmInstr]:
    """Compiles an Lvar expression into Wasm instructions that leave the result on the stack."""
    match e:
        case BoolConst(n):
            # Push an i32 constant onto the stack
            return [WasmInstrConst("i32", int(bool(n)))]

        case IntConst(n):
            # Push an i64 constant onto the stack
            return [WasmInstrConst("i64", n)]

        case Name(name):
            # Get the value of a local variable and push it onto the stack
            return [WasmInstrVarLocal("get", identToWasmId(name))]

        case UnOp(USub(), arg):
            # Compile unary negation (0 - arg)
            # 1. Compile the argument
            instrs = compileExp(arg)
            # 2. Prepend 0
            instrs.insert(0, WasmInstrConst("i64", 0))
            # 3. Subtract (stack is now: 0, arg_value)
            instrs.append(WasmInstrNumBinOp("i64", "sub"))
            return instrs

        case UnOp(Not(), arg):
            # Compile logical negation
            # 1. Compile the argument
            instrs = compileExp(arg)
            # 2. Prepend 0 (boolean)
            instrs.insert(0, WasmInstrConst("i32", 0))
            # 3. Apply equality compparison with 0
            instrs.append(WasmInstrIntRelOp("i32", "eq"))
            return instrs

        case BinOp(left, op, right):
            # Compile binary operations
            # 1. Compile left operand
            instrsLeft = compileExp(left)
            # 2. Compile right operand (stack: left_val, right_val)
            instrsRight = compileExp(right)
            # 3. Perform the operation for Numeric Binary Operation Instruction & Integer Relational Operation
            match op:
                # Arithmetic Ops (Int -> Int, use i64, result i64)
                case Add():
                    instrs = WasmInstrNumBinOp("i64", "add")
                case Sub():
                    instrs = WasmInstrNumBinOp("i64", "sub")
                case Mul():
                    instrs = WasmInstrNumBinOp("i64", "mul")

                # Comparison Ops (Int -> Bool, use i64 comparison, result i32)
                case Less():
                    instrs = WasmInstrIntRelOp("i64", "lt_s")
                case LessEq():
                    instrs = WasmInstrIntRelOp("i64", "le_s")
                case Greater():
                    instrs = WasmInstrIntRelOp("i64", "gt_s")
                case GreaterEq():
                    instrs = WasmInstrIntRelOp("i64", "ge_s")

                # Equality Ops (Int -> Bool OR Bool -> Bool, use i64 or i32, result i32)
                case Eq():
                    # Create instruction for the correct type
                    instrs = WasmInstrIntRelOp(tyToWasmValueType(tyOfExp(left)), "eq")
                case NotEq():
                    # create instruction for the correct type
                    instrs = WasmInstrIntRelOp(tyToWasmValueType(tyOfExp(left)), "ne")
                case And():
                    # Short-circuiting And: left && right
                    if_instr = WasmInstrIf(
                        "i32",
                        instrsRight,  # then block: if left is true, evaluate right
                        [
                            WasmInstrConst("i32", 0)
                        ],  # else block: if left is false, return 0
                    )
                    return instrsLeft + [if_instr]
                case Or():
                    # short-circuiting Or: left || right
                    if_instr = WasmInstrIf(
                        "i32",
                        [WasmInstrConst("i32", 1)],  # if left is true , result is 1
                        instrsRight,  # If left is false (0), result is right's value
                    )
                    return instrsLeft + [if_instr]
            return instrsLeft + instrsRight + [instrs]

        case Call(Ident("print"), [arg]):
            # 1. Compile the argument
            instrs = compileExp(arg)
            # 2. determine the type of the argument
            argTy = tyOfExp(arg)
            # 3. Choose the correct print function based on the type
            match argTy:
                case Int():
                    instrs.append(WasmInstrCall(WasmId("$print_i64")))
                case Bool():
                    instrs.append(WasmInstrCall(WasmId("$print_bool")))
            return instrs

        case Call(Ident("input_int"), []):
            # Call the input function
            # $input_i64 takes nothing, returns i64. It pushes a value.
            return [WasmInstrCall(WasmId("$input_i64"))]

        case Call(name, args):
            # only 'print' and 'input_int' are known functions
            numArgs = len(args)
            if name.name == "print":
                raise Exception(f"'print' called with {numArgs} arguments, expected 1.")
            elif name.name == "input_int":
                raise Exception(
                    f"'input_int' called with {numArgs} arguments, expected 0."
                )
            else:
                raise Exception(f"Unsupported function call: {name.name}")

        case _:
            raise Exception(f"Unsupported expression: {e}")
