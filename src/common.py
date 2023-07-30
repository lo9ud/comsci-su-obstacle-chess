"""Classses and functions common to all files
"""

import enum

class Player(enum.Enum):
    """Player enum
    
    Members:
    ----------
    WHITE : auto -> The white player
    BLACK : auto -> The black player
    """
    WHITE = enum.auto()
    BLACK = enum.auto()
    @staticmethod
    def from_str(string:str):
        return Player.WHITE if string.lower() == 'w' else Player.BLACK
    
class Move:
    """Represents a move in the game.

    Stores the move's origin and destination, and provides methods for transforming it into several representations
    """
    def __init__(self, origin: tuple[int, int], destination: tuple[int, int]) -> None:
        raise NotImplementedError
    
def algebraic(x:int,y:int):
    if not(0 <= x <= 7 and 0 <= y <= 7):
        raise ValueError("Coordinates must be between 0 and 7, inclusive")
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
    return chr(x+97) + str(y+1)

def coords(alg:str) -> tuple[int, int]:
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
    return (ord(alg[0])-97,int(alg[1])-1)
