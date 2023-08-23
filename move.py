from common import *
from common import Player
from piece import Piece
from board import Wall
import re


class Move:
    """Represents a move in the game.

    Stores the move's origin and destination, and provides methods for transforming it into several representations
    """

    std_move_re = re.compile(r"\w\d-\w\d(?:=\w)")
    castle_re = re.compile(r"0(-0){1,2}")

    def __init__(self, player: Player, origin: tuple, destination: tuple) -> None:
        self.player = player
        self.origin = origin
        self.destination = destination
        self.delta: tuple = tuple(
            map(lambda x: abs(x[1] - x[0]), zip(origin, destination))
        )

    @classmethod
    def from_str(cls, player: Player, string: str) -> Result["Move"]:
        # TODO: wall transformation from direction-position to position-position
        # TODO: pawn promotion transformation
        # TODO: check that failures are passing correctly
        # TODO: ensure valid coordinates
        if cls.std_move_re.match(string):
            origin, dest = string[:2], string[3:5]
            if "=" in string:
                new_piece = Piece.from_str(string[-1])
                if isinstance(new_piece, Failure):
                    return Failure()
                return Success(
                    Promotion(
                        player,
                        coords(origin),
                        coords(dest),
                        new_piece.unwrap().__class__,
                    )
                )
            return Success(Move(player, coords(origin), coords(dest)))
            # castling
        elif cls.castle_re.match(string):
            if len(string) > 3:
                return Success(QueenCastle(player))
            return Success(KingCastle(player))
        elif string.startswith("D"):
            return Success(PlaceTrapdoor(player, coords(string[1:3])))
            # mine
        elif string.startswith("M"):
            return Success(PlaceMine(player, coords(string[1:3])))
        elif string[0] in ["|", "_"]:
            x, y = string[1:3]
            wall = string[0]
            _from = coords(x + y)
            # west wall
            if wall == "|":
                _to = coords(x + y[0] + str(int(y[1]) + 1))
                _to = _to[0] - 1, _to[1]
            else:  # wall == "_"
                _to = coords(x + y)
                _to = _to[0], _to[1] + 1
            return Success(PlaceWall(player, _from, _to))
        elif string == "...":
            return Success(NullMove())
        return Failure()

    def canonical(self) -> str:
        """Returns the move in canonical notation.

        Returns
        -------
        str
            The move in canonical notation
        """
        return f"{algebraic(*self.origin)}-{algebraic(*self.destination)}"

class NullMove(Move):
    """Defines the null move `...`, which is used to represent a partially played game where the last played move was white's."""
    def __init__(self, player: Player = Player.WHITE, origin: tuple = (0,0), destination: tuple = (0,0)) -> None:
        super().__init__(player, origin, destination)
    
    def canonical(self) -> str:
        return "..."

class PlaceWall(Move):
    """Represents a wall placement in the game.

    The wall is placed between the two coordinates, which must be adjacent and not diagonal.
    """

    def __init__(self, player: Player, origin: tuple, destination: tuple) -> None:
        super().__init__(player, origin, destination)

    def canonical(self) -> str:
        # TODO: Implement the fact the only south/west walls are allowed
        node_wall = Wall.get_wall_direction(self.origin, self.destination)
        if node_wall == Wall.SOUTH:
            return f"_{algebraic(*self.origin)}"
        elif node_wall == Wall.WEST:
            return f"|{algebraic(*self.origin)}"
        else:
            raise ValueError


class PlaceMine(Move):
    def __init__(self, player: Player, origin: tuple) -> None:
        super().__init__(player, origin, origin)

    def canonical(self) -> str:
        return f"M{algebraic(*self.origin)}"


class PlaceTrapdoor(Move):
    def __init__(self, player: Player, origin: tuple) -> None:
        super().__init__(player, origin, origin)

    def canonical(self) -> str:
        return f"D{algebraic(*self.origin)}"


class Promotion(Move):
    """Represents a pawn promotion in the game.

    The pawn is promoted to the piece specified by the promotion.
    """

    def __init__(
        self,
        player: Player,
        origin: tuple,
        destination: tuple,
        promotion: type,
    ) -> None:
        super().__init__(player, origin, destination)
        self.promotion = promotion

    def canonical(self) -> str:
        return f"{algebraic(*self.origin)}-{algebraic(*self.destination)}={self.promotion(self.player).canonical()}"


class Castle(Move):  # TODO: Implement castling
    """Represents castling.

    This class holds the common logic for castling, and the subclasses implement the specifics.

    Only the information about the kings movement is stored, the rook's movement is inferred from the king's, but can be calculated using the rook_move method.

    This class should not be manually instantiated.
    """

    def __init__(self, player: Player, destination: tuple) -> None:
        if player == Player.WHITE:
            origin = (7, 4)
        elif player == Player.BLACK:
            origin = (0, 4)
        else:
            origin = (0, 0)
        super().__init__(player, origin, destination)

    def rook_move(self) -> Move:
        """Generates the move of the rook in a castling move.

        Returns a move object bound to the same player as the castling move, with the origin and destination of the rook in the castling move.

        Returns
        -------
        Move
            The move of the rook in the castling move
        """
        # if the king is castling to the right, the rook is on the rightmost column, otherwise it is on the leftmost column, and its row is the same as the king's
        rook_origin = (7 if self.destination[0] == 6 else 0, self.origin[1])

        # if the king is castling to the right, the rook moves to the left of the king, otherwise it moves to the right of the king, and its row is the same as the king's
        rook_destination = (5 if self.destination[0] == 6 else 0, self.destination[1])

        return Move(self.player, rook_origin, rook_destination)


class QueenCastle(Castle):
    def __init__(self, player: Player) -> None:
        if player == Player.WHITE:
            destination = (7, 6)
        elif player == Player.BLACK:
            destination = (0, 2)
        else:
            destination = (0, 0)
        super().__init__(player, destination)


class KingCastle(Castle):
    def __init__(self, player: Player) -> None:
        if player == Player.WHITE:
            destination = (7, 2)
        elif player == Player.BLACK:
            destination = (0, 4)
        else:
            destination = (0, 0)
        super().__init__(player, destination)
