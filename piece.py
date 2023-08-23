from common import *
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:  # allows typechecking while preventing circular imports
    from move import Move


class PieceDelta:
    """Defines the movement of a piece."""

    def __init__(self, delta_f: Callable[["Move"], bool]) -> None:
        self.__delta = delta_f
        """A function that takes a move, and returns whether the move is valid for the piece."""

    def __contains__(self, item: "Move") -> bool:
        return self.__delta(item)

    def __call__(self, move: "Move") -> bool:
        return self.__delta(move)


class Piece:
    """The base class for all pieces.

    Provides methods for representing the piece's state, and provides methods for manipulating it.
    """

    delta = PieceDelta(lambda _: False)
    """The movement of the piece, as a PieceDelta with containment implemented."""
    jumps = False
    """Whether the piece can jump over other pieces and walls."""

    def __init__(self, owner: Player) -> None:
        self.owner = owner
        """The player this piece belongs to"""
        self.name = self.__class__.__name__.lower()
        """A huma readable name for the piece in lowercase"""

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}({Player.canonical(self.owner)})"

    def canonical(self) -> str:
        """Returns a string representation of the piece, using standard algebraic notation.

        Returns
        -------
        str
            A string representation of the piece.
        """
        raise NotImplementedError

    def can_move(self, move: "Move") -> bool:
        """Returns whether the piece can move to the given location.

        Parameters
        ----------
        move : Move
            The move to check.

        Returns
        -------
        bool
            Whether the piece can move to the given location.
        """
        return move in self.delta

    @classmethod
    def from_str(cls, string: str) -> Result["Piece"]:
        """Returns a piece from a string, using standard algebraic notation.

        Parameters
        ----------
        string : str
            The string to parse.

        Returns
        -------
        Piece
            Some subclass of Piece, depending on the string.
        """
        player = Player.WHITE if string.isupper() else Player.BLACK
        if string.lower() == "p":
            return Success(Pawn(player))
        elif string.lower() == "n":
            return Success(Knight(player))
        elif string.lower() == "b":
            return Success(Bishop(player))
        elif string.lower() == "r":
            return Success(Rook(player))
        elif string.lower() == "q":
            return Success(Queen(player))
        elif string.lower() == "k":
            return Success(King(player))
        else:
            return Failure()


class Pawn(Piece):
    """A pawn."""

    delta = PieceDelta(
        lambda move: move.delta == (0, 1)  # Standard move
        or move.delta == (0, 2)  # First move
        or move.delta == (1, 1)  # Capture
    )

    def canonical(self) -> str:
        return "p" if self.owner == Player.BLACK else "P"

    ...


class Knight(Piece):
    """A knight."""

    delta = PieceDelta(
        lambda move: move.delta == [1, 2]  # Standard move
        or move.delta == [2, 1]  # Standard move
    )
    jumps = True

    def canonical(self) -> str:
        return "n" if self.owner == Player.BLACK else "N"

    ...


class Bishop(Piece):
    """A bishop."""

    delta = PieceDelta(lambda move: move.delta[0] == move.delta[1])  # Standard move

    def canonical(self) -> str:
        return "b" if self.owner == Player.BLACK else "B"

    ...


class Rook(Piece):
    """A rook."""

    delta = PieceDelta(
        lambda move: (
            move.delta[0] == 0 and move.delta[1] > 0
        )  # Standard (vertical) move
        or (move.delta[1] == 0 and move.delta[0] > 0)  # Standard (horizontal) move
    )

    def canonical(self) -> str:
        return "r" if self.owner == Player.BLACK else "R"

    ...


class Queen(Piece):
    """A queen."""

    delta = PieceDelta(
        lambda move: move.delta[0] == move.delta[1]  # Diagonal move
        or (move.delta[0] == 0 and move.delta[1] > 0)  # Standard (vertical) move
        or (move.delta[1] == 0 and move.delta[0] > 0)  # Standard (horizontal) move
    )

    def canonical(self) -> str:
        return "q" if self.owner == Player.BLACK else "Q"

    ...


class King(Piece):
    """A king."""

    delta = PieceDelta(
        lambda move: move.delta[0] <= 1 and move.delta[1] <= 1  # Standard move
    )

    def canonical(self) -> str:
        return "k" if self.owner == Player.BLACK else "K"

    ...
