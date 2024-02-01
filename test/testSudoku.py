import unittest
from Sudoku.sudoku import sudoku, PuzzleSolved
import Sudoku.data

class TestSudoku(unittest.TestCase):

    def runTest(self, puzzle, solution):
        su = sudoku()
        su.load(puzzle)

        with self.assertRaises(PuzzleSolved):
            su.solve()

        self.assertTrue(su.solved())

        for group in su.groups():
            for v in range(1, 10):
                self.assertTrue(group.hasValue(v))

        solutionIt = iter(solution)
        for row in su.rows:
            self.assertEqual(row.stringValue(), next(solutionIt))

    def test_puzzle1(self):
        puzzle = Sudoku.data.puzzle1

        solution = [
            "917354862",
            "482196735",
            "536287149",
            "854931627",
            "679842513",
            "123765498",
            "365479281",
            "248513976",
            "791628354"
        ]

        self.runTest(puzzle, solution)

    def test_hard_puzzle(self):
        puzzle = Sudoku.data.hard_puzzle

        solution = [
            "714639852",
            "362578941",
            "985142367",
            "829467513",
            "571293486",
            "643851279",
            "257386194",
            "436915728",
            "198724635"
        ]

        self.runTest(puzzle, solution)

    def test_harder_puzzle(self):
        puzzle = Sudoku.data.harder_puzzle

        solution = [
            "563798412",
            "187243965",
            "249165873",
            "354871629",
            "971526348",
            "628934157",
            "895417236",
            "716382594",
            "432659781"
        ]

        self.runTest(puzzle, solution)

    def test_hardest_puzzle(self):
        puzzle = Sudoku.data.hardest_puzzle

        solution = [
            "697243185",
            "453816927",
            "812597364",
            "926781543",
            "341625798",
            "785439612",
            "134972856",
            "269358471",
            "578164239"
        ]

        self.runTest(puzzle, solution)
