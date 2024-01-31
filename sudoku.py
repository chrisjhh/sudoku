from typing import Generator, Callable, TypeAlias, TypeVar, TYPE_CHECKING
import curses
import time

import logging
logging.basicConfig(filename="sudoku_log", level=logging.INFO, filemode='w')

if TYPE_CHECKING:
    from curses import _CursesWindow

class PuzzleSolved(Exception):
    pass

class BadPuzzleState(Exception):
    pass

class LookAheadExceeded(Exception):
    pass

T = TypeVar('T')

def listify(itemOrList: T | list[T]) -> list[T]:
    try:
        return list(itemOrList)
    except TypeError:
        return [itemOrList]

class cell:

    def __init__(self) -> None:
        self.row: CellRow = None
        self.col: CellCol = None
        self.box: CellBox = None
        self.value: int = None
        self.potentialValues: list[int] = []
        self.drawPos = None 
        self.drawAtrr = 0
        self._snapshot = None

    def complete(self) -> bool:
        return self.value is not None
    
    def setValue(self, value:int):
        if self.value is not None:
            raise Exception("Value already set")
        self.value = value
        self.potentialValues = []
        for group in self.groups():
            group.completed += 1

        
    def groups(self) -> Generator['CellGroup', None, None]:
        if self.row is None:
            raise Exception("Cell is not in a row")
        yield self.row
        if self.col is None:
            raise Exception("Cell is not in a col")
        yield self.col
        if self.box is None:
            raise Exception("Cell is not in a box")
        yield self.box

    def isPotentialValue(self, value: int):
        for group in self.groups():
            if group.hasValue(value):
                return False
        return True
    
    def takeSnapshot(self):
        if self.complete():
            return
        self._snapshot = self.potentialValues[:]
        self.drawAtrr = curses.color_pair(3)

    def restoreSnapshot(self):
        if self._snapshot is None:
            return
        self.value = None
        self.potentialValues = self._snapshot[:]
        self._snapshot = None
        self.drawAtrr = 0

setCell: TypeAlias = Callable[[cell, int], None]
flashCellValues: TypeAlias = Callable[[cell | list[cell], int | list[int], int | list[int], float], None]

class CellGroup:

    def __init__(self, cells: list[cell]):
        self.cells = cells
        self.completed: int = len([x for x in cells if x.complete()])

    def complete(self) -> bool:
        if self.completed > 9:
            raise Exception("More than 9 completed cells in group!")
        return self.completed == 9
    
    def recomputeCompleted(self):
        self.completed = 0
        for cell in self:
            if cell.complete():
                self.completed += 1

    def __iter__(self):
        for cell in self.cells:
            yield cell

    def hasValue(self, value: int):
        for cell in self.cells:
            if cell.value == value:
                return True
        return False
    
    def processPotentials(self, setCell: setCell):
        logging.debug("Check group {}".format(self))
        for x in range(1,10):
            if self.hasValue(x):
                logging.debug("{} is already in the group".format(x))
                continue
            potentials = [c for c in self if x in c.potentialValues]
            logging.debug("{} could be in {} cells in this group".format(x, len(potentials)))
            if len(potentials) == 0:
                raise BadPuzzleState("There are no potentials for {}. This should not happen. {}".format(x, ", ".join([str(c.potentialValues) for c in self])))
            if len(potentials) == 1:
                logging.info("There is only one option for {} in {} so call setCell()".format(x,self))
                setCell(potentials[0], x)

    def findPairs(self, setCell: setCell, flashCellValues: flashCellValues):
        """We may not be able to pin a value to a unique cell, but if we have two numbers that can both only be
        in the same two cells then no other posibile values are valid for these two cells. This may help us
        pin down where the other numbers should be
        """
        pairs = []
        logging.debug("Finding pairs in group {}".format(self))
        for x in range(1,10):
            if self.hasValue(x):
                logging.debug("{} is already in the group".format(x))
                continue
            potentials = [c for c in self if x in c.potentialValues]
            logging.debug("{} could be in {} cells in this group".format(x, len(potentials)))
            if len(potentials) == 0:
                raise BadPuzzleState("There are no potentials for {}. This should not happen. {}".format(x, ", ".join([str(c.potentialValues) for c in self])))
            if len(potentials) == 2:
                logging.debug("We have found a pair")
                pairs.append((x, (potentials[0], potentials[1])))
        
        if len(pairs) > 1:
            logging.debug("We have some pairs. Check if any are the same")
            for p1 in pairs:
                (v1, cellPair1) = p1
                it = iter(pairs)
                p2 = next(it)
                while p2 != p1:
                    p2 = next(it)
                for p2 in it:
                    (v2, cellPair2) = p2
                    logging.debug("Comparing pairs for values {} and {}".format(v1, v2))
                    if cellPair1 == cellPair2:
                        logging.debug("They are the same")
                        logging.debug("Remove any possible values in these cells that are not the two values matched")
                        doneFlash = False
                        for cell in cellPair1:
                            
                            if len(cell.potentialValues) > 2:
                                if not doneFlash:
                                    # Flash the values we are using in cyan the first time they are used
                                    flashCellValues(cellPair1, (v1,v2), curses.color_pair(2), 0.4)
                                    doneFlash = True
                                logging.info("Adjusting possible values for pair of {} and {} in {}".format(v1, v2, self))
                                logging.info("Potential values before {}".format(cell.potentialValues))
                                cell.potentialValues = [v1, v2]
                                logging.info("Potential values after {}".format(cell.potentialValues))
                                # Process the effected groups
                                for group in cell.groups():
                                    if not group.complete():
                                        group.processPotentials(setCell)

    def findTriples(self, setCell: setCell, flashCellValues: flashCellValues):
        self.findGrouping(3, setCell, flashCellValues)


    def findGrouping(self, groupSize: int, setCell: setCell, flashCellValues: flashCellValues):
        """As with find pairs if we have three values that share the same three cells this must be exclusive to any other values
        """
        groupings = []
        logging.debug("Finding groups of {} in group {}".format(groupSize, self))
        for x in range(1,10):
            if self.hasValue(x):
                logging.debug("{} is already in the group".format(x))
                continue
            potentials = [c for c in self if x in c.potentialValues]
            logging.debug("{} could be in {} cells in this group".format(x, len(potentials)))
            if len(potentials) == 0:
                raise BadPuzzleState("There are no potentials for {}. This should not happen. {}".format(x, ", ".join([str(c.potentialValues) for c in self])))
            if len(potentials) == groupSize:
                logging.debug("We have found a group of {}".format(groupSize))
                groupings.append((x, potentials))
        
        if len(groupings) >= groupSize:
            logging.info("We have some groups of {} in {}. Check if any three are the same".format(groupSize, self))
            for t1 in groupings:
                (v1, cellGrouping1) = t1
                it = iter(groupings)
                t2 = next(it)
                while t2 != t1:
                    t2 = next(it)
                matched = []
                for t2 in it:
                    (v2, cellGrouping2) = t2
                    logging.info("Comparing groupings for values {} and {}".format(v1, v2))
                    if cellGrouping1 == cellGrouping2:
                        logging.info("They are the same")
                        matched.append(v2)
                        if len(matched) < groupSize - 1:
                            logging.info("Need to find more")
                        elif len(matched) == groupSize - 1:
                            logging.info("Found all groupings to make an exclusive set. Remove any other potential values")
                            doneFlash = False
                            for cell in cellGrouping1:
                                logging.info("Potential values before {}".format(cell.potentialValues))
                                if len(cell.potentialValues) > groupSize:
                                    if not doneFlash:
                                        # Flash the values we are using in cyan the first time they are used
                                        flashCellValues(cellGrouping1, [v1, *matched], curses.color_pair(2), 0.4)
                                        doneFlash = True
                                    cell.potentialValues = [v1, *matched]
                                    logging.info("Potential values after {}".format(cell.potentialValues))
                                    # Process the effected groups
                                    for group in cell.groups():
                                        if not group.complete():
                                            group.processPotentials(setCell)


class CellRow(CellGroup):

    def __init__(self, cells: list[cell]):
        super().__init__(cells)
        for cell in cells:
            cell.row = self


class CellCol(CellGroup):

    def __init__(self, cells: list[cell]):
        super().__init__(cells)
        for cell in cells:
            cell.col = self

def inSameRow(cells: list[cell]) -> bool:
    lastRow = None
    for cell in cells:
        if lastRow is not None and cell.row != lastRow:
            return False
        lastRow = cell.row
    return True

def inSameCol(cells: list[cell]) -> bool:
    lastCol = None
    for cell in cells:
        if lastCol is not None and cell.col != lastCol:
            return False
        lastCol = cell.col
    return True

class CellBox(CellGroup):

    def __init__(self, cells: list[cell]):
        super().__init__(cells)
        for cell in cells:
            cell.box = self

    def findRowsAndCols(self, setCell, flashCellValues):
        """We may not be able to pin a value to a unique cell, but if all the possible cells for a value in a box
        occur in the same row or column, then we can use this fact to eliminate this value as a possibility in
        the cells of the same row or column in the other boxes.
        """
        logging.debug("Check for values in the same row or column in box {}".format(self))
        for x in range(1,10):
            if self.hasValue(x):
                logging.debug("{} is already in the box".format(x))
                continue
            potentialCells = [c for c in self if x in c.potentialValues]
            logging.debug("{} could be in {} cells in this group".format(x, len(potentialCells)))
            if len(potentialCells) == 0:
                raise BadPuzzleState("There are no potentials for {}. This should not happen. {}".format(x, ", ".join([str(c.potentialValues) for c in self])))
            groupToUpdate = None
            if len(potentialCells) <= 3:
                logging.debug("Check if these cells are in the same row or column")
                if inSameRow(potentialCells):
                    logging.info("Cells for value {} in {} are all in the same row.".format(x, self))
                    logging.debug("Update the potential value for the other cells in this row")
                    groupToUpdate = potentialCells[0].row
                elif inSameCol(potentialCells):
                    logging.info("Cells for value {} in {} are all in the same column.".format(x, self))
                    logging.debug("Update the potential value for the other cells in this column")
                    groupToUpdate = potentialCells[0].col
            if groupToUpdate is not None:
                doneFlash = False
                for cell in groupToUpdate:
                    if cell.box == self:
                        # Only want to update the potential values in the other boxes
                        continue
                    if cell.complete():
                        continue
                    if x in cell.potentialValues:
                        if not doneFlash:
                            # Flash the values we are using in red the first time they are used
                            flashCellValues(potentialCells, x, curses.color_pair(1), 0.4)
                            doneFlash = True
                        logging.info("Potential values before {}".format(cell.potentialValues))
                        cell.potentialValues.remove(x)
                        logging.info("Potential values after {}".format(cell.potentialValues))
                        if len(cell.potentialValues) == 0:
                            raise BadPuzzleState("Cell has no remaining potential values")
                        if len(cell.potentialValues) == 1:
                            logging.info("Only one potential value left. Call setCell() with this value: {}".format(cell.potentialValues[0]))
                            setCell(cell, cell.potentialValues[0])
                        else:
                            # Process the effected groups
                            for group in cell.groups():
                                if not group.complete():
                                    group.processPotentials(setCell)



class sudoku:

    def __init__(self) -> None:
        self.cells: list[list[cell]] = []
        for i in range(9):
            row: list[cell] = []
            for j in range(9):
                row.append(cell())
            self.cells.append(row)
        # Create the rows
        self.rows: list[CellRow] = []
        for i in range(9):
            self.rows.append(CellRow(self.cells[i]))
        # Create the cols
        self.cols: list[CellCol] = []
        for i in range(9):
            colCells = [row[i] for row in self.cells]
            self.cols.append(CellCol(colCells))
        # Create the boxes
        self.boxes: list[CellBox] = []
        indexes = [[0,1,2], [3,4,5], [6,7,8]]
        for i in range(3):
            for j in range(3):
                boxCells: list[cell] = []
                for y in indexes[i]:
                    row = self.cells[y]
                    for x in indexes[j]:
                        boxCells.append(row[x])
                self.boxes.append(CellBox(boxCells))
        # For drawing
        self.window: '_CursesWindow' = None
        # To check if we are stuck
        self.foundThisPass: int = 0

    def load(self, puzzleData: str):
        lines = [line for line in puzzleData.splitlines() if len(line) > 0 and not '-' in line]
        if len(lines) != 9:
            raise Exception("Unexpected number of lines. Expect 9 got {}".format(len(lines)))
        for i in range(9):
            row = self.cells[i]
            chars = [c for c in lines[i] if c != '|']
            if len(chars) != 9:
                raise Exception("Unexpected number of chars. Expected 9 got [{}]".format(lines[i]))
            for j in range(9):
                if chars[j] != " ":
                    row[j].setValue(int(chars[j]))
                    row[j].drawAtrr = curses.A_BOLD

    def draw(self, window: '_CursesWindow'):
        window.clear()
        curses.curs_set(False)
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        width = (3 + 4) * 3 + 4
        gap = int((curses.COLS - width) / 2)
        dashRow = "-" * width
        start = 2
        y = start
        nRow = 0
        for row in self.cells:
            if nRow % 3 == 0:
                window.addstr(y, gap, dashRow)
                y += 1
            for j in range(4):
                window.addch(y, gap + j*8, "|")
            offset = gap + 2
            n = 0
            for cell in row:
                if cell.complete():
                    window.addstr(y, offset, str(cell.value), cell.drawAtrr)
                cell.drawPos = (y, offset)
                offset += 2
                n += 1
                if n % 3 == 0:
                    offset += 2
            y += 1
            nRow += 1
        window.addstr(y, gap, dashRow)

    def flashCellValues(self, cells: cell | list[cell], values: int | list[int] = None, attrs: int | list[int] = None, delay: float = 0.2):
        attrList = listify(attrs) if attrs is not None else [None]
        valList = listify(values) if values is not None else [None]
        cellList = listify(cells)
        pause = delay / (len(attrList) * len(valList))
        for attr in attrList:
            for val in valList:
                for cell in cellList:
                    v = val
                    if v is None:
                        v = cell.value
                        if v is None:
                            v = " "
                    if attr is None:
                        attr = curses.A_REVERSE | cell.drawAtrr
                    self.window.addstr(cell.drawPos[0], cell.drawPos[1], str(v), attr)
                self.window.refresh()
                time.sleep(pause)
        # Put cells back as they were
        for cell in cellList:
            v = cell.value
            if v is None:
                v = " "
            self.window.addstr(cell.drawPos[0], cell.drawPos[1], str(v), cell.drawAtrr)
        self.window.refresh()        




        
    
    def solved(self):
        for row in self.rows:
            if not row.complete():
                return False
        return True
    
    def setCell(self, cell:cell, value: int):
        logging.info("setCell: value={}".format(value))
        if not cell.isPotentialValue(value):
            raise BadPuzzleState("Trying to set value for a cell that is not allowed")
        cell.setValue(value)
        self.flashCellValues(cell)
        self.foundThisPass += 1
        if hasattr(self, "_inPreview") and hasattr(self, "_lookahead") and hasattr(self, "_foundThisPass"):
            if self.foundThisPass - self._foundThisPass > self._lookahead:
                raise LookAheadExceeded()
        if self.solved():
            logging.info("Puzzle solved after setCell")
            raise PuzzleSolved()
        # Remove this value as a potential value from the cells groups
        toSet: list[cell] = []
        for group in cell.groups():
            logging.debug("Removing potential value from cells in {}".format(group))
            if group.complete():
                logging.debug("group is complete skipping")
                continue
            for cell in group:
                if cell.complete():
                    continue
                if value in cell.potentialValues:
                    logging.info("Potential values before {}".format(cell.potentialValues))
                    cell.potentialValues.remove(value)
                    logging.info("Potential values after {}".format(cell.potentialValues))
                    if len(cell.potentialValues) == 0:
                        raise BadPuzzleState("Number of potential values for a cell has reached zero")
                    if len(cell.potentialValues) == 1:
                        logging.info("Only one potential value left {}. Add to list of cells to set".format(cell.potentialValues[0]))
                        # Set this cell, but only after we have finished updating the potential values of the other cells
                        toSet.append(cell)
        # Now update the other cells that now have only one potential value left
        if len(toSet) > 0:
            logging.info("Process list of new cells to set that now have only one potential value")
            for cell in toSet:
                if cell.complete():
                    # Already set as a consequence of a previous setCell
                    continue
                self.setCell(cell, cell.potentialValues[0])
        # Process the effected groups
        for group in cell.groups():
            if not group.complete():
                group.processPotentials(self.setCell)
        logging.info("End of setCell()")

    def groups(self):
        for r in self.rows:
            yield r
        for c in self.cols:
            yield c
        for b in self.boxes:
            yield b

    def startPreview(self):
        self._foundThisPass = self.foundThisPass
        for row in self.cells:
            for cell in row:
                cell.takeSnapshot()
        self._inPreview = True
        self._lookahead = 10

    def endPreview(self):
        if not hasattr(self, "_inPreview"):
            return
        delattr(self, "_inPreview")
        delattr(self, "_lookahead")

        for row in self.cells:
            for cell in row:
                cell.restoreSnapshot()
                if not cell.complete():
                    self.window.addstr(cell.drawPos[0], cell.drawPos[1], " ")
        self.window.refresh()
        for group in self.groups():
            # Need to revert completed count
            group.recomputeCompleted()
        if hasattr(self,"_foundThisPass"):
            self.foundThisPass = self._foundThisPass
            delattr(self, "_foundThisPass")

    def trialValue(self, cell: cell, value: int) -> bool:
        logging.info("Trialing {} in {}".format(value, cell))
        self.startPreview()
        initialCount = self.foundThisPass
        try:
            self.setCell(cell, value)
        except LookAheadExceeded:
            pass
        except PuzzleSolved:
            # Do it for real!
            self.endPreview()
            self.setCell(cell, value)
        except BadPuzzleState:
            # Remove this value from potentials
            self.endPreview()
            logging.info("{} is not a potential for {} within lookahead".format(value, cell))
            cell.potentialValues.remove(value)
            if len(cell.potentialValues) == 0:
                raise BadPuzzleState("No remaining potential values")
            for group in cell.groups():
                group.processPotentials(self.setCell)
            return True
                
        
        self.endPreview()
        logging.info("End of trial")
        return False

    def tryAllValues(self):
        for row in self.cells:
            for cell in row:
                if cell.complete():
                    continue
                # Take copy
                trialValues = cell.potentialValues[:]
                #trialValues.reverse()
                for val in trialValues:
                    doneSomething = self.trialValue(cell, val)
                    if doneSomething:
                        return
                   


    def solve(self):
        # Set the potential values
        logging.info("Set the inital potential values")
        initiallySolved = []
        for row in self.cells:
            for cell in row:
                if cell.complete():
                    continue
                cell.potentialValues = [x for x in range(1,10) if cell.isPotentialValue(x)]
                if len(cell.potentialValues) == 1:
                    # Solve this but only once we have finished the initialisation
                    initiallySolved.append((cell, cell.potentialValues[0]))
        # Process the cells already solved
        logging.info("Process initially solved cells")
        for (cell, value) in initiallySolved:
            self.setCell(cell, value)
        logging.info("Process the groups")
        for x in range(10):
            logging.info("--- pass {} ---".format(x))
            self.foundThisPass = 0
            for group in self.groups():
                group.processPotentials(self.setCell)
            if self.foundThisPass == 0:
                # We need a bit of extra help
                # Look at the boxes to see if any values must be in certain rows or columns
                for box in self.boxes:
                    box.findRowsAndCols(self.setCell, self.flashCellValues) 
            if self.foundThisPass == 0:
                # Even more help required
                # Look for matching pairs that will exclude other posibilities
                for group in self.groups():
                    group.findPairs(self.setCell, self.flashCellValues)
            if self.foundThisPass == 0:
                # Getting desperate
                # Look for triples
                for group in self.groups():
                    group.findTriples(self.setCell, self.flashCellValues)
            if self.foundThisPass == 0:
                # Look for quadrupoles
                for group in self.groups():
                    group.findGrouping(4, self.setCell, self.flashCellValues)
            if self.foundThisPass == 0:
                # Look for quintuples
                for group in self.groups():
                    group.findGrouping(5, self.setCell, self.flashCellValues)
            if self.foundThisPass == 0:
                # Look for sextuples
                for group in self.groups():
                    group.findGrouping(6, self.setCell, self.flashCellValues)
            if self.foundThisPass == 0:
                # Look for sexptuples
                for group in self.groups():
                    group.findGrouping(7, self.setCell, self.flashCellValues)
            if self.foundThisPass == 0:
                # Look for octuples
                for group in self.groups():
                    group.findGrouping(8, self.setCell, self.flashCellValues)
            if self.foundThisPass == 0:
                # Last resort
                self.tryAllValues()

            #if self.foundThisPass == 0:
            # We are stuck!
            #    break
        logging.info("Stuck!")
        

if __name__ == "__main__":
    from curses import wrapper
    from .data import hardest_puzzle as puzzle

    def main(window: '_CursesWindow'):
        su = sudoku()
        su.window = window
        su.load(puzzle)
        su.draw(window)

        text = "Any key to start"
        y = 16
        x = int(curses.COLS/2 - len(text)/2)
        window.addstr(y, x, text)

        window.getch()
        window.addstr(y, x, text, curses.A_REVERSE)
        window.refresh()
        time.sleep(0.2)
        window.addstr(y, x, text)
        window.refresh()
        time.sleep(0.1)
        window.addstr(y, x, " " * len(text))
        window.refresh()               

        try:
            su.solve()
        except PuzzleSolved:
            pass

        if su.solved():
            text = "Solved!"
        else:
            text = "Stuck! :("
        x = int(curses.COLS/2 - len(text)/2)
        window.addstr(y, x, text)

        window.getch()

    wrapper(main)




                 

        