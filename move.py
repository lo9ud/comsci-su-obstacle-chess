from common import *
from piece import Piece


class Move:
    """Represents a move in the game.

    Stores the move's origin and destination, and provides methods for transforming it into several representations
    """

    def __init__(self, player: int, origin: tuple[int, int], destination: tuple[int, int]) -> None:
        self.player = player
        self.origin = origin
        self.destination = destination

    @classmethod
    def from_str(cls, string) -> Result:
        raise NotImplementedError

    def canonical(self) -> str:
        """Returns the move in canonical notation.

        Returns
        -------
        str
            The move in canonical notation
        """
        return f"{algebraic(*self.origin)}-{algebraic(*self.destination)}"

    def validate(self, board: "Board") -> Result:
        """Validates this move against the supplied board

        Parameters
        ----------
        board : Board
            The board to validate against

        Returns
        -------
        Result
            Whether the move succeeded
        """
        raise NotImplementedError


class PlaceWall(Move):
    """Represents a wall placement in the game.

    The wall is placed between the two coordinates, which must be adjacent and not diagonal.
    """

    def __init__(self, origin: tuple[int, int], destination: tuple[int, int]) -> None:
        super().__init__(origin, destination)

    def canonical(self) -> str:
        # TODO: Implement the fact the only south/west walls are allowed
        raise NotImplementedError(
            "Cannot convert wall placement to canonical notation")


class PlaceMine(Move):
    def __init__(self, origin: tuple[int, int]) -> None:
        super().__init__(origin, origin)

    def canonical(self) -> str:
        return f"M{algebraic(*self.origin)}"


class PlaceTrapdoor(Move):
    def __init__(self, origin: tuple[int, int]) -> None:
        super().__init__(origin, origin)

    def canonical(self) -> str:
        return f"D{algebraic(*self.origin)}"


class Promotion(Move):
    """Represents a pawn promotion in the game.

    The pawn is promoted to the piece specified by the promotion.
    """

    def __init__(
        self, origin: tuple[int, int], destination: tuple[int, int], promotion: Piece
    ) -> None:
        super().__init__(origin, destination)
        self.promotion = promotion

    def canonical(self) -> str:
        return f"{algebraic(*self.origin)}-{algebraic(*self.destination)}={self.promotion.canonical()}"


class Castle(Move):  # TODO: Implement castling
    """Represents castling"""

    def __init__(self):
        pass


class QueenCastle(Castle):
    pass


class KingCastle(Castle):
    pass
