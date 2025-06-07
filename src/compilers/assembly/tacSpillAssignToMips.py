import assembly.tacSpill_ast as tacSpill
import assembly.mips_ast as mips
from typing import *
from assembly.common import *
from assembly.mipsHelper import *
from common.compilerSupport import *

#! I added comments throughout the code to explain my thought process and understanding.


def primToReg(p: tacSpill.prim, tempReg: mips.reg) -> tuple[mips.reg, list[mips.instr]]:
    """Converts a tacSpill.prim to a MIPS register."""
    match p:
        case tacSpill.Name(var=name):
            return reg(name), []  #  just return register for variable
        case tacSpill.Const(value=val):
            return tempReg, [
                mips.LoadI(target=tempReg, value=imm(val))
            ]  # load constant into tempReg


def assignToMips(i: tacSpill.Assign) -> list[mips.instr]:
    """Translates a tacSpill.Assign instruction to MIPS instructions."""
    mipsInstr: list[mips.instr] = []
    target = reg(i.var)  # target register for assignment

    match i.right:
        case tacSpill.Prim(p=p):
            match p:
                case tacSpill.Const(value=val):
                    mipsInstr.append(
                        mips.LoadI(target=target, value=imm(val))
                    )  # load constant directly
                case tacSpill.Name(var=name):
                    src = reg(name)
                    if target.name != src.name:
                        mipsInstr.append(
                            mips.Move(target=target, source=src)
                        )  # move from source register

        case tacSpill.BinOp(op=opObj, left=leftPrim, right=rightPrim):
            opName = opObj.name

            regL, codeL = primToReg(leftPrim, reg(Regs.t0))
            mipsInstr.extend(codeL)  # prepare left operand register

            if opName in {"ADD", "LT_S"}:
                match rightPrim:
                    case tacSpill.Const(value=val):
                        opIMap = {"ADD": mips.AddI, "LT_S": mips.LessI}
                        mipsInstr.append(
                            mips.OpI(
                                opI=opIMap[opName](),
                                target=target,
                                left=regL,
                                right=imm(val),
                            )
                        )  # use immediate op if right is constant
                        return mipsInstr
                    case _:
                        pass

            regR, codeR = primToReg(rightPrim, reg(Regs.t1))
            mipsInstr.extend(codeR)  # prepare right operand register

            opMap = {
                "ADD": mips.Add,
                "SUB": mips.Sub,
                "MUL": mips.Mul,
                "LT_S": mips.Less,
                "EQ": mips.Eq,
                "NE": mips.NotEq,
                "GT_S": mips.Greater,
                "LE_S": mips.LessEq,
                "GE_S": mips.GreaterEq,
            }

            mipsInstr.append(
                mips.Op(
                    op=opMap[opName](),
                    target=target,
                    left=regL,
                    right=regR,
                )
            )  # perform binary operation with registers

    return mipsInstr
