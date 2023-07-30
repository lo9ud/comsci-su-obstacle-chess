from typing import Any
from src.piece import Piece
from src.game import Player


class BoardNode:
    def __init__(self) -> None:
        raise NotImplementedError


class Board:
    """A representation of the board state.

    Maintains the boards current state, and provides methods for manipulating it.
    """

    def __init__(self, board: list[list[BoardNode]], state: dict[str, bool | Player | None] | None = None) -> None:
        # The boards nodes, as a 2D array
        self.__nodes: list[list[BoardNode]] = board

        # the boards state, including castling rights, en passant, and the current player
        # if state is not provided, it is assumed to be the standard starting state
        # TODO: see if state must be verified
        self.__state = state or {
            "castling": {
                "black": {
                    "queenside": True,
                    "kingside": True,
                },
                "white": {
                    "queenside": True,
                    "kingside": True,
                }
            },
            "enpassant": None,
            "player": Player.WHITE
        }

    @classmethod
    def standard_board(cls) -> "Board":
        """Returns a board that is in standard starting positions.
        """
        raise NotImplementedError

    @classmethod
    def from_file(cls, file) -> "Board":
        """Returns a board that is in the state described by the given file.
        """
        raise NotImplementedError


class Move:
    """Represents a move in the game.

    Stores the move's origin and destination, and the piece that moved.
    """

    def __init__(self, origin: tuple[int, int], destination: tuple[int, int], piece: Piece) -> None:
        raise NotImplementedError
