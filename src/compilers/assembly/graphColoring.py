from assembly.common import *
import assembly.tac_ast as tac
from common.prioQueue import PrioQueue

#! I added comments throughout the code to explain my thought process and understanding.


def chooseColor(x: tac.ident, forbidden: set[int]) -> int:
    """
    Returns the lowest possible color for variable x that is not forbidden for x.
    """
    color = 0
    while True:
        if color not in forbidden:
            return color  # first free color found
        color += 1  # try next color


def colorInterfGraph(
    g: InterfGraph,
    secondaryOrder: dict[tac.ident, int] = {},
    maxRegs: int = MAX_REGISTERS,
) -> RegisterMap:
    """
    Given an interference graph, computes a register map mapping a TAC variable
    to a TACspill variable. You have to implement the "simple graph coloring algorithm"
    from slide 58 here.

    - Parameter maxRegs is the maximum number of registers we are allowed to use.
    - Parameter secondaryOrder is used by the tests to get deterministic results even
      if two variables have the same number of forbidden colors.
    """

    colors: dict[tac.ident, int] = {}  # final colors
    wPrioQueue = PrioQueue[tac.ident](secondaryOrder=secondaryOrder)  # worklist
    allVertices: list[tac.ident] = list(g.vertices)  # all variables
    uncoloredNodes: set[tac.ident] = set(allVertices)  # initially all uncolored

    for node in uncoloredNodes:
        wPrioQueue.push(node, 0)  # start with zero priority

    while not wPrioQueue.isEmpty():
        node = wPrioQueue.pop()  # pick next node
        uncoloredNodes.remove(node)  # mark as colored

        curForbidden: set[int] = set()  # collect neighbor colors
        for neighborOfNode in g.succs(node):
            if neighborOfNode in colors:
                curForbidden.add(colors[neighborOfNode])

        color = chooseColor(node, curForbidden)  # get color

        colors[node] = color

        for neighborOfNode in g.succs(node):
            if neighborOfNode in uncoloredNodes:  # update only uncolored

                isNewlyForbidden = True
                for neighborOfNeighbor in g.succs(neighborOfNode):
                    if neighborOfNeighbor in colors and neighborOfNeighbor != node:
                        if colors[neighborOfNeighbor] == color:
                            isNewlyForbidden = False  # not a new conflict
                            break

                if isNewlyForbidden:
                    try:
                        wPrioQueue.incPrio(neighborOfNode, 1)  # bump priority
                    except ValueError:
                        pass  # skip if already processed

    m = RegisterAllocMap(colors, maxRegs)
    return m
