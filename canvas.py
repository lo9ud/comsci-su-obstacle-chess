import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import functools
import board
from move import Move
from typing import Protocol
from common import *

# import stddraw

number = int | float


class ClickEvent:
    def __init__(self, x: number, y: number):
        self.x, self.y = x, y


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

    def intersection(self, __o: "Rect"):
        return Rect(
            max(self.x1, __o.x1),
            max(self.y1, __o.y1),
            min(self.x2, __o.x2),
            min(self.y2, __o.y2),
        )

    def bounding_union(self, __o: "Rect"):
        return Rect(
            min(self.x1, __o.x1),
            min(self.y1, __o.y1),
            max(self.x2, __o.x2),
            max(self.y2, __o.y2),
        )

    def scale_inner(self, *rects: "Rect"):
        """Scales a list of `Rect`s (contained within this one) such that they have the same relative dimensions , but fit within `self`

        Returns
        -------
        list[Rect]
            The new rectangles
        """
        inner = functools.reduce(Rect.bounding_union, rects)
        w, h = inner.width, inner.height

        def _scale_inner(rect: "Rect"):
            return Rect.from_center(
                rect.center, rect.width / w * self.width, rect.height / h * self.height
            )

        return list(map(_scale_inner, rects))

    def transform(self, parent: "Rect") -> "Rect":
        """Transforms a Rect's boundary to be flat to parent

        _extended_summary_

        Parameters
        ----------
        parent : Self
            _description_

        Returns
        -------
        Self
            _description_
        """
        return Rect(
            parent.x1 + self.x1,
            parent.y1 + self.y1,
            parent.x2 + self.x2,
            parent.y2 + self.y2,
        )

    def __contains__(self, __o: "Rect") -> bool:
        return self & __o in [self, __o]

    def __and__(self, __o: "Rect"):
        return self.intersection(__o)

    def __rand__(self, __o: "Rect"):
        return __o.intersection(self)

    def __or__(self, __o: "Rect"):
        return self.bounding_union(__o)

    def __ror__(self, __o: "Rect"):
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

    def align(self, __o: "Rect"):
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
    """Drawable interface for all controls that implement a `draw_in` method"""

    def draw_in(self, draw_boundary: Rect):
        pass


class ClickDelegate(Protocol):
    """This class delegates clicks to its children"""

    def get_click_handler(self):
        ...


class ClickSink(Protocol):
    """This class can handle clicks, returning a"""

    def handle_click(
        self, __e: ClickEvent
    ) -> (
        str
    ):  # TODO: return type. str, custom message object... (should be queue-transferable)
        ...


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
    def draw(cls, draw_boundary: Rect, piece: "Piece"):
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
        self.controls: dict[int, tuple[Rect, Drawable]] = {}
        self._rects: dict[int, Rect] = {}

    def register(self, pos: Rect, cont: Drawable) -> int:
        self.controls[o := hash(pos)] = (pos, cont)
        self._rects[o] = pos
        return o

    def unregister(self, key: int):
        del self.controls[key]

    # def get_click_controller(self):
    #     # construct a clickevent
    #     event = ClickEvent(
    #         x:=stddraw.mouseX(),
    #         y:=stddraw.mouseY()
    #     )
    #     # construct a rect around the click
    #     micro_bound = Rect.from_center(
    #         (0.0001,0.0001),
    #         x,
    #         y
    #     )
    #     # TODO: hierarchial delegation
    #     # find the smallest rect that encloses this
    #     enclosing = min(
    #         ((rect, cont) for rect, cont in self.controls.values() if micro_bound in rect),
    #         key=lambda x: x[0].area,
    #     )
    #     return enclosing

    def __getitem__(self, key):
        return self.controls[key]

    def send(self, move: Move):
        raise NotImplementedError

    # def draw(self, *kwargs):
    #     for control in self.controls.values():
    #         control.draw(kwargs[control.req])

    def kill(self):
        pass
