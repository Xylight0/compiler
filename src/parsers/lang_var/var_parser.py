from lark import Token, Tree
from lang_var.var_ast import *
from parsers.common import *

#! I added comments throughout the code to explain my thought process and understanding.


def parseTreeToExpAst(t: Tree[Token] | Token) -> exp:
    match t.data:
        case "exp" | "exp1" | "exp2":
            return parseTreeToExpAst(
                t.children[0]
            )  # Recursive calll for nested expressions

        case "add" | "sub" | "mul":
            left, right = t.children[0], t.children[1]
            op = {"add": Add(), "sub": Sub(), "mul": Mul()}[t.data]
            return BinOp(
                left=parseTreeToExpAst(left), op=op, right=parseTreeToExpAst(right)
            )  # Create binary operation

        case "uminus":
            return UnOp(
                op=USub(), arg=parseTreeToExpAst(t.children[0])
            )  # Unary minus operation

        case "const":
            return IntConst(value=int(t.children[0].value))  # Constant integer

        case "var":
            return Name(name=Ident(name=t.children[0].value))  # Variable reference

        case "call":
            argsAst = (
                [parseTreeToExpAst(child) for child in t.children[1].children]
                if len(t.children) > 1
                else []
            )
            return Call(name=Ident(t.children[0].value), args=argsAst)  # Function call


def parseTreeToStmtAst(t: Tree[Token]) -> stmt:
    match t.data:
        case "assign":
            var = Ident(name=t.children[0].value)
            return Assign(
                var=var, right=parseTreeToExpAst(t.children[1])
            )  # Assignment statement
        case "expr_stmt":
            return StmtExp(exp=parseTreeToExpAst(t.children[0]))  # Expression statement
        case "stmt":
            return parseTreeToStmtAst(
                t.children[0]
            )  # recursive call for nested statement


def parseTreeToStmtListAst(t: Tree[Token]) -> list[stmt]:
    return [parseTreeToStmtAst(child) for child in t.children]  # Convert statement list


def parseTreeToModuleAst(t: Tree[Token]) -> mod:
    return Module(
        stmts=parseTreeToStmtListAst(t.children[0])
    )  # Module with statement list


def parseModule(args: ParserArgs) -> mod:
    parseTree = parseAsTree(args, "src/parsers/lang_var/var_grammar.lark", "lvar")
    return parseTreeToModuleAst(parseTree)  # Parse and return module
