from typing import Generator, TYPE_CHECKING
import curses

if TYPE_CHECKING:
    from curses import _CursesWindow


class cell:

    def __init__(self) -> None:
        self.row = None
        self.col = None
        self.box = None
        self.value: int = None
        self.potentialValues: list[int] = []
        self.drawPos = None 

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
        if self.row is not None:
            yield self.row
        if self.col is not None:
            yield self.col
        if self.box is not None:
            yield self.box


class CellGroup:

    def __init__(self, cells: list[cell]):
        self.cells = cells
        self.completed: int = len([x for x in cells if x.complete()])

    def complete(self) -> bool:
        return self.completed == 9

    def __iter__(self):
        for cell in self.cells:
            yield cell

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
                    window.addstr(y, offset, str(cell.value))
                cell.drawPos = (y, offset)
                offset += 2
                n += 1
                if n % 3 == 0:
                    offset += 2
            y += 1
            nRow += 1
        window.addstr(y, gap, dashRow)

if __name__ == "__main__":
    from curses import wrapper
    from .data import puzzle1

    def main(window: '_CursesWindow'):
        su = sudoku()
        su.load(puzzle1)
        su.draw(window)

        window.getch()

    wrapper(main)




                 

        