from typing import Generator, Iterable
from logger import Logger, StdOut, Errors, Infos
from board import Board


class Position:
    def __init__(self, position: str | tuple[int, int]) -> None:
        if isinstance(position, str):
            self.position = tuple(map(lambda x: ord(x)-ord('a'), position))
        else:
            self.position = position

        self.rank = self.position[1]
        self.file = self.position[0]

    def __str__(self) -> str:
        return f"{chr(self.position[0]+ord('a'))}{self.position[1]+1}"

    def __iter__(self) -> Iterable[int]:
        return iter(self.position)


class Move:
    def __init__(self, start: Position, end: Position) -> None:
        self.start = start
        self.end = end

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"

    def validate(self) -> None:
        """Checks that the move is valid

        Checks the board state for flags such as check and checkmate, and determines whether the move is valid.

        Raises
        ------
        NotImplementedError
        """
        raise NotImplementedError

    def apply(self, board: Board) -> None:
        """Applies a move to the board

        _extended_summary_

        Parameters
        ----------
        board : Board
            _description_
        """
        self.validate()
        # TODO: Apply move to board


class KCastle(Move):
    def __init__(self) -> None:
        pass

    def apply(self, board: Board) -> None:
        # TODO: Find out how castling works with arbitrary numbers of rooks etc
        raise NotImplementedError


class QCastle(Move):
    def __init__(self) -> None:
        pass

    def apply(self, board: Board) -> None:
        # TODO: Find out how castling works with arbitrary numbers of rooks etc
        raise NotImplementedError


class Piece:
    def __init__(self, designation, position=None):
        self.designation = designation
        self.position = position

    def __str__(self):
        return f"{self.designation} at {self.position}"
