import assembly.common as asTypes
import common.genericCompiler as genCompiler
import shell
import common.utils as utils
import common.log as log
import assembly.tac_ast as tac
import assembly.tacPretty as tacPretty
import common.testsupport as testsupport
import pytest
import assembly.controlFlow as controlFlow
import assembly.loopToTac as lt
from assembly.common import BasicBlock

pytestmark = pytest.mark.instructor

def test_instrDef():
    # We have to import these modules dynamically because they are not present in student code
    liveness = utils.importModuleNotInStudent('compilers.assembly.liveness')

    i1 = loopSrcToTac('y = 1\nx = y + 1')[-1]
    assert liveness.instrDef(i1) == set([tac.Ident('$x')]), f'i1={i1}'

    i2 = loopSrcToTac('a = input_int()')[-1]
    assert liveness.instrDef(i2) == set([tac.Ident('$a')]), f'i2={i2}'

    i3 = loopSrcToTac('print(42)')[-1]
    assert liveness.instrDef(i3) == set(), f'i3={i3}'

def test_instrUse():
    # We have to import these modules dynamically because they are not present in student code
    liveness = utils.importModuleNotInStudent('compilers.assembly.liveness')

    i1 = loopSrcToTac('y=1\nz=2\nx = y + z')[-1]
    assert liveness.instrUse(i1) == set([tac.Ident('$y'), tac.Ident('$z')]), f'i1={i1}'

    i2 = loopSrcToTac('z=1\nprint(z)')[-1]
    assert liveness.instrUse(i2) == set([tac.Ident('$z')]), f'i2={i2}'

    i3 = loopSrcToTac('print(42)')[-1]
    assert liveness.instrUse(i3) == set(), f'i3={i3}'

    i4 = tac.GotoIf(tac.Name(tac.Ident('x')), 'some_label')
    assert liveness.instrUse(i4) == set([tac.Ident('x')]), f'i4={i4}'

def mkName(x: str) -> tac.prim:
    return tac.Name(tac.Ident(x))

def mkConst(n: int) -> tac.prim:
    return tac.Const(n)

def test_liveStart():
    # LIVE: a, n
    # res = 1
    # n = n - 1
    # LIVE: res, n, a
    instrs: list[tac.instr] = [
        tac.Assign(tac.Ident('res'), tac.Prim(mkConst(1))),
        tac.Assign(tac.Ident('n'), tac.BinOp(mkName('n'), tac.Op('MUL'), mkConst(1)))
    ]
    bb = BasicBlock(0, [], instrs)
    # We have to import these modules dynamically because they are not present in student code
    liveness = utils.importModuleNotInStudent('compilers.assembly.liveness')
    builder = liveness.InterfGraphBuilder()
    liveAtStart = builder.liveStart(bb, set([tac.Ident('res'), tac.Ident('n'), tac.Ident('a')]))
    assert liveAtStart == set([tac.Ident('n'), tac.Ident('a')])

def test_computeLiveness():
    tacInstrs = loopSrcToTac(src3)
    ctrlFlowG = controlFlow.buildControlFlowGraph(tacInstrs)
    # We have to import these modules dynamically because they are not present in student code
    liveness = utils.importModuleNotInStudent('compilers.assembly.liveness')
    builder = liveness.InterfGraphBuilder()
    builder.liveness(ctrlFlowG)
    expectedBefore: dict[tuple[int, int], set[tac.ident]] = {
        (1, 1): set(),
        (1, 0): {tac.Ident(name='$a')},
        (2, 0): set(),
        (0, 3): {tac.Ident(name='$a'), tac.Ident(name='$c')},
        (0, 2): {tac.Ident(name='$a'), tac.Ident(name='$b')},
        (0, 1): {tac.Ident(name='$a')},
        (0, 0): set()
    }
    expectedAfter: dict[tuple[int, int], set[tac.ident]] = {
        (1, 1): set(),
        (1, 0): set(),
        (2, 0): set(),
        (0, 3): {tac.Ident(name='$a')},
        (0, 2): {tac.Ident(name='$a'), tac.Ident(name='$c')},
        (0, 1): {tac.Ident(name='$a'), tac.Ident(name='$b')},
        (0, 0): {tac.Ident(name='$a')}
    }
    assert builder.before == expectedBefore
    assert builder.after == expectedAfter

def loopToTac(args: genCompiler.Args) -> list[tac.instr]:
    log.debug(f'Compiling to TAC')
    tacInstrs = lt.loopToTac(args)
    log.debug(f'TAC:\n{tacPretty.prettyInstrs(tacInstrs)}')
    return tacInstrs

def loopSrcToTac(src: str) -> list[tac.instr]:
    with shell.tempDir() as d:
        srcFile = shell.pjoin(d, "input.py")
        outFile = shell.pjoin(d, "out.wasm")
        utils.writeTextFile(srcFile, src)
        args = genCompiler.Args(srcFile, outFile)
        return loopToTac(args)


def buildInterfGraph(tacInstrs: list[tac.instr]) -> asTypes.InterfGraph:
    # We have to import these modules dynamically because they are not present in student code
    liveness = utils.importModuleNotInStudent('compilers.assembly.liveness')
    log.debug(f'Building the control flow graph ...')
    ctrlFlowG = controlFlow.buildControlFlowGraph(tacInstrs)
    log.debug(f'Control flow graph: {ctrlFlowG}')
    log.debug(f'Building the interference graph ...')
    interfGraph = liveness.buildInterfGraph(ctrlFlowG)
    log.debug(f'Interference graph: {interfGraph}')
    return interfGraph

def interfGraphTest(src: str, expectedConflicts: list[tuple[str, str]]):
    l: list[tuple[str, str]] = expectedConflicts[:]
    for (x, y) in expectedConflicts:
        l.append((y, x))
    expectedConflicts = l
    interfGraph = buildInterfGraph(loopSrcToTac(src))
    realConflicts = [(x.name, y.name) for (x, y) in interfGraph.edges]
    for c in realConflicts:
        if c not in expectedConflicts:
            pytest.fail(f'Conflict {c} in interference graph was not expected. realConflicts={realConflicts}')
    for c in expectedConflicts:
        if c not in realConflicts:
            pytest.fail(f'Expected conflict {c} not in interference graph. realConflicts={realConflicts}')

src1 = """
n = input_int()
res = 1
c = n <= 0
while c:
    res = res * n
    n = n - 1
    c = n <= 0
print(res)
"""

# Control flow graph: see slide 39 (with slight variations)
src2 = """
n = input_int()
s = 0
i = 1
c = i < n
while c:
    t = i * i
    s = s + t
    i = i + 1
    c = i < n
print(s)
"""

# Control flow graph: see slide 38
src3 = """
a = input_int()
b = input_int()
c = b == 1
if c:
    print(0)
else:
    print(a)
"""

def test_interfGraph1():
    interfGraphTest(src1, [('$n', '$res'), ('$res', '$c'), ('$c', '$n')])

def test_interfGraph2():
    n = '$n'
    s = '$s'
    i = '$i'
    c = '$c'
    t = '$t'
    interfGraphTest(src2, [(c, n), (c, s), (c, i), (n, s), (n, i), (n, t), (i, s), (i, t), (s, t)])

def test_interfGraph3():
    interfGraphTest(src3, [('$a', '$b'), ('$a', '$c')])

@pytest.mark.parametrize("lang, srcFile",
                         testsupport.collectTestFiles(langOnly=['loop', 'var'], ignoreErrorFiles=True))
def test_interfGraph(lang: str, srcFile: str, tmp_path: str):
    outFile = shell.pjoin(tmp_path, "out.wasm")
    args = genCompiler.Args(srcFile, outFile)
    buildInterfGraph(loopToTac(args)) # make sure it does not fail
