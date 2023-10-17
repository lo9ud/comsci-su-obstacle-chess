"""Classses and functions common to all files
"""
import enum
import sys
from typing import Callable, List, TypeVar, Generic, Iterator, Any


def err_print(_s):
    sys.stderr.write(_s)


class Position:
    def __init__(self, x: int, y: int) -> None:
        self.x: int = x  # ranks
        self.y: int = y  # files

    @property
    def rank(self) -> int:
        """Horizontal position on the board, from 0 to 7"""
        return self.x

    @property
    def file(self) -> int:
        """Vertical position on the board, from 0 to 7"""
        return self.y
    
    @classmethod
    def all(cls):
        """Returns a list of all positions on the board"""
        return [Position(x, y) for x in range(8) for y in range(8)]

    def __add__(self, other: "Position") -> "Position":
        if isinstance(other, Position):
            return Position(self.x + other.x, self.y + other.y)
        return NotImplemented

    def __mul__(self, other: int) -> "Position":
        if isinstance(other, int):
            return Position(self.x * other, self.y * other)
        return NotImplemented

    def __iter__(self) -> Iterator[int]:
        yield self.x
        yield self.y

    def __eq__(self, other: "Position") -> bool:
        if isinstance(other, Position):
            return self.x == other.x and self.y == other.y
        return super().__eq__(other)

    def __sub__(self, other: "Position") -> "Position":
        return Position(self.x - other.x, self.y - other.y)
    
    def norm(self) -> "Position":
        """Normalizes a position offset such that both components are either 1, 0 or -1"""
        return Position(
            self.x if self.x == 0 else self.x//abs(self.x), 
            self.y if self.y == 0 else self.y//abs(self.y)
            )
    
    def between(self, other: "Position") -> List["Position"]:
        """Returns a non-inclusive list of positions between two positions

        Returns
        -------
        Iterable[Positions]
            The positions between the two positions
        """
        norm_delta = (self - other).norm()
        return [
            self + norm_delta * i
            for i in range(1, max(abs(self.x - other.x), abs(self.y - other.y)))
        ]
        
    def blocks(self, other1: "Position", other2:"Position") -> bool:
        """Determines if a position blocks a line between two other positions

        Parameters
        ----------
        other1 : Position
            THe first position
        other2 : Position
            The second position

        Returns
        -------
        bool
            Whether the position blocks the line between the other two positions
        """
        return True if self in other1.between(other2) else self in [other1, other2]
    
    def canonical(self) -> str:
        """The canonical representation of a position

        In chess algebraic notation. For example, the position (0, 0) is a1.

        Returns
        -------
        str
            The canonical representation of the position
        """
        char_part = chr(self.x + 97)
        int_part = str(8 - self.y)
        return char_part + int_part

    @classmethod
    def from_str(cls, string: str) -> "Position":
        """Returns a position from a string in algebraic chess notation

        Returns
        -------
        Position
            The Position described by that string
        """
        coords = (ord(string[0]) - 97, 8 - int(string[1]))
        return Position(*coords)

    def __repr__(self) -> str:
        return f"P({self.canonical()} -> ({self.x}, {self.y}))"

    def __hash__(self) -> int:
        return hash((self.x, self.y))


P = Position



class GameSignal(enum.Flag):
    """Signals from the game providing information about the game state."""
    
    MOVE = enum.auto()
    """Moved a piece"""
    PROMOTE = enum.auto()
    """Promoted a pawn"""
    CASTLE = enum.auto()
    """Castled a king"""
    THREEFOLD_AVAILABLE = enum.auto()
    """Threefold repetition is available"""
    FIFTY_AVAILABLE = enum.auto()
    """Fifty-move rule is available"""
    CHECK = enum.auto()
    """Player is in check"""
    CHECKMATE = enum.auto()
    """Player is checkmated"""
    STALEMATE = enum.auto()
    """Game is at stalemate"""
    ILLEGAL_MOVE = enum.auto()
    """Move is illegal"""
    MINE_DETONATION = enum.auto()
    """A mine has detonated"""


class Error:
    """Error messages as an enum."""

    ILLEGAL_MOVE = "illegal move %s"
    """Move %s is illegal"""
    ILLEGAL_BOARD = "illegal board at %s"
    """Board is illegal at %s"""
    ILLEGAL_STATUSLINE = "illegal board at status line"
    """Illegal statusline"""


class Info:
    """Informational messages as an enum."""

    CHECK = "INFO: check"
    """Player in check"""
    CHECKMATE = "INFO: checkmate"
    """Player checkmated"""
    STALEMATE = "INFO: stalemate"
    """Game at stalemate"""
    DRAW_FIFTY = "INFO: draw due to fifty moves"
    """Game drawn due to fifty-move rule"""
    DRAW_THREEFOLD = "INFO: draw due to threefold repetition"
    """Game drawn due to threefold-repetition"""


class Wall(enum.Flag):
    """A flag enum  for walls"""
    
    NORTH = enum.auto()
    """North wall"""
    SOUTH = enum.auto()
    """South wall"""
    EAST = enum.auto()
    """East wall"""
    WEST = enum.auto()
    """West wall"""
    
    @classmethod
    def to_str(cls, walls: "Wall") -> str:
        """Constructs a string of which walls are contained within a wall flag

        Parameters
        ----------
        walls : int
            The wall flag to check

        Returns
        -------
        str
            The constructed string
        """
        retval = []
        if walls & Wall.NORTH:
            retval.append("NORTH")
        if walls & Wall.SOUTH:
            retval.append("SOUTH")
        if walls & Wall.EAST:
            retval.append("EAST")
        if walls & Wall.WEST:
            retval.append("WEST")
        return "|".join(retval) or "NONE"

    @classmethod
    def get_wall_direction(cls, _from: Position, _to: Position) -> tuple:
        """Returns the types of wall that would block motion between _from and _to

        Returns a tuple of the walls that _from would have to block the motion and the walls that _to would need to block the motion

        Parameters
        ----------
        _from : tuple[int, int]
            The position a piece is coming from
        _to : tuple[int,int]
            THe position a piece is going to

        Returns
        -------
        tuple[int, int]
            The correct wall code for _from and for _to
        """
        x1, y1, x2, y2 = _from.x, _from.y, _to.x, _to.y
        if x1 != x2:
            return (Wall.EAST, Wall.WEST) if x2 > x1 else (Wall.WEST, Wall.EAST)
        if y1 != y2:
            return (Wall.SOUTH, Wall.NORTH) if y2 > y1 else (Wall.NORTH, Wall.SOUTH)
        from_walls = Wall(0)
        to_walls = Wall(0)
        if y1 > y2:
            from_walls |= Wall.NORTH
            to_walls &= Wall.SOUTH
        else:
            from_walls &= Wall.SOUTH
            to_walls &= Wall.NORTH
        if x1 > x2:
            from_walls &= Wall.WEST
            to_walls &= Wall.EAST
        else:
            from_walls &= Wall.EAST
            to_walls &= Wall.WEST
        return (from_walls, to_walls)

    @classmethod
    def coords_to_walls(cls, _from: Position, _to: Position) -> tuple:
        """Transforms two coordinates into a wall flag

        Parameters
        ----------
        _from : tuple[int,int]
            The "back" of the wall
        _to : tuple[int, int]
            The "front" of the wall

        Returns
        -------
        int
            The wall flag
        """
        x1, y1, x2, y2 = _from.x, _from.y, _to.x, _to.y
        # East-West movement
        if x1 == x2 and y1 != y2:
            return (Wall.SOUTH, Wall.NORTH) if y2 > y1 else (Wall.NORTH, Wall.SOUTH)
        # North-South movement
        elif x1 != x2 and y1 == y2:
            return (Wall.EAST, Wall.WEST) if x2 > x1 else (Wall.WEST, Wall.EAST)
        else:
            return (Wall(0), Wall(0))


    def blocking(self, pos) -> Position:
        """Returns the position that this wall blocks

        Args:
            pos (Position): The position

        Returns:
            Position: The blocked position
        """
        if self == Wall.NORTH:
            return pos + P(0, 1)
        elif self == Wall.SOUTH:
            return pos + P(0, -1)
        elif self == Wall.EAST:
            return pos + P(1, 0)
        elif self == Wall.WEST:
            return pos + P(-1, 0)
        else:
            raise ValueError("Invalid wall")

    def alternate(self) -> "Wall":
        """Returns the opposite wall

        Returns
        -------
        Wall
            The opposite wall
        """
        if self == Wall.NORTH:
            return Wall.SOUTH
        elif self == Wall.SOUTH:
            return Wall.NORTH
        elif self == Wall.EAST:
            return Wall.WEST
        elif self == Wall.WEST:
            return Wall.EAST
        else:
            return Wall(0)


class TrapdoorState(enum.Enum):
    """The possible states of a trapdoor as an "enum"."""

    NONE = enum.auto()
    """No trapdoor"""
    HIDDEN = enum.auto()
    """Trapdoor present (Hidden)"""
    OPEN = enum.auto()
    """Trapdoor present (Open)"""


T = TypeVar("T", covariant=True)
S = TypeVar("S")
E = TypeVar("E")


class Result(Generic[T]):
    """A result monad with two possible states:

     - Success(payload)
     - Failure(reason)

    This was implemented before becoming aware that try/except was allowed. Inspired by Rust-style Result.
    """

    def __init__(self, payload: T):
        self.__payload = payload

    def unwrap(self) -> T:
        """Return the payload of this result

        Returns
        -------
        Any
            The Result payload
        """
        return self.__payload

    def inject(self, payload):
        """Replace the payload of this Result with a new one

        Parameters
        ----------
        payload : Any
            The new payload
        """
        self.__payload = payload

    def and_then(self, f: Callable, *args, **kwargs) -> "Result":
        """Applies a function to the payload of this Result and return a new Result

        Failures pass through unchanged.

        Parameters
        ----------
        f : function
            The fucntion to apply

        Returns
        -------
        Result
            The new result
        """
        retval = f(self.__payload, *args, **kwargs)
        return retval if isinstance(retval, Result) else Success(retval)

    def on_err(self, f, *args, **kwargs):
        """Applies a function to the payload of this Failure

        Successes pass through unchanged

        Parameters
        ----------
        f : function
            The function to perform, that returns nothing

        Returns
        -------
        Result
            The original Result
        """
        return self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__payload})"

class Success(Result[T]):
    def __init__(self, payload: T = None):
        super().__init__(payload)


class Failure(Result):
    """Represents a failure of an operation.

    Payload must be the entire error message to be printed to screen.
    """

    def __init__(self, reason: str = "") -> None:
        super().__init__(reason)

    def and_then(self, f, *args, **kwargs) -> "Failure":
        return self

    def on_err(self, f, *args):
        f(*args)
        return self


class Player(enum.Enum):
    """Player enum

    Members:
    ----------
    WHITE : auto -> The white player
    BLACK : auto -> The black player
    """

    WHITE = -1
    BLACK = 1

    @classmethod
    def from_str(cls, string: str) -> Result["Player"]:
        return (
            Success(Player.WHITE)
            if string.lower() == "w"
            else Success(Player.BLACK)
            if string.lower() == "b"
            else Failure("           ")
        )

    @staticmethod
    def canonical(player):
        return "w" if player == Player.WHITE else "b"

    def opponent(self) -> "Player":
        """Returns the other player when called on a player

        Returns
        -------
        Player
            The other player
        """
        return Player.WHITE if self == Player.BLACK else Player.BLACK


def is_white(i, j) -> bool:
    """Determines is a square is white or black

    Accepts a tuple of coordinates, an algebraic string, or two integer arguments

    Returns
    -------
    bool
        Whether the square is white or black

    Raises
    ------
    ValueError
        The position is invalid
    ValueError
        The arguments are invalid
    """
    return not bool((i + j) % 2)


def lzip(*args, min_l: int = -1, default: Any = None) -> Iterator[tuple]:
    """A reimplementation of zip that pads with a default value

    Parameters
    ----------
    min_l : int|None, optional
        The minimum length to pad to, by default -1 to pad to length of the longest iterable
    default : Any, optional
        The value to pad with, by default None

    Returns
    -------
    Iterator[tuple]
        An iterable of tuples, where each tuple is the corresponding element of each iterable, or the default value if the iterable is too short
    """
    min_l = max(max(map(len, args)), min_l)
    return (tuple(a[i] if i < len(a) else default for a in args) for i in range(min_l))


if __name__ == "__main__":
    for y in range(8):
        for x in range(8):
            string = f"{chr(x+97)}{y+1}"
            frm = Position.from_str(string)
            crd = Position(x, y)
            print(f"{frm.canonical()==crd.canonical()}", end=" ")
        print()
    print(0)
    for y in range(8):
        for x in range(8):
            print(Position(x, y).canonical(), end=" ")
        print()
    print()
    begin = Position.from_str("a1")
    end = Position.from_str("h8")
    for pos in begin.between(end):
        print(pos.canonical(), end=" ")