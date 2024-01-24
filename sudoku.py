from typing import Generator, TYPE_CHECKING
import curses
import time

import logging
logging.basicConfig(filename="sudoku_log", level=logging.DEBUG)

if TYPE_CHECKING:
    from curses import _CursesWindow

class PuzzleSolved(Exception):
    pass


class cell:

    def __init__(self) -> None:
        self.row = None
        self.col = None
        self.box = None
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
                logging.debug("There is only one option so call setCell()")
                setCell(potentials[0], x)

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

class CellBox(CellGroup):

    def __init__(self, cells: list[cell]):
        super().__init__(cells)
        for cell in cells:
            cell.box = self


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

    def load(self, puzzleData: str):
        lines = [line for line in puzzleData.splitlines() if len(line) > 0 and not '-' in line]
        if len(lines) != 9:
            raise Exception("Unexpected number of lines. Expect 9 got {}".format(len(lines)))
        for i in range(9):
            row = self.cells[i]
            chars = [c for c in lines[i] if c != '|']
            if len(chars) != 9:
                raise Exception("Unexpected number of chars. Expected 9 got []".format(lines[i]))
            for j in range(9):
                if chars[j] != " ":
                    row[j].setValue(int(chars[j]))
                    row[j].drawAtrr = curses.A_BOLD

    def draw(self, window: '_CursesWindow'):
        window.clear()
        curses.curs_set(False)
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
        logging.debug("setCell: value={}".format(value))
        cell.setValue(value)
        self.window.addstr(cell.drawPos[0], cell.drawPos[1], str(cell.value), curses.A_REVERSE)
        self.window.refresh()
        time.sleep(0.2)
        self.window.addstr(cell.drawPos[0], cell.drawPos[1], str(cell.value))
        self.window.refresh()
        if self.solved():
            logging.debug("Puzzle solved after setCell")
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
                    logging.debug("Potential values before {}".format(cell.potentialValues))
                    cell.potentialValues.remove(value)
                    logging.debug("Potential values after {}".format(cell.potentialValues))
                    if len(cell.potentialValues) == 1:
                        logging.debug("Only one potential value left. Call setCell() with this value: {}".format(cell.potentialValues[0]))
                        self.setCell(cell, cell.potentialValues[0])
        # Process the effected groups
        for group in cell.groups():
            if not group.complete():
                group.processPotentials(self.setCell)

    def groups(self):
        for r in self.rows:
            yield r
        for c in self.cols:
            yield c
        for b in self.boxes:
            yield b


    def solve(self):
        # Set the potential values
        logging.debug("Set the inital potential values")
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
        logging.debug("Process initially solved cells")
        for (cell, value) in initiallySolved:
            self.setCell(cell, value)
        logging.debug("Process the groups")
        for x in range(10):
            for group in self.groups():
                group.processPotentials(self.setCell)
        

if __name__ == "__main__":
    from curses import wrapper
    from .data import puzzle1

    def main(window: '_CursesWindow'):
        su = sudoku()
        su.window = window
        su.load(puzzle1)
        su.draw(window)

        window.getch()

        try:
            su.solve()
        except PuzzleSolved:
            pass
        window.getch()

    wrapper(main)




                 

        