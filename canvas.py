import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import functools
from common import *

# import stddraw

number = Union[int, float]

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

class App:
    def __init__(self) -> None:
        ...
