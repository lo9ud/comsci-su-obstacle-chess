from src.common import *

class Piece:
    """The base class for all pieces.

    Provides methods for representing the piece's state, and for providing methods for manipulating it.
    """
    def __init__(self, player: Player) -> None:
        self.player = player
        self.name = self.__class__.__name__.lower()
        
    def __repr__(self) -> str:
        return f"{self.name}({self.player.name.lower()})"
    
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
    """A pawn.
    """
    ...

class Knight(Piece):
    """A knight.
    """
    ...

class Bishop(Piece):
    """A bishop.
    """
    ...

class Rook(Piece):
    """A rook.
    """
    ...

class Queen(Piece):
    """A queen.
    """
    ...

class King(Piece):
    """A king.
    """
    ...

