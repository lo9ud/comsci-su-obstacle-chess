"""Classses and functions common to all files
"""
import enum
import sys
from typing import Any, Callable, TypeVar, Generic


def err_print(_s):
    sys.stderr.write(_s)


class Error:
    """Error messages as an enum."""

    ILLEGAL_MOVE = "illegal move at %s"
    """Move %s is illegal"""
    ILLEGAL_BOARD = "illegal board at %s"
    """Board is illegal at %s"""
    ILLEGAL_STATUSLINE = "illegal board at statusline"
    """Illegal statusline"""


class Info:
    """Informational messages as an enum."""

    CHECK = "check"
    """Player in check"""
    CHECKMATE = "checkmate"
    """Player checkmated"""
    STALEMATE = "stalemate"
    """Game at stalemate"""
    DRAW_FIFTY = "draw due to fifty moves"
    """Game drawn due to fifty-move rule"""
    DRAW_THREEFOLD = "draw due to threefold repetition"
    """Game drawn due to threefold-repetition"""


class Wall(enum.Flag):
    """A flag enum  for walls"""

    NONE = enum.auto()
    """No walls"""
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
        return " ".join(retval) or "NONE"

    @classmethod
    def get_wall_direction(cls, _from: tuple, _to: tuple) -> tuple:
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
        x1, y1, x2, y2 = *_from, *_to
        if x1 == x2:
            # Diagonal movement
            if y1 == y2:
                from_walls = Wall.NONE
                to_walls = Wall.NONE
                if y1 > y2:  # Going Northwards
                    from_walls |= Wall.NORTH
                    from_walls &= ~Wall.NONE
                    to_walls &= Wall.SOUTH
                    from_walls &= ~Wall.NONE
                    if x1 > x2:
                        from_walls &= Wall.WEST
                        to_walls &= Wall.EAST
                    else:
                        from_walls &= Wall.EAST
                        to_walls &= Wall.WEST
                else:  # Going Southwards
                    from_walls &= Wall.SOUTH
                    from_walls &= ~Wall.NONE
                    to_walls &= Wall.NORTH
                    from_walls &= ~Wall.NONE
                    if x1 > x2:
                        from_walls &= Wall.WEST
                        to_walls &= Wall.EAST
                    else:
                        from_walls &= Wall.EAST
                        to_walls &= Wall.WEST
                return (from_walls, to_walls)
            # East-West movement
            else:
                return (Wall.SOUTH, Wall.NORTH) if y2 > y1 else (Wall.NORTH, Wall.SOUTH)
            # North-South movement
        else:
            return (Wall.EAST, Wall.WEST) if x2 > x1 else (Wall.WEST, Wall.EAST)

    @classmethod
    def coords_to_walls(cls, _from: tuple, _to: tuple) -> tuple:
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
        x1, y1, x2, y2 = *_from, *_to
        # East-West movement
        if x1 == x2 and y1 != y2:
            return (Wall.SOUTH, Wall.NORTH) if y2 > y1 else (Wall.NORTH, Wall.SOUTH)
        # North-South movement
        elif x1 != x2 and y1 == y2:
            return (Wall.EAST, Wall.WEST) if x2 > x1 else (Wall.WEST, Wall.EAST)
        else:
            return (Wall.NONE, Wall.NONE)


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

    def and_then(self, f: Callable, *args, **kwargs) -> "Result[E]":
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

    def other(self) -> "Player":
        """Returns the other player when called on a player

        Returns
        -------
        Player
            The other player
        """
        return Player.WHITE if self == Player.BLACK else Player.BLACK
def algebraic(x: int, y: int):
    """Converts a tuple of coordinates to algebraic notation.

    Parameters
    ----------
    x : int
        The x coordinate (zero-indexed)
    y : int
        The y coordinate (zero-indexed)

    Returns
    -------
    str
        The algebraic notation for the coordinates
    """
    char_part = chr(x + 97)
    int_part = str(8 - y)
    return char_part + int_part


def coords(alg: str) -> tuple:
    """Converts a string in algebraic notation to a tuple of coordinates.

    Parameters
    ----------
    alg : str
        The string to convert

    Returns
    -------
    tuple[int, int]
        The coordinates represented by the string
    """
    return (7 - int(alg[1]) + 1, ord(alg[0]) - 97)


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


if __name__ == "__main__":
    for y in range(8):
        for x in range(8):
            print(algebraic(x, y), end=" ")
        print()
