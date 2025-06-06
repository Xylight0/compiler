from lang_array.array_astAtom import *
import lang_array.array_ast as plainAst
from common.wasm import *
import lang_array.array_tychecker as array_tychecker
import lang_array.array_transform as array_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *
import common.utils as utils

#! I added comments throughout the code to explain my thought process and understanding.
#! Applied code review feedback from Assignment 1&2


def compileModule(m: plainAst.mod, cfg: CompilerConfig) -> WasmModule:
    """Compiles the given module."""
    vars = array_tychecker.tycheckModule(m)
    ctx = array_transform.Ctx()

    lAstmts = array_transform.transStmts(m.stmts, ctx)  # translate L_Array to L_A_array
    instrs = compileStmts(lAstmts, cfg)
    idMain = WasmId("$main")

    # collect all vars
    all_locals: list[tuple[WasmId, WasmValtype]] = []
    all_locals.extend(Locals.decls())
    all_locals.extend(
        [(identToWasmId(x), tyToWasmValueType(y.ty)) for (x, y) in vars.items()]
    )
    all_locals.extend(
        [(identToWasmId(x), tyToWasmValueType(t)) for (x, t) in ctx.freshVars.items()]
    )

    return WasmModule(
        imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=Globals.decls(),
        data=Errors.data(),
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, all_locals, instrs)],
    )


def tyToWasmValueType(y: ty) -> Literal["i32", "i64"]:
    """Converts a ty to a value type."""
    match y:
        case Bool():
            return "i32"
        case Int():
            return "i64"
        case Array():
            return "i32"


def tyToWasmValueSize(y: ty):
    """Converts a ty to a value size (byte)."""
    match y:
        case Bool():
            return 4
        case Int():
            return 8
        case Array():
            return 4


def identToWasmId(x: Ident) -> WasmId:
    """Converts an Lvar Identifier to a WasmId."""
    return WasmId(f"${x.name}")


def compileStmts(stmts: list[stmt], cfg: CompilerConfig) -> list[WasmInstr]:
    """Compiles a list of Lvar statements into a list of Wasm instructions."""
    instructions: list[WasmInstr] = []

    for stmt in stmts:
        instructions.extend(compileStmt(stmt, cfg))

    return instructions


def compileStmt(stmt: stmt, cfg: CompilerConfig) -> list[WasmInstr]:
    """Compiles a single Lvar statement into a list of Wasm instructions."""

    match stmt:
        case Assign(var, right):
            # 1. Compile the right-hand side expression. Its value will be on the stack
            instrs = compileExp(right, cfg)
            # 2. Store the value from the stack into the local variable
            instrs.append(WasmInstrVarLocal("set", identToWasmId(var)))
            return instrs

        case StmtExp(e):
            # 1. Compile the expression
            instrs = compileExp(e, cfg)
            return instrs

        case IfStmt(cond, thenBody, elseBody):
            # 1. Compile condition
            instrs = compileExp(cond, cfg)
            # 2. Compile the branches separately
            instrsThen = compileStmts(thenBody, cfg)
            instrsElse = compileStmts(elseBody, cfg)
            # 3. Create the Wasm If instruction
            instrs.append(WasmInstrIf(None, instrsThen, instrsElse))
            return instrs

        case WhileStmt(cond, body):
            blockLabel = WasmId(f"$while_block")
            loopLabel = WasmId(f"$while_loop")

            # compile body statements
            instrsBody = compileStmts(body, cfg)
            loopBodyInstrs = [
                *compileExp(cond, cfg),
                WasmInstrConst("i32", 0),
                WasmInstrIntRelOp("i32", "eq"),
                # if condition was true exit
                WasmInstrBranch(target=blockLabel, conditional=True),
                # execute the body
                *instrsBody,
                # jump back to the beginning of the loop
                WasmInstrBranch(target=loopLabel, conditional=False),
            ]

            loopInstr = WasmInstrLoop(loopLabel, loopBodyInstrs)
            blockInstr = WasmInstrBlock(blockLabel, None, [loopInstr])
            return [blockInstr]

        case SubscriptAssign(left, index, right):
            instrs: list[WasmInstr] = []

            match utils.assertNotNone(right.ty):
                case NotVoid(t):
                    x = tyToWasmValueType(t)
                case Void():
                    raise Exception(
                        f"Compiler Error: Void type encountered in expression: {right}"
                    )

            instrs.extend(arrayOffsetInstrs(left, index, cfg))  # get array offset
            instrs.extend(
                [
                    *compileExp(right, cfg),
                    WasmInstrMem(x, "store"),
                ]
            )  # compile right value and store in array

            return instrs


def tyOfExp(e: exp) -> ty:
    """Extracts the type (Int, Bool or Array) from an expression."""

    match utils.assertNotNone(e.ty):
        case NotVoid(t):
            return t
        case Void():
            raise Exception(f"Compiler Error: Expression has Void type: {e}")


def compileInitArray(
    lenExp: atomExp, elemTy: ty, cfg: CompilerConfig
) -> list[WasmInstr]:
    """Initialization of a new array."""

    if isinstance(elemTy, Array):
        elemSize = tyToWasmValueSize(elemTy.elemTy)
    else:
        raise Exception(f"Compiler Error: 'elemTy' is not valid for type {elemTy}")

    maxMemSize = ((cfg.maxMemSize * 65536) - 100 - 4) // elemSize
    maxArrSize = ((cfg.maxArraySize) - 100 - 4) // elemSize
    maxLength = min(maxArrSize, maxMemSize)  # Max number of elements

    instrs: list[WasmInstr] = []

    instrs.append(WasmInstrVarGlobal("get", WasmId("$@free_ptr")))
    instrs.extend(compileExp(AtomExp(lenExp), cfg))
    instrs.append(WasmInstrVarLocal("tee", WasmId("$@tmp_i64")))

    # Evaluate length
    # Lower bound check
    instrs.append(WasmInstrConst("i64", 1))  # Min Length
    instrs.append(
        WasmInstrIntRelOp("i64", "lt_s")
    )  # Stack: is length > 1 (return i32: 0 or 1)

    instrs.append(
        WasmInstrIf(
            None,
            [
                *Errors.outputError(Errors.arraySize),
                WasmInstrTrap(),
            ],
            [],
        )
    )

    # Upper bound check
    instrs.append(WasmInstrVarLocal("get", WasmId("$@tmp_i64")))
    instrs.append(WasmInstrConst("i64", maxLength))
    instrs.append(
        WasmInstrIntRelOp("i64", "gt_s")
    )  # Stack: is length > MAX_LENGTH (return i32: 0 or 1)

    instrs.append(
        WasmInstrIf(
            None,
            [
                *Errors.outputError(Errors.arraySize),
                WasmInstrTrap(),
            ],
            [],
        )
    )

    # Compute header value
    instrs.extend(
        [
            WasmInstrVarGlobal("get", WasmId("$@free_ptr")),
            WasmInstrVarLocal("get", WasmId("$@tmp_i64")),
            WasmInstrConvOp("i32.wrap_i64"),
            WasmInstrConst("i32", 4),  # 4 bit left shift
            WasmInstrNumBinOp("i32", "shl"),
            WasmInstrConst("i32", 3),  # type: 3 if array else 1
            WasmInstrNumBinOp("i32", "xor"),
            WasmInstrMem("i32", "store"),
        ]
    )

    # Calculate array address and leave on stack
    instrs.extend(
        [
            WasmInstrVarLocal("get", WasmId("$@tmp_i64")),
            WasmInstrConvOp("i32.wrap_i64"),
            WasmInstrConst("i32", elemSize),  # elem size 8 (Int) or 4 (Array, Boolean)
            WasmInstrNumBinOp("i32", "mul"),
            WasmInstrConst("i32", 4),
            WasmInstrNumBinOp("i32", "add"),
            WasmInstrVarGlobal("get", WasmId("$@free_ptr")),
            WasmInstrNumBinOp("i32", "add"),
            WasmInstrVarGlobal("set", WasmId("$@free_ptr")),
        ]
    )

    return instrs


def arrayLenInstrs() -> list[WasmInstr]:
    "Load length of array from memory."
    instrs: list[WasmInstr] = []

    instrs.extend(
        [
            WasmInstrMem("i32", "load"),
            WasmInstrConst("i32", 4),  # 4 bit shift right
            WasmInstrNumBinOp("i32", "shr_u"),
            WasmInstrConvOp("i64.extend_i32_u"),
        ]
    )

    return instrs


def arrayOffsetInstrs(
    arrayExp: atomExp, indexExp: atomExp, cfg: CompilerConfig
) -> list[WasmInstr]:
    """Compute memory offset for array element at index"""

    arrTy = utils.assertNotNone(arrayExp.ty)

    if isinstance(arrTy, Array):
        elemSize = tyToWasmValueSize(arrTy.elemTy)
    else:
        raise Exception(f"Compiler Error: 'elemTy' is not valid for type {arrTy}")

    instrs: list[WasmInstr] = []

    # Check index in bounds
    # Lower bound check
    instrs.extend(compileExp(AtomExp(indexExp), cfg))
    instrs.append(WasmInstrConst("i64", 0))  # Min Index
    instrs.append(WasmInstrIntRelOp("i64", "lt_s"))
    # Stack: is index < 0 (return i32: 0 or 1)

    instrs.append(
        WasmInstrIf(
            None,
            [
                *Errors.outputError(Errors.arrayIndexOutOfBounds),
                WasmInstrTrap(),
            ],
            [],
        )
    )

    # Upper bound check
    instrs.extend(compileExp(AtomExp(arrayExp), cfg))
    instrs.extend(arrayLenInstrs())
    instrs.extend(compileExp(AtomExp(indexExp), cfg))
    instrs.append(WasmInstrIntRelOp("i64", "le_s"))
    # Stack: is length <= index (return i32: 0 or 1)

    instrs.append(
        WasmInstrIf(
            None,
            [
                *Errors.outputError(Errors.arrayIndexOutOfBounds),
                WasmInstrTrap(),
            ],
            [],
        )
    )

    instrs.extend(compileExp(AtomExp(arrayExp), cfg))
    instrs.extend(compileExp(AtomExp(indexExp), cfg))

    # Offset = Header Size + Index * Element Size
    instrs.extend(
        [
            WasmInstrConvOp("i32.wrap_i64"),
            WasmInstrConst("i32", elemSize),
            WasmInstrNumBinOp("i32", "mul"),
            WasmInstrConst("i32", 4),
            WasmInstrNumBinOp("i32", "add"),
            WasmInstrNumBinOp("i32", "add"),
        ]
    )

    return instrs


def compileExp(e: exp, cfg: CompilerConfig) -> list[WasmInstr]:
    """Compiles an Lvar expression into Wasm instructions that leave the result on the stack."""

    match e:
        case AtomExp(BoolConst(n)):
            # Push an i32 constant onto the stack
            return [WasmInstrConst("i32", int(bool(n)))]

        case AtomExp(IntConst(n)):
            # Push an i64 constant onto the stack
            return [WasmInstrConst("i64", n)]

        case AtomExp(Name(name)):
            # Get the value of a local variable and push it onto the stack
            return [WasmInstrVarLocal("get", identToWasmId(name))]

        case UnOp(USub(), arg):
            # Compile unary negation (0 - arg)
            # 1. Compile the argument
            instrs = compileExp(arg, cfg)
            # 2. Prepend 0
            instrs.insert(0, WasmInstrConst("i64", 0))
            # 3. Subtract (stack is now: 0, arg_value)
            instrs.append(WasmInstrNumBinOp("i64", "sub"))
            return instrs

        case UnOp(Not(), arg):
            # Compile logical negation
            # 1. Compile the argument
            instrs = compileExp(arg, cfg)
            # 2. Prepend 0 (boolean)
            instrs.insert(0, WasmInstrConst("i32", 0))
            # 3. Apply equality compparison with 0
            instrs.append(WasmInstrIntRelOp("i32", "eq"))
            return instrs

        case BinOp(left, op, right):
            # Compile binary operations
            # 1. Compile left operand
            instrsLeft = compileExp(left, cfg)
            # 2. Compile right operand (stack: left_val, right_val)
            instrsRight = compileExp(right, cfg)
            # 3. Perform the operation for Numeric Binary Operation Instruction & Integer Relational Operation
            match op:
                # Arithmetic Ops (Int -> Int, use i64, result i64)
                case Add():
                    instr = WasmInstrNumBinOp("i64", "add")
                case Sub():
                    instr = WasmInstrNumBinOp("i64", "sub")
                case Mul():
                    instr = WasmInstrNumBinOp("i64", "mul")

                # Comparison Ops (Int -> Bool, use i64 comparison, result i32)
                case Less():
                    instr = WasmInstrIntRelOp("i64", "lt_s")
                case LessEq():
                    instr = WasmInstrIntRelOp("i64", "le_s")
                case Greater():
                    instr = WasmInstrIntRelOp("i64", "gt_s")
                case GreaterEq():
                    instr = WasmInstrIntRelOp("i64", "ge_s")

                # Equality Ops (Int -> Bool OR Bool -> Bool, use i64 or i32, result i32)
                case Is():
                    instr = WasmInstrIntRelOp("i32", "eq")
                case Eq():
                    # Create instruction for the correct type
                    instr = WasmInstrIntRelOp(tyToWasmValueType(tyOfExp(left)), "eq")
                case NotEq():
                    # create instruction for the correct type
                    instr = WasmInstrIntRelOp(tyToWasmValueType(tyOfExp(left)), "ne")
                case And():
                    # Short-circuiting And: left && right
                    ifInstr = WasmInstrIf(
                        "i32",
                        instrsRight,  # then block: if left is true, evaluate right
                        [
                            WasmInstrConst("i32", 0)
                        ],  # else block: if left is false, return 0
                    )
                    return instrsLeft + [ifInstr]
                case Or():
                    # short-circuiting Or: left || right
                    ifInstr = WasmInstrIf(
                        "i32",
                        [WasmInstrConst("i32", 1)],  # if left is true , result is 1
                        instrsRight,  # If left is false (0), result is right's value
                    )
                    return instrsLeft + [ifInstr]
            return instrsLeft + instrsRight + [instr]

        case ArrayInitDyn(lenExp, elemInit, ty):
            match utils.assertNotNone(ty):
                case NotVoid(t):
                    instrs = compileInitArray(lenExp, t, cfg)

                    instrs.extend(
                        [
                            WasmInstrVarLocal("tee", WasmId("$@tmp_i32")),
                            WasmInstrVarLocal("get", WasmId("$@tmp_i32")),
                            WasmInstrConst("i32", 4),  # header offset
                            WasmInstrNumBinOp("i32", "add"),
                            WasmInstrVarLocal("set", WasmId("$@tmp_i32")),
                        ]
                    )

                    blockLabel = WasmId(f"$while_block")
                    loopLabel = WasmId(f"$while_loop")

                    if isinstance(t, Array):
                        elemSize = tyToWasmValueSize(t.elemTy)
                        elemType = tyToWasmValueType(t.elemTy)
                    else:
                        raise Exception(
                            f"Compiler Error: 'elemTy' is not valid for type {t}"
                        )

                    loopBodyInstrs: list[WasmInstr] = [
                        WasmInstrVarLocal("get", WasmId("$@tmp_i32")),
                        WasmInstrVarGlobal("get", WasmId("$@free_ptr")),
                        WasmInstrIntRelOp("i32", "ge_u"),
                        # current >= end ? (result is i32: 1 or 0)
                        WasmInstrBranch(
                            target=blockLabel, conditional=True
                        ),  # Exit if true
                        # initialize element
                        WasmInstrVarLocal("get", WasmId("$@tmp_i32")),
                        *compileExp(AtomExp(elemInit), cfg),
                        WasmInstrMem(elemType, "store"),  # store value at address
                        # increment current address by element size
                        WasmInstrVarLocal("get", WasmId("$@tmp_i32")),
                        WasmInstrConst("i32", elemSize),
                        WasmInstrNumBinOp("i32", "add"),
                        WasmInstrVarLocal("set", WasmId("$@tmp_i32")),
                        WasmInstrBranch(
                            target=loopLabel, conditional=False
                        ),  # back to loop start
                    ]

                    loopInstr = WasmInstrLoop(loopLabel, loopBodyInstrs)
                    blockInstr = WasmInstrBlock(blockLabel, None, [loopInstr])

                    instrs.append(blockInstr)

                case Void():
                    raise Exception(f"Compiler Error")

            return instrs

        case ArrayInitStatic(elemInit, ty):
            match utils.assertNotNone(ty):
                case NotVoid(t):
                    instrs = compileInitArray(
                        IntConst(len(elemInit)), t, cfg
                    )  # Allocate space for array

                    if isinstance(t, Array):
                        elemSize = tyToWasmValueSize(t.elemTy)
                        elemType = tyToWasmValueType(t.elemTy)
                    else:
                        raise Exception(
                            f"Compiler Error: 'elemTy' is not valid for type {t}"
                        )

                    for index, elem in enumerate(elemInit):

                        # Offset = Header Size + Index * Element Size
                        offset = 4 + index * elemSize

                        instrs.extend(
                            [
                                WasmInstrVarLocal("tee", WasmId("$@tmp_i32")),
                                WasmInstrVarLocal("get", WasmId("$@tmp_i32")),
                                WasmInstrConst("i32", offset),
                                WasmInstrNumBinOp("i32", "add"),
                                *compileExp(AtomExp(elem), cfg),
                                WasmInstrMem(
                                    elemType, "store"
                                ),  # Store element at address
                            ]
                        )

                case Void():
                    raise Exception(f"Compiler Error")

            return instrs

        case Subscript(array, index):
            instrs: list[WasmInstr] = []

            if isinstance(array.ty, Array):
                elemType = tyToWasmValueType(array.ty.elemTy)
            else:
                raise Exception(f"Compiler Error")

            instrs.extend(
                arrayOffsetInstrs(array, index, cfg)
            )  # compute address of array[index]
            instrs.extend(
                [
                    WasmInstrMem(elemType, "load"),  # Load value from computed address
                ]
            )

            return instrs

        case Call(Ident("print"), [arg]):
            instrs = compileExp(arg, cfg)
            argTy = tyOfExp(arg)

            match argTy:
                case Int():
                    instrs.append(WasmInstrCall(WasmId("$print_i64")))  # Print integer
                case Bool():
                    instrs.append(WasmInstrCall(WasmId("$print_bool")))  # Print boolean
                case Array():
                    instrs.append(WasmInstrCall(WasmId("$print_i32")))  # Print array

            return instrs

        case Call(Ident("input_int"), []):
            # $input_i64 takes nothing, returns i64. It pushes a value.
            return [WasmInstrCall(WasmId("$input_i64"))]

        case Call(Ident("len"), [arg]):
            instrs = compileExp(arg, cfg)  # Stack: Array Base Address (i32)
            # expects the array's base address i32 to be on top of the stack and leave the i64 length value on the stack.
            instrs.extend(arrayLenInstrs())

            return instrs  # Return the instructions that compute and leave the length

        case _:
            raise Exception(f"Unsupported expression: {e}")
