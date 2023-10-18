from typing import Union
from common import *
from piece import Piece
import re


class Move:
    """Represents a move in the game.

    Stores the move's origin and destination, and provides methods for transforming it into several representations
    """

    type_index = 1
    std_move_re = re.compile(r"\w\d-\w\d(=\w)?")
    castle_re = re.compile(r"0(-0){1,2}")

    def __init__(self, player: Player, origin: Position, destination: Position) -> None:
        self.player = player
        self.origin = origin
        self.destination = destination
        self.delta: Position = P(destination.x - origin.x, destination.y - origin.y)

    @classmethod
    def from_str(cls, player: Player, string: str) -> Result["Move"]:
        if cls.std_move_re.match(string):
            origin, dest = string[:2], string[3:5]
            if "=" in string:
                new_piece = Piece.from_str(string[-1])
                if isinstance(new_piece, Failure):
                    return Failure()
                return Success(
                    Promotion(
                        player,
                        Position.from_str(origin),
                        Position.from_str(dest),
                        new_piece.unwrap().__class__,
                    )
                )
            return Success(
                Move(player, Position.from_str(origin), Position.from_str(dest))
            )
            # castling
        elif cls.castle_re.match(string):
            if len(string) > 3:
                return Success(QueenCastle(player))
            return Success(KingCastle(player))
        elif string.startswith("D"):
            return Success(PlaceTrapdoor(player, Position.from_str(string[1:3])))
            # mine
        elif string.startswith("M"):
            return Success(PlaceMine(player, Position.from_str(string[1:3])))
        elif string[0] in ["|", "_"]:
            wall = string[0]
            _from = Position.from_str(string[1:3])
            # west wall
            if wall == "|":
                # _to = _from + P(-1, 0)
                wall_type = Wall.WEST
            else:  # wall == "_"
                # _to = _from + P(0, 1)
                wall_type = Wall.SOUTH
            return Success(PlaceWall(player, _from, wall_type))
        elif string == "...":
            return Success(NullMove())
        return Failure(Error.ILLEGAL_MOVE % string)

    def canonical(self) -> str:
        """Returns the move in canonical notation.

        Returns
        -------
        str
            The move in canonical notation
        """
        return f"{self.origin.canonical()}-{self.destination.canonical()}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.origin.canonical()}->{self.destination.canonical()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return False
        return (
            self.player == other.player
            and self.origin == other.origin
            and self.destination == other.destination
        )

    def __hash__(self) -> int:
        return hash((self.player.value, self.origin, self.destination))

class NullMove(Move):
    """Defines the null move `...`, which is used to represent a partially played game where the last played move was white's."""

    type_index = 0

    def __init__(
        self,
        player: Player = Player.WHITE,
        origin: Position = P(0, 0),
        destination: Position = P(0, 0),
    ) -> None:
        super().__init__(player, origin, destination)

    def canonical(self) -> str:
        return "..."


class PlaceWall(Move):
    """Represents a wall placement in the game.

    The wall is placed between the two coordinates, which must be adjacent and not diagonal.
    """

    type_index = 2

    def __init__(self, player: Player, origin: Position, wall) -> None:
        super().__init__(player, origin, origin)
        self.wall = wall

    def canonical(self) -> str:
        if self.wall & Wall.SOUTH:
            return f"_{self.origin.canonical()}"
        elif self.wall & Wall.WEST:
            return f"|{self.origin.canonical()}"
        


class PlaceMine(Move):
    type_index = 3

    def __init__(self, player: Player, origin: Position) -> None:
        super().__init__(player, origin, origin)

    def canonical(self) -> str:
        return f"M{self.origin.canonical()}"


class PlaceTrapdoor(Move):
    type_index = 4

    def __init__(self, player: Player, origin: Position) -> None:
        super().__init__(player, origin, origin)

    def canonical(self) -> str:
        return f"D{self.origin.canonical()}"


class Promotion(Move):
    """Represents a pawn promotion in the game.

    The pawn is promoted to the piece specified by the promotion.
    """

    type_index = 5

    def __init__(
        self,
        player: Player,
        origin: Position,
        destination: Position,
        promotion: type,
    ) -> None:
        super().__init__(player, origin, destination)
        self.promotion = promotion

    def canonical(self) -> str:
        return f"{self.origin.canonical()}-{self.destination.canonical()}={self.promotion(self.player).canonical()}"

    @classmethod
    def from_semi(cls, semi:"SemiPromotion", promotion_class:Piece):
        return cls(semi.player, semi.origin, semi.destination, promotion_class)

class SemiPromotion(Move):
    """Represents a pawn promotion in the game.

    Does not specify the piece to which the pawn is promoted.
    """

    def __init__(
        self,
        player: Player,
        origin: Position,
        destination: Position,
    ) -> None:
        super().__init__(player, origin, destination)

    def __eq__(self, other: Union[Promotion, "SemiPromotion"]) -> bool:
        if isinstance(other, Promotion):
            return (
                self.player == other.player
                and self.origin == other.origin
                and self.destination == other.destination
            )
        return super().__eq__(other)

    def canonical(self) -> str:
        return f"{self.origin.canonical()}-{self.destination.canonical()}=?"


class Castle(Move):
    """Represents castling.

    This class holds the common logic for castling, and the subclasses implement the specifics.

    Only the information about the kings movement is stored, the rook's movement is inferred from the king's, but can be calculated using the rook_move method.

    This class should not be manually instantiated.
    """

    def __init__(self, player: Player, destination: Position) -> None:
        if player == Player.WHITE:
            origin = P(4, 7)
        elif player == Player.BLACK:
            origin = P(4, 0)
        else:
            origin = P(0, 0)
        super().__init__(player, origin, destination)

    def rook_move(self) -> Move:
        """Generates the move of the rook in a castling move.

        Returns a move object bound to the same player as the castling move, with the origin and destination of the rook in the castling move.

        Returns
        -------
        Move
            The move of the rook in the castling move
        """
        raise NotImplementedError


class QueenCastle(Castle):
    type_index = 6

    def __init__(self, player: Player) -> None:
        destination = P(2, int(3.6 - 3.5 * player.value))
        super().__init__(player, destination)

    def rook_move(self) -> Move:
        rook_origin = P(0, self.origin.y)
        rook_destination = P(3, self.origin.y)
        return Move(self.player, rook_origin, rook_destination)

    def canonical(self) -> str:
        return "0-0-0"


class KingCastle(Castle):
    type_index = 7

    def __init__(self, player: Player) -> None:
        destination = P(6, int(3.6 - 3.5 * player.value))
        super().__init__(player, destination)

    def rook_move(self) -> Move:
        rook_origin = P(7, self.origin.y)
        rook_destination = P(5, self.origin.y)
        return Move(self.player, rook_origin, rook_destination)

    def canonical(self) -> str:
        return "0-0"
