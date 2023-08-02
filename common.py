"""Classses and functions common to all files
"""
import stdio


class Result:
    """A result monad with two possible states:

     - Success(payload)
     - Failure(reason)

    This class provides a method unwrap to extract its payload
    """

    def __init__(self, payload):
        self.__payload = payload

    def unwrap(self):
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
        self, f, *args, **kwargs
    ) -> "Result":  # TODO: fix typing ie f:funtion[returns result]
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


class Success(Result):
    def __init__(self, payload):
        super().__init__(payload)


class Failure(Result):
    """Represents a failure of an operation.

    Payload must be the entire error message to be printed to screen.
    """

    def __init__(self, reason: str = "") -> None:
        super().__init__(reason)

    def and_then(self, f, *args, **kwargs) -> Result:
        return self


class Player:
    """Player enum

    Members:
    ----------
    WHITE : auto -> The white player
    BLACK : auto -> The black player
    """

    WHITE = 0
    BLACK = 1

    @staticmethod
    def from_str(string: str):
        return Player.WHITE if string.lower() == "w" else Player.BLACK

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
    return chr(y + 97) + str(7 - x + 1)


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
    stdio.writeln("Testing algebraic()")
    stdio.writeln("  a  b  c  d  e  f  g  h")
    for i in range(8):
        stdio.writef("%i ", i + 1)
        for j in range(8):
            stdio.writef("%s ", algebraic(i, j))
        stdio.writeln()

    stdio.writeln("\nTesting inverse algebraic()/coords()")
    for i in range(8):
        for j in range(8):
            stdio.writef("%b ", coords(algebraic(i, j)) == (i, j))
        stdio.writeln()

    stdio.writeln("\nTesting constrain()")
    for i in range(8):
        stdio.writef("(%i, %i)", constrain(i, 2, 5))

    stdio.writeln("\nTesting is_white()")
    stdio.writeln("Black squares are '░░', white squares are '██'")
    stdio.writeln("  a b c d e f g h")
    for i in range(8):
        stdio.writef("%i ", i + 1)
        for j in range(8):
            stdio.write("██" if is_white(i, j) else "░░")
        stdio.writeln()
