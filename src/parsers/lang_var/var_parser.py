from lark import ParseTree
from lang_var.var_ast import *
from parsers.common import *

#! I added comments throughout the code to explain my thought process and understanding.


def parseTreeToExpAst(t: ParseTree) -> exp:
    match t.data:
        case "exp" | "exp1" | "exp2":
            return parseTreeToExpAst(
                asTree(t.children[0])
            )  # Recursive calll for nested expressions

        case "add" | "sub" | "mul":
            left, right = t.children[0], t.children[1]
            op = {"add": Add(), "sub": Sub(), "mul": Mul()}[t.data]
            return BinOp(
                left=parseTreeToExpAst(asTree(left)),
                op=op,
                right=parseTreeToExpAst(asTree(right)),
            )  # Create binary operation

        case "uminus":
            return UnOp(
                op=USub(), arg=parseTreeToExpAst(asTree(t.children[0]))
            )  # Unary minus operation

        case "const":
            return IntConst(value=int(asToken(t.children[0]).value))  # Constant integer

        case "var":
            return Name(
                name=Ident(name=asToken(t.children[0]).value)
            )  # Variable reference

        case "call":
            funcIdent = Ident(asToken(t.children[0]).value)
            argsAstList: list[exp] = []

            if len(t.children) > 1:
                argsTree = asTree(t.children[1])
                argsAstList = [
                    parseTreeToExpAst(asTree(child)) for child in argsTree.children
                ]

            return Call(name=funcIdent, args=argsAstList)  # Function call

        case _:
            raise ValueError(f"Unknown expression: {t.data}")


def parseTreeToStmtAst(t: ParseTree) -> stmt:
    match t.data:
        case "assign":
            var = Ident(name=asToken(t.children[0]).value)
            return Assign(
                var=var, right=parseTreeToExpAst(asTree(t.children[1]))
            )  # Assignment statement

        case "expr_stmt":
            return StmtExp(
                exp=parseTreeToExpAst(asTree(t.children[0]))
            )  # Expression statement

        case "stmt":
            return parseTreeToStmtAst(
                asTree(t.children[0])
            )  # recursive call for nested statement

        case _:
            raise ValueError(f"Unknown statement: {t.data}")


def parseTreeToStmtListAst(t: ParseTree) -> list[stmt]:
    return [
        parseTreeToStmtAst(asTree(child)) for child in t.children
    ]  # Convert statement list


def parseTreeToModuleAst(t: ParseTree) -> mod:
    return Module(
        stmts=parseTreeToStmtListAst(asTree(t.children[0]))
    )  # Module with statement list


def parseModule(args: ParserArgs) -> mod:
    parseTree = parseAsTree(args, "src/parsers/lang_var/var_grammar.lark", "lvar")
    return parseTreeToModuleAst(asTree(parseTree))  # Parse and return module
