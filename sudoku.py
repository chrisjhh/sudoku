from typing import Generator, TYPE_CHECKING
import curses
import time

import logging
logging.basicConfig(filename="sudoku_log", level=logging.INFO, filemode='w')

if TYPE_CHECKING:
    from curses import _CursesWindow

class PuzzleSolved(Exception):
    pass


class cell:

    def __init__(self) -> None:
        self.row: CellRow = None
        self.col: CellCol = None
        self.box: CellBox = None
        self.value: int = None
        self.potentialValues: list[int] = []
        self.drawPos = None 
        self.drawAtrr = 0

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


class CellGroup:

    def __init__(self, cells: list[cell]):
        self.cells = cells
        self.completed: int = len([x for x in cells if x.complete()])

    def complete(self) -> bool:
        return self.completed == 9

    def __iter__(self):
        for cell in self.cells:
            yield cell

    def hasValue(self, value: int):
        for cell in self.cells:
            if cell.value == value:
                return True
        return False
    
    def processPotentials(self, setCell):
        logging.debug("Check group {}".format(self))
        for x in range(1,10):
            if self.hasValue(x):
                logging.debug("{} is already in the group".format(x))
                continue
            potentials = [c for c in self if x in c.potentialValues]
            logging.debug("{} could be in {} cells in this group".format(x, len(potentials)))
            if len(potentials) == 0:
                raise Exception("There are no potentials for {}. This should not happen. {}".format(x, ", ".join([str(c.potentialValues) for c in self])))
            if len(potentials) == 1:
                logging.info("There is only one option for {} in {} so call setCell()".format(x,self))
                setCell(potentials[0], x)

    def findPairs(self, setCell, window: '_CursesWindow'):
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
                raise Exception("There are no potentials for {}. This should not happen. {}".format(x, ", ".join([str(c.potentialValues) for c in self])))
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
                                    for c in cellPair1:
                                        window.addstr(c.drawPos[0], c.drawPos[1], str(v1), curses.color_pair(2))
                                    window.refresh()
                                    time.sleep(0.4)
                                    for c in cellPair1:
                                        window.addstr(c.drawPos[0], c.drawPos[1], str(v2), curses.color_pair(2))
                                    window.refresh()
                                    time.sleep(0.4)
                                    for c in cellPair1:
                                        window.addstr(c.drawPos[0], c.drawPos[1], " ")
                                    window.refresh()
                                    doneFlash = True
                                logging.info("Adjusting possible values for pair of {} and {} in {}".format(v1, v2, self))
                                logging.info("Potential values before {}".format(cell.potentialValues))
                                cell.potentialValues = [v1, v2]
                                logging.info("Potential values after {}".format(cell.potentialValues))
                                # Process the effected groups
                                for group in cell.groups():
                                    if not group.complete():
                                        group.processPotentials(setCell)

    def findTriples(self, setCell, window: '_CursesWindow'):
        """As with find pairs if we have three values that share the same three cells this must be exclusive to any other values
        """
        triples = []
        logging.debug("Finding triples in group {}".format(self))
        for x in range(1,10):
            if self.hasValue(x):
                logging.debug("{} is already in the group".format(x))
                continue
            potentials = [c for c in self if x in c.potentialValues]
            logging.debug("{} could be in {} cells in this group".format(x, len(potentials)))
            if len(potentials) == 0:
                raise Exception("There are no potentials for {}. This should not happen. {}".format(x, ", ".join([str(c.potentialValues) for c in self])))
            if len(potentials) == 3:
                logging.debug("We have found a triple")
                triples.append((x, (potentials[0], potentials[1], potentials[2])))
        
        if len(triples) > 2:
            logging.info("We have some triples in {}. Check if any three are the same".format(self))
            for t1 in triples:
                (v1, cellTriple1) = t1
                it = iter(triples)
                t2 = next(it)
                while t2 != t1:
                    t2 = next(it)
                matched = []
                for t2 in it:
                    (v2, cellTriple2) = t2
                    logging.info("Comparing pairs for values {} and {}".format(v1, v2))
                    if cellTriple1 == cellTriple2:
                        logging.info("They are the same")
                        matched.append(v2)
                        if len(matched) == 1:
                            logging.info("Need to find one more")
                        elif len(matched) == 2:
                            logging.info("Found all three to make an exclusive triple. Remove any other potential values")
                            doneFlash = False
                            for cell in cellTriple1:
                                logging.info("Potential values before {}".format(cell.potentialValues))
                                if len(cell.potentialValues) > 3:
                                    if not doneFlash:
                                        # Flash the values we are using in cyan the first time they are used
                                        for c in cellTriple1:
                                            window.addstr(c.drawPos[0], c.drawPos[1], str(v1), curses.color_pair(2))
                                        window.refresh()
                                        time.sleep(0.4)
                                        for c in cellTriple1:
                                            window.addstr(c.drawPos[0], c.drawPos[1], str(matched[0]), curses.color_pair(2))
                                        window.refresh()
                                        time.sleep(0.4)
                                        for c in cellTriple1:
                                            window.addstr(c.drawPos[0], c.drawPos[1], str(matched[1]), curses.color_pair(2))
                                        window.refresh()
                                        time.sleep(0.4)
                                        for c in cellTriple1:
                                            window.addstr(c.drawPos[0], c.drawPos[1], " ")
                                        window.refresh()
                                        doneFlash = True
                                    cell.potentialValues = [v1, matched[0], matched[1]]
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

    def findRowsAndCols(self, setCell, window: '_CursesWindow'):
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
                raise Exception("There are no potentials for {}. This should not happen. {}".format(x, ", ".join([str(c.potentialValues) for c in self])))
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
                            for c in potentialCells:
                                window.addstr(c.drawPos[0], c.drawPos[1], str(x), curses.color_pair(1))
                            window.refresh()
                            time.sleep(0.4)
                            for c in potentialCells:
                                window.addstr(c.drawPos[0], c.drawPos[1], " ")
                            window.refresh()
                            doneFlash = True
                        logging.info("Potential values before {}".format(cell.potentialValues))
                        cell.potentialValues.remove(x)
                        logging.info("Potential values after {}".format(cell.potentialValues))
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
    
    def solved(self):
        for row in self.rows:
            if not row.complete():
                return False
        return True
    
    def setCell(self, cell:cell, value: int):
        logging.info("setCell: value={}".format(value))
        cell.setValue(value)
        self.window.addstr(cell.drawPos[0], cell.drawPos[1], str(cell.value), curses.A_REVERSE)
        self.window.refresh()
        time.sleep(0.2)
        self.window.addstr(cell.drawPos[0], cell.drawPos[1], str(cell.value))
        self.window.refresh()
        self.foundThisPass += 1
        if self.solved():
            logging.info("Puzzle solved after setCell")
            raise PuzzleSolved()
        # Remove this value as a potential value from the cells groups
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
                    if len(cell.potentialValues) == 1:
                        logging.info("Only one potential value left. Call setCell() with this value: {}".format(cell.potentialValues[0]))
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
                    box.findRowsAndCols(self.setCell, self.window) 
            if self.foundThisPass == 0:
                # Even more help required
                # Look for matching pairs that will exclude other posibilities
                for group in self.groups():
                    group.findPairs(self.setCell, self.window)
            if self.foundThisPass == 0:
                # Getting desperate
                # Look for triples
                for group in self.groups():
                    group.findTriples(self.setCell, self.window)
            #if self.foundThisPass == 0:
            # We are stuck!
            #    break
        logging.info("Stuck!")
        

if __name__ == "__main__":
    from curses import wrapper
    from .data import harder_puzzle as puzzle

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




                 

        