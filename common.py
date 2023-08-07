"""Classses and functions common to all files
"""
import sys
from typing import Callable, TypeVar, Generic, Union

def err_print(string, *args, **kwargs):
    print(string, *args, file=sys.stderr, **kwargs)


# TODO: IF typing is allowed, replace Result with type alias and rename Result to __Result
T = TypeVar("T", covariant=True)
E = TypeVar("E", covariant=True)
class Result(Generic[T]):
    """A result monad with two possible states:

     - Success(payload)
     - Failure(reason)

    This class provides a method unwrap to extract its payload
    """

    def __init__(self, payload:T):
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

    def and_then(
        self, f:Callable[[T], "Result[E]"|E], *args, **kwargs
    ) -> "Result[E]":  # TODO: fix typing ie f:funtion[returns result]
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


class Success(Result, Generic[T]):
    def __init__(self, payload:T=None):
        super().__init__(payload)


class Failure(Result):
    """Represents a failure of an operation.

    Payload must be the entire error message to be printed to screen.
    """

    def __init__(self, reason: str = "") -> None:
        super().__init__(reason)

    def and_then(self, f, *args, **kwargs) -> "Result":
        return self

    def on_err(self, f, *args):
        f(*args)
        return self

class Player:
    """Player enum

    Members:
    ----------
    WHITE : auto -> The white player
    BLACK : auto -> The black player
    """

    WHITE = -1
    BLACK = 1

    @staticmethod
    def from_str(string: str) -> Result[int]:
        return (
            Success(Player.WHITE)
            if string.lower() == "w"
            else Success(Player.BLACK)
            if string.lower() == "b"
            else Failure()
        )

    @staticmethod
    def canonical(player):
        return "w" if player == Player.WHITE else "b"


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


def coords(alg: str) -> tuple[int, int]:
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


def constrain(
    x: int | float, _min: int | float = -1e32, _max: int | float = 1e32
) -> int | float:
    """Constrains a value to between _min and _max

    Leaving _min or _max empty will default to arbitrarily high/low numbers

    Parameters
    ----------
    x : int | float
        The value to constrain
    _min : int | float
        The minimum value
    _max : int | float
        The maximum value

    Returns
    -------
    int|float
        The constrained value
    """
    return max(_min, min(x, _max))


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
    print("Testing algebraic()")
    for y in range(8):
        for x in range(8):
            print(f"{x=}|{y=}|{algebraic(x, y)} ", end = "")
        print()
    for y in range(8):
        for x in range(8):
            print(f"{algebraic(x, y)} ", end = "")
        print()

    print("\nTesting inverse algebraic()/coords()")
    for x in range(8):
        for y in range(8):
            print(str(coords(algebraic(x, y)) == (x, y)).ljust(5), end = "")
        print()

    print("\nTesting constrain()")
    for x in range(8):
        print("(%i)"%(constrain(x, 2, 5)))

    print("\nTesting is_white()")
    print("Black squares are '░░', white squares are '██'")
    print("  a b c d e f g h")
    for x in range(8):
        print("%i "%(8-x), end = "")
        for y in range(8):
            print("██" if is_white(x, y) else "░░", end = "")
        print()
