from assembly.common import *
from assembly.graph import Graph
import assembly.tac_ast as tac

#! I added comments throughout the code to explain my thought process and understanding.


def isSpecialVar(v: tac.ident) -> bool:
    """Check if a variable is special/precolored."""
    return v.name.startswith("%")  # special vars start with %


def primUse(p: tac.prim) -> set[tac.ident]:
    """Get used identifiers from a primitive."""
    match p:
        case tac.Name(var=var):
            return {var} # variable is used
        case tac.Const():
            return set() # constants use nothing


def expUse(e: tac.exp) -> set[tac.ident]:
    """Get used identifiers from an expression."""
    match e:
        case tac.Prim(p=p):
            return primUse(p) # delegate to primUse
        case tac.BinOp(left=left, right=right):
            return primUse(left).union(primUse(right)) # both sides used


def instrDef(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers defined by some instrucution.
    """
    
    match instr:
        case tac.Assign(var=var):
            return {var} # assigned var is defined
        case tac.Call(var=var) if var is not None:
            return {var} # return value var is defined
        case _:
            return set() # other instructions define nothing


def instrUse(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers used by some instrucution.
    """
    
    match instr:
        case tac.Assign(right=right):
            return expUse(right) # use in right expression
        case tac.Call(args=args):
            used: set[tac.ident] = set()
            for argPrim in args:
                used.update(primUse(argPrim)) # all call args used
            return used
        case tac.GotoIf(test=test):
            return primUse(test)  # condition is used
        case _:
            return set()  # others use nothing


# Each individual instruction has an identifier. This identifier is the tuple
# (index of basic block, index of instruction inside the basic block)
type InstrId = tuple[int, int]


class InterfGraphBuilder:
    def __init__(self):
         # self.before holds, for each instruction I, to set of variables live before I.
        self.before: dict[InstrId, set[tac.ident]] = {}
         # self.after holds, for each instruction I, to set of variables live after I.
        self.after: dict[InstrId, set[tac.ident]] = {}

    def liveStart(self, bb: BasicBlock, s: set[tac.ident]) -> set[tac.ident]:
        """
        Given a set of variables s and a basic block bb, liveStart computes
        the set of variables live at the beginning of bb, assuming that s
        are the variables live at the end of the block.

        Essentially, you have to implement the subalgorithm "Computing L_start" from
        slide 46 here. You should update self.after and self.before while traversing
        the instructions of the basic block in reverse.
        """
        
        curLiveAfter = s # start from known end
        bbId = bb.index

        for k in reversed(range(len(bb.instrs))): # walk backwards
            instr = bb.instrs[k]
            instrId: InstrId = (bbId, k)

            self.after[instrId] = curLiveAfter # record live after
            definedByInstr = instrDef(instr)
            usedByInstr = instrUse(instr)
            liveBeforeInstr = (curLiveAfter - definedByInstr).union(
                usedByInstr
            )
            self.before[instrId] = liveBeforeInstr # record live before
            curLiveAfter = liveBeforeInstr # propagate
        return curLiveAfter 

    def liveness(self, g: ControlFlowGraph):
        """
        This method computes liveness information and fills the sets self.before and
        self.after.

        You have to implement the algorithm for computing liveness in a CFG from
        slide 46 here.
        """
        
        IN: dict[int, set[tac.ident]] = {} # live at block entry
        for bbId in g.vertices:
            IN[bbId] = set() # init empty

        changed = True
        while changed:
            changed = False
            sortedBB = sorted(list(g.vertices), reverse=True) # iterate blocks in reverse
            for bbId in sortedBB:
                bb = g.getData(bbId)
                OUT_B: set[tac.ident] = set()
                for succId in g.succs(bbId):  # collect successor IN sets
                    OUT_B.update(IN[succId])
                newInB = self.liveStart(bb, OUT_B) # recompute IN
                if newInB != IN[bbId]: # check for change
                    IN[bbId] = newInB
                    changed = True # need another round

    def __addEdgesForInstr(
        self, instrId: InstrId, instr: tac.instr, interfG: InterfGraph
    ):
        """
        Given an instruction and its ID, adds the edges resulting from the instruction
        to the interference graph.

        You should implement the algorithm specified on the slide
        "Computing the interference graph" (slide 50) here.
        """
        
        defVarsSet = instrDef(instr)
        if not defVarsSet:
            return # nothing defined

        x = list(defVarsSet)[0]
        if not interfG.hasVertex(x):
            return # skip

        isMove = False
        moveSourceVar: tac.ident | None = None
        if (
            isinstance(instr, tac.Assign)
            and isinstance(instr.right, tac.Prim)
            and isinstance(instr.right.p, tac.Name)
        ):
            isMove = True
            moveSourceVar = instr.right.p.var # check for move instr

        liveAfterInstr = self.after[
            instrId
        ]  # vars live after instr

        for y in liveAfterInstr:
            if y == x:  # skip self-edge
                continue

            if isMove and y == moveSourceVar:
                continue # skip move edge 

            if interfG.hasVertex(y):
                interfG.addEdge(x, y) # add edge if both are allocatable

    def build(self, g: ControlFlowGraph) -> InterfGraph:
        """
        This method builds the interference graph. It performs three steps:

        - Use liveness to fill the sets self.before and self.after.
        - Setup the interference graph as an undirected graph containing all variables
          defined or used by any instruction of any basic block. Initially, the
          graph does not have any edges.
        - Use __addEdgesForInstr to fill the edges of the interference graph.
        """
        
        self.liveness(g) # compute liveness

        interfG: InterfGraph = Graph(kind="undirected")  # init graph

        allocatableVars: set[tac.ident] = set()
        for bbId in g.vertices:
            bb = g.getData(bbId)
            for instr in bb.instrs:
                for vDef in instrDef(instr):
                    if not isSpecialVar(vDef):
                        allocatableVars.add(vDef)
                for v_use in instrUse(instr):
                    if not isSpecialVar(v_use):
                        allocatableVars.add(v_use)

        for var in allocatableVars: 
            interfG.addVertex(var, None) # add nodes

        for bbId in g.vertices:
            bb = g.getData(bbId)
            for k, instr in enumerate(bb.instrs):
                instrId: InstrId = (bbId, k)
                self.__addEdgesForInstr(instrId, instr, interfG) # add edges

        return interfG


def buildInterfGraph(g: ControlFlowGraph) -> InterfGraph:
    builder = InterfGraphBuilder()
    return builder.build(g) 
