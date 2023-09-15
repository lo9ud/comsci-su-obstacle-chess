from common import *
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:  # allows typechecking while preventing circular imports
    from move import Move

class Piece:
    """The base class for all pieces.

    Provides methods for representing the piece's state, and provides methods for manipulating it.
    """

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

    @staticmethod
    def check(move: "Move") -> bool:
        """Does basic validation on a move. Checks that the move fits the basic move pattern for the piece.
        """
        valid = True

        # check that the piece is moving
        valid &= move.delta != P(0,0)

        # check that the move starts and ends on the board
        valid &= all(map(lambda x: 0 <= x <= 7, (*move.origin, *move.destination)))

        return valid

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

    def canonical(self) -> str:
        return "p" if self.owner == Player.BLACK else "P"

    @staticmethod
    def check(move) -> bool:
        # check base conditions
        valid = Piece.check(move)

        # check that the pawn is moving forward by one or two
        valid &= abs(move.delta.y) in [1, 2]

        # check that the pawn is moving sideways by at most one
        valid &= abs(move.delta.x) <= 1
        return valid


class Knight(Piece):
    """A knight."""

    jumps = True

    offsets = [
        P(2, 1),
        P(2, -1),
        P(-2, 1),
        P(-2, -1),
        P(1, 2),
        P(1, -2),
        P(-1, 2),
        P(-1, -2),
    ]
    """The offsets that a knight can move by."""

    def canonical(self) -> str:
        return "n" if self.owner == Player.BLACK else "N"

    @staticmethod
    def check(move) -> bool:
        valid = Piece.check(move)

        # check that the knight is moving in an L shape
        valid &= (
            abs(move.delta.x) == 2
            and abs(move.delta.y) == 1
            or abs(move.delta.x) == 1
            and abs(move.delta.y) == 2
        )

        return valid


class Bishop(Piece):
    """A bishop."""

    def canonical(self) -> str:
        return "b" if self.owner == Player.BLACK else "B"

    @staticmethod
    def check(move) -> bool:
        valid = Piece.check(move)

        # check that the bishop is moving diagonally
        valid &= abs(move.delta.x) == abs(move.delta.y)

        return valid


class Rook(Piece):
    """A rook."""

    def canonical(self) -> str:
        return "r" if self.owner == Player.BLACK else "R"

    @staticmethod
    def check(move) -> bool:
        valid = Piece.check(move)

        # check that the rook is moving orthogonally
        valid &= min(move.delta) == 0

        return valid


class Queen(Piece):
    """A queen."""

    def canonical(self) -> str:
        return "q" if self.owner == Player.BLACK else "Q"

    @staticmethod
    def check(move) -> bool:
        valid = Piece.check(move)
        # queens can move like rooks or like bishops
        valid &= Rook.check(move) or Bishop.check(move)

        return valid


class King(Piece):
    """A king."""

    def canonical(self) -> str:
        return "k" if self.owner == Player.BLACK else "K"

    @staticmethod
    def check(move) -> bool:
        valid = Piece.check(move)

        # check that the king is moving by at most one in any direction
        valid &= all(map(lambda x: abs(x) <= 1, move.delta))

        return valid
