from common import *


class Piece:
    """The base class for all pieces.

    Provides methods for representing the piece's state, and provides methods for manipulating it.
    """

    def __init__(self, player: int) -> None:
        self.player = player
        """The player this piece belongs to"""
        self.name = self.__class__.__name__.lower()
        """A huma readable name for the piece in lowercase"""

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}({Player.canonical(self.player)})"

    def canonical(self) -> str:
        """Returns a string representation of the piece, using standard algebraic notation.

        Returns
        -------
        str
            A string representation of the piece.
        """
        raise NotImplementedError

    @staticmethod
    def from_str(string: str) -> "Piece":
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
        match string.lower():
            case "p":
                return Pawn(player)
            case "n":
                return Knight(player)
            case "b":
                return Bishop(player)
            case "r":
                return Rook(player)
            case "q":
                return Queen(player)
            case "k":
                return King(player)
            case _:
                raise ValueError(f"Invalid piece string: {string}")


class Pawn(Piece):
    """A pawn."""

    def canonical(self) -> str:
        return "p" if self.player == Player.BLACK else "P"

    ...


class Knight(Piece):
    """A knight."""

    def canonical(self) -> str:
        return "n" if self.player == Player.BLACK else "N"

    ...


class Bishop(Piece):
    """A bishop."""

    def canonical(self) -> str:
        return "b" if self.player == Player.BLACK else "B"

    ...


class Rook(Piece):
    """A rook."""

    def canonical(self) -> str:
        return "r" if self.player == Player.BLACK else "R"

    ...


class Queen(Piece):
    """A queen."""

    def canonical(self) -> str:
        return "q" if self.player == Player.BLACK else "Q"

    ...


class King(Piece):
    """A king."""

    def canonical(self) -> str:
        return "k" if self.player == Player.BLACK else "K"

    ...
