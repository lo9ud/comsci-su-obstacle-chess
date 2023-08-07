from common import *
from piece import Piece


class Move:
    """Represents a move in the game.

    Stores the move's origin and destination, and provides methods for transforming it into several representations
    """

    def __init__(
        self, player: int, origin: tuple[int, int], destination: tuple[int, int]
    ) -> None:
        self.player = player
        self.origin = origin
        self.destination = destination
        self.delta : tuple[int,int] = tuple(map(lambda x: abs(x[1] - x[0]), zip(origin, destination)))

    @classmethod
    def from_str(cls, player: int, string:str) -> Result["Move"]:
        # TODO: wall transformation from direction-position to position-position
        # TODO: pawn promotion transformation
        match list(string):
            # standard move
            case [x1, y1,'-', x2, y2] if x1.isalpha() and y1.isdigit() and x2.isalpha() and y2.isdigit():
                return Success(Move(player, coords(x1+y1), coords(x2+y2)))
            # pawn promotion
            case [x1, y1, '-', x2, y2, '=', p] if x1.isalpha() and y1.isdigit() and x2.isalpha() and y2.isdigit() and p.isalpha():
                return Success(Promotion(player, coords(x1+y1), coords(x2+y2), Piece.from_str(p).unwrap().__class__)) # TODO: clean this up
            # castling
            case ["0","-","0", *queen]:
                if queen == ["-","0"]:
                    return Success(QueenCastle(player))
                return Success(KingCastle(player))
            # special moves
            # trapdoor
            case ['D', x, y] if x.isalpha() and y.isdigit():
                return Success(PlaceTrapdoor(player, coords(x+y)))
            # mine
            case ['M', x, y] if x.isalpha() and y.isdigit():
                return Success(PlaceMine(player, coords(x+y)))
            # wall
            case [("|"|"_" as wall), x, y]:
                # west wall
                if wall == "|":
                    _from = coords(x+y)
                    _to = coords(x+y[0]+str(int(y[1])+1))
                    _to = _to[0]-1,_to[1]
                # south wall
                else: # wall == "_"
                    _from = coords(x+y)
                    _to = coords(x+y)
                    _to = _to[0],_to[1]+1
                return Success(PlaceWall(player, _from, _to))
        raise NotImplementedError 

    def canonical(self) -> str:
        """Returns the move in canonical notation.

        Returns
        -------
        str
            The move in canonical notation
        """
        return f"{algebraic(*self.origin)}-{algebraic(*self.destination)}"


class PlaceWall(Move):
    """Represents a wall placement in the game.

    The wall is placed between the two coordinates, which must be adjacent and not diagonal.
    """

    def __init__(self, player:int, origin: tuple[int, int], destination: tuple[int, int]) -> None:
        super().__init__(player, origin, destination)

    def canonical(self) -> str:
        # TODO: Implement the fact the only south/west walls are allowed
        raise NotImplementedError("Cannot convert wall placement to canonical notation")


class PlaceMine(Move):
    def __init__(self, player:int, origin: tuple[int, int]) -> None:
        super().__init__(player, origin, origin)

    def canonical(self) -> str:
        return f"M{algebraic(*self.origin)}"


class PlaceTrapdoor(Move):
    def __init__(self, player: int, origin: tuple[int, int]) -> None:
        super().__init__(player, origin, origin)

    def canonical(self) -> str:
        return f"D{algebraic(*self.origin)}"


class Promotion(Move):
    """Represents a pawn promotion in the game.

    The pawn is promoted to the piece specified by the promotion.
    """

    def __init__(
        self, player:int, origin: tuple[int, int], destination: tuple[int, int], promotion: type[Piece]
    ) -> None:
        super().__init__(player, origin, destination)
        self.promotion = promotion

    def canonical(self) -> str:
        return f"{algebraic(*self.origin)}-{algebraic(*self.destination)}={self.promotion(self.player).canonical()}"


class Castle(Move):  # TODO: Implement castling
    """Represents castling. 
    
    This class holds the common logic for castling, and the subclasses implement the specifics.
    
    Only the information about the kings movement is stored, the rook's movement is inferred from the king's, but can be calculated using the rook_move method."""

    def __init__(self, player:int, destination: tuple[int, int]) -> None:
        match player:
            case Player.WHITE:
                origin = (7, 4)
            case Player.BLACK:
                origin = (0, 4)
            case _:
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
        
        return Move(
            self.player, 
            rook_origin, 
            rook_destination
            )


class QueenCastle(Castle):
    def __init__(self, player: int) -> None:
        match player:
            case Player.WHITE:
                destination = (7, 6)
            case Player.BLACK:
                destination = (0, 2)
            case _:
                destination = (0, 0)
        super().__init__(player, destination)


class KingCastle(Castle):
    def __init__(self, player: int) -> None:
        match player:
            case Player.WHITE:
                destination = (7, 2)
            case Player.BLACK:
                destination = (0, 4)
            case _:
                destination = (0, 0)
        super().__init__(player, destination)
