from functools import total_ordering
import board
from typing import Protocol
from common import *

number = int | float


@total_ordering
class Rect:
    def __init__(self, *args) -> None:
        x1: number = 0
        y1: number = 0
        x2: number = 0
        y2: number = 0
        match len(args):
            case 1:  # 4-tuple of ints
                x1, y1, x2, y2 = args[0]
            case 2:
                x1, y1, x2, y2 = args[0] + args[1]
            case 4:
                x1, y1, x2, y2 = args
        self.x1 = min(x1, x2)
        self.x2 = max(x1, x2)
        self.y1 = min(y1, y2)
        self.y2 = max(y1, y2)

    def intersection(self, __o: Self):
        return Rect(
            max(self.x1, __o.x1),
            max(self.y1, __o.y1),
            min(self.x2, __o.x2),
            min(self.y2, __o.y2),
        )

    def bounding_union(self, __o: Self):
        return Rect(
            min(self.x1, __o.x1),
            min(self.y1, __o.y1),
            max(self.x2, __o.x2),
            max(self.y2, __o.y2),
        )

    def __eq__(self, __o: Self):
        return (
            self.x1 == __o.x1
            and self.x2 == __o.x2
            and self.y1 == __o.y1
            and self.y2 == __o.y2
        )

    def __lt__(self, __o: Self):
        return (
            __o.x1 < self.x1 < __o.x2
            and __o.y1 < self.y1 < __o.y2
            and __o.x1 < self.x2 < __o.x2
            and __o.y1 < self.y2 < __o.y2
        )

    def __and__(self, __o: Self):
        return self.intersection(__o)

    def __rand__(self, __o: Self):
        return __o.intersection(self)

    def __or__(self, __o: Self):
        return self.bounding_union(__o)

    def __ror__(self, __o: Self):
        return __o.bounding_union(self)

    @property
    def center(self):
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    def align(self, __o: Self):
        return Rect.from_center(self.center, __o.width, __o.height)

    @property
    def area(self):
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @classmethod
    def from_center(cls, center: tuple[number, number], width: number, height: number):
        return cls(
            center[0] - width / 2,
            center[1] - height / 2,
            center[0] + width / 2,
            center[1] + height / 2,
        )


class Drawable(Protocol):
    """Drawable interface for all controls that implement a `draw` method"""

    def draw(self, draw_boundary: Rect):
        raise NotImplementedError


class Piece(Drawable):
    piece_icons = {
        1: {
            "king": "\u265A",
            "queen": "\u265B",
            "rook": "\u265C",
            "bishop": "\u265D",
            "knight": "\u265E",
            "pawn": "\u265F",
        },
        -1: {
            "king": "\u2654",
            "queen": "\u2655",
            "rook": "\u2656",
            "bishop": "\u2657",
            "knight": "\u2658",
            "pawn": "\u2659",
        },
        "mine": "\u26EF",
        "trapdoor": {"open": "\u2610", "closed": "\u2612"},
    }

    def __init__(self) -> None:
        pass

    @classmethod
    def draw(cls, draw_boundary: Rect, piece: Self):
        pass


class Mine(Piece):
    def __init__(self) -> None:
        pass


class Wall(Drawable):
    def __init__(self) -> None:
        pass


class Tile(Drawable):
    def __init__(self, node: board.BoardNode) -> None:
        pass


class Board(Drawable):
    req = "board"

    def __init__(self, pos: Rect) -> None:
        pass


class App:
    def __init__(self) -> None:
        self.controls = {}

    def register(self, pos: Rect, cont: Drawable) -> int:
        self.controls[o := hash(pos)]((pos, cont))
        return o

    def unregister(self, key: int):
        del self.controls[key]

    def __getitem__(self, key):
        return self.controls[key]

    def draw(self, *kwargs):
        for control in self.controls.values():
            control.draw(kwargs[control.req])

    def kill(self):
        pass
