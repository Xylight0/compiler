# AUTOMATICALLY GENERATED (2024-07-23 16:01:08)
from __future__ import annotations
from dataclasses import dataclass

type optional[T] = T | None

@dataclass(frozen=True)
class Ident:
    name: str

type ident = Ident
type string = str

@dataclass
class USub:
    pass

@dataclass
class Not:
    pass

type unaryop = USub | Not

@dataclass
class Add:
    pass

@dataclass
class Sub:
    pass

@dataclass
class Mul:
    pass

@dataclass
class Less:
    pass

@dataclass
class LessEq:
    pass

@dataclass
class Greater:
    pass

@dataclass
class GreaterEq:
    pass

@dataclass
class Eq:
    pass

@dataclass
class NotEq:
    pass

@dataclass
class Is:
    pass

@dataclass
class And:
    pass

@dataclass
class Or:
    pass

type binaryop = Add | Sub | Mul | Less | LessEq | Greater | GreaterEq | Eq | NotEq | Is | And | Or

@dataclass
class Int:
    pass

@dataclass
class Bool:
    pass

@dataclass
class Array:
    elemTy: ty

@dataclass
class Fun:
    params: list[ty]
    result: resultTy

@dataclass
class Class:
    name: ident

@dataclass
class Interface:
    name: ident

type ty = Int | Bool | Array | Fun | Class | Interface

@dataclass
class NotVoid:
    ty: ty

@dataclass
class Void:
    pass

type resultTy = NotVoid | Void

@dataclass
class Var:
    pass

@dataclass
class UserFun:
    pass

@dataclass
class BuiltinFun:
    pass

type scope = Var | UserFun | BuiltinFun

@dataclass
class FunParam:
    var: ident
    ty: ty

type funParam = FunParam

@dataclass
class IntConst:
    value: int
    ty: optional[resultTy] = None

@dataclass
class BoolConst:
    value: bool
    ty: optional[resultTy] = None

@dataclass
class Name:
    var: ident
    scope: optional[scope] = None
    ty: optional[resultTy] = None

@dataclass
class Call:
    fun: exp
    args: list[exp]
    ty: optional[resultTy] = None

@dataclass
class UnOp:
    op: unaryop
    arg: exp
    ty: optional[resultTy] = None

@dataclass
class BinOp:
    left: exp
    op: binaryop
    right: exp
    ty: optional[resultTy] = None

@dataclass
class ArrayInitDyn:
    len: exp
    elemInit: exp
    ty: optional[resultTy] = None

@dataclass
class ArrayInitStatic:
    elemInit: list[exp]
    ty: optional[resultTy] = None

@dataclass
class Subscript:
    array: exp
    index: exp
    ty: optional[resultTy] = None

@dataclass
class Closure:
    params: list[funParam]
    body: exp
    ty: optional[resultTy] = None

type exp = IntConst | BoolConst | Name | Call | UnOp | BinOp | ArrayInitDyn | ArrayInitStatic | Subscript | Closure

@dataclass
class StmtExp:
    exp: exp

@dataclass
class Assign:
    var: ident
    right: exp

@dataclass
class IfStmt:
    cond: exp
    thenBody: list[stmt]
    elseBody: list[stmt]

@dataclass
class WhileStmt:
    cond: exp
    body: list[stmt]

@dataclass
class SubscriptAssign:
    left: exp
    index: exp
    right: exp

@dataclass
class Return:
    result: optional[exp] = None

type stmt = StmtExp | Assign | IfStmt | WhileStmt | SubscriptAssign | Return

@dataclass
class FunDef:
    name: ident
    params: list[funParam]
    result: resultTy
    body: list[stmt]

type fun = FunDef

@dataclass
class FieldDecl:
    ty: ty
    name: ident

type fieldDecl = FieldDecl

@dataclass
class MethodSig:
    name: ident
    params: list[funParam]
    result: resultTy

type methodSig = MethodSig

@dataclass
class MethodDecl:
    sig: methodSig
    body: list[stmt]

type methodDecl = MethodDecl

@dataclass
class ClassDecl:
    name: ident
    extends: optional[ident]
    implements: list[ident]
    fields: list[fieldDecl]
    methods: list[methodDecl]

type classDecl = ClassDecl

@dataclass
class InterfaceDecl:
    name: ident
    methods: list[methodSig]

type interfaceDecl = InterfaceDecl

@dataclass
class Module:
    interfaces: list[interfaceDecl]
    classes: list[classDecl]
    funs: list[fun]
    stmts: list[stmt]

type mod = Module