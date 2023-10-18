import copy
from enum import Enum
from math import cos, radians, sin, sqrt
import os
import time


from move import (
    Move,
    NullMove,
    PlaceMine,
    PlaceTrapdoor,
    PlaceWall,
    Castle,
    Promotion,
    SemiPromotion,
)
from piece import Piece

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
from typing import Dict, Tuple, Union, List, Iterator

import board
import game
import movehandler

from common import *

import stddraw
import color
import picture
from tkinter.filedialog import askopenfile, asksaveasfile

# fps = 30
REFRESH_RATE = 30
FONT_WEIGHT = 24
CHAR_WIDTH = FONT_WEIGHT * 0.60  # calculated experimentally
Widget = TypeVar("Widget", bound="AppWidget")

def print_time_tree(tree):
    def inner(tree, depth=0):
        (id, delta), sub = tree
        print(f"{'  ' * depth}{delta:.4f} |:| {id}")
        if sub:
            for item in sub:
                inner(item, depth + 1)
    inner(tree)

def make_id(widget:object):
    base = widget.__class__.__name__[0].lower()
    for char in widget.__class__.__name__[1:]:
        if char.isupper():
            base += "_"
        base += char.lower()
    base.lstrip("_")
    suffix = int(hash(widget) + time.perf_counter()*10000000)%1000000
    return f"{base}_{suffix}"

class DebugFlags(enum.Flag):
    """Flags for debugging"""

    WIDGET = enum.auto()
    """Show the widget borders and ids"""
    HIERARCHY = enum.auto()
    """Print the widget hierarchy"""
    CLICK = enum.auto()
    """Print the click resolution process"""
    INSPECT = enum.auto()
    """Display the click result after each click"""
    TIME = enum.auto()
    """Time the draw process"""


DEBUG_FLAGS = DebugFlags(0)


class Colors(Enum):
    """Colors used in the game"""

    def clerp(self, _color: color.Color, amount: float):
        """Interpolates between two colors by a given amount"""
        return color.Color(
            int(self.value.getRed() * (1 - amount) + _color.getRed() * amount),
            int(self.value.getGreen() * (1 - amount) + _color.getGreen() * amount),
            int(self.value.getBlue() * (1 - amount) + _color.getBlue() * amount),
        )

    def rotate(self, deg):
        """Applies a linear transformation to the color matrix to rotate the hue by a given amount of degrees"""
        # Adapated from @Mark Ransom on Stack Overflow
        # https://stackoverflow.com/questions/8507885/shift-hue-of-an-rgb-color
        cosA = cos(radians(deg))
        sinA = sin(radians(deg))
        matrix = [
            [
                cosA + (1.0 - cosA) / 3.0,
                1.0 / 3.0 * (1.0 - cosA) - sqrt(1.0 / 3.0) * sinA,
                1.0 / 3.0 * (1.0 - cosA) + sqrt(1.0 / 3.0) * sinA,
            ],
            [
                1.0 / 3.0 * (1.0 - cosA) + sqrt(1.0 / 3.0) * sinA,
                cosA + 1.0 / 3.0 * (1.0 - cosA),
                1.0 / 3.0 * (1.0 - cosA) - sqrt(1.0 / 3.0) * sinA,
            ],
            [
                1.0 / 3.0 * (1.0 - cosA) - sqrt(1.0 / 3.0) * sinA,
                1.0 / 3.0 * (1.0 - cosA) + sqrt(1.0 / 3.0) * sinA,
                cosA + 1.0 / 3.0 * (1.0 - cosA),
            ],
        ]
        rx = (
            self.value.getRed() * matrix[0][0]
            + self.value.getGreen() * matrix[0][1]
            + self.value.getBlue() * matrix[0][2]
        )
        gx = (
            self.value.getRed() * matrix[1][0]
            + self.value.getGreen() * matrix[1][1]
            + self.value.getBlue() * matrix[1][2]
        )
        bx = (
            self.value.getRed() * matrix[2][0]
            + self.value.getGreen() * matrix[2][1]
            + self.value.getBlue() * matrix[2][2]
        )
        return color.Color(
            max(0, min(int(rx), 255)),
            max(0, min(int(gx), 255)),
            max(0, min(int(bx), 255)),
        )

    WHITE = color.Color(255,255,255)
    BLACK = color.Color(0, 0, 0)
    MAGENTA = color.Color(255, 0, 255)

    BOARD = color.Color(209, 139, 71)
    BOARD_ALT = color.Color(255, 206, 158)

    WALL = color.Color(100, 53, 52)

    TRAPDOOR = color.Color(255, 255, 255)
    TRAPDOOR_ALT = color.Color(0, 0, 0)

    DIALOG_INNER = color.Color(40, 40, 40)
    DIALOG_BORDER = color.Color(0, 0, 0)
    DIALOG_TEXT = color.Color(255, 255, 255)
    DIALOG_TEXT_ALT = color.Color(120, 120, 120)

    MOVE_OVERLAY = color.Color(0, 255, 0)
    MOVE_OVERLAY_BORDER = color.Color(0, 0, 0)

    BUTTON_INNER = color.Color(40, 40, 40)
    BUTTON_BORDER = color.Color(0, 0, 0)
    BUTTON_TEXT = color.Color(255, 255, 255)

    CHECKBOX_CHECKED = color.Color(0, 0, 0)

########## Constants ###########
PIECE_IMAGE_FILES = {
    "K": picture.Picture(r"Chess_klt45.svg.png"),
    "Q": picture.Picture(r"Chess_qlt45.svg.png"),
    "R": picture.Picture(r"Chess_rlt45.svg.png"),
    "B": picture.Picture(r"Chess_blt45.svg.png"),
    "N": picture.Picture(r"Chess_nlt45.svg.png"),
    "P": picture.Picture(r"Chess_plt45.svg.png"),
    "k": picture.Picture(r"Chess_kdt45.svg.png"),
    "q": picture.Picture(r"Chess_qdt45.svg.png"),
    "r": picture.Picture(r"Chess_rdt45.svg.png"),
    "b": picture.Picture(r"Chess_bdt45.svg.png"),
    "n": picture.Picture(r"Chess_ndt45.svg.png"),
    "p": picture.Picture(r"Chess_pdt45.svg.png"),
}
OBSTACLE_IMAGE_FILES = {
    "MINE": picture.Picture(r"landmine_crush.png"),
    "TRAPDOOR": picture.Picture(r"trapdoor_crush.png"),
}
SETTINGS = {
    "move_overlay": True,
    "move_animation": False
}


class _AppSize:
    """Defines the size of the app, and calculates a reasonable font size based on the width"""
    def __init__(self, width: int = None, height: int = None) -> None:  # type: ignore
        if any(x is None for x in [width, height]):
            raise ValueError("All arguments must be specified")
        self.width = width
        self.height = height
        self.font = int(28 / 1000 * width)

# Predefined app sizes based on common screen resolutions
APP_SIZES = [
    _AppSize(width=400, height=300),
    _AppSize(width=800, height=600),
    _AppSize(width=1000, height=800),
    _AppSize(width=1080, height=720),
    _AppSize(width=1920, height=1080),
]


class Context:
    """A class that provides information to widgets about the current state of the game"""

    def __init__(
        self,
        _game: game.Game,
        potential_moves: List[Position],
        last_moves: List[Move],
        check: Union[Player, None] = None,
    ) -> None:
        self.game = _game
        self.potential_moves: List[Position] = potential_moves
        self.last_moves: List[Move] = last_moves
        self.check = check


def mod_lightness(color: color.Color, lightness):
    return color.Color(
        int(color.getRed() * lightness),
        int(color.getGreen() * lightness),
        int(color.getBlue() * lightness),
    )


class Point:
    """Defines a point on the canvas"""
    def __init__(self, _x: float, _y: float) -> None:
        self.x = _x
        self.y = _y

    def __add__(self, __o: "Point") -> "Point":
        return Point(self.x + __o.x, self.y + __o.y)

    def __sub__(self, __o: "Point") -> "Point":
        return Point(self.x - __o.x, self.y - __o.y)

    def __mul__(self, __o: "Point") -> "Point":
        if isinstance(__o, (float, int)):
            return Point(self.x * __o, self.y * __o)
        return Point(self.x * __o.x, self.y * __o.y)

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __truediv__(self, __o: Union["Point", float, int]) -> "Point":
        if isinstance(__o, Point):
            return Point(self.x / __o.x, self.y / __o.y)
        elif isinstance(__o, (float, int)):
            return Point(self.x / __o, self.y / __o)

    def __iter__(self):
        yield from (self.x, self.y)


class Rect:
    """Defines a rectangle on the canvas"""
    def __init__(self, x1, y1, x2, y2) -> None:
        self.x1 = min(x1, x2)
        self.x2 = max(x1, x2)
        self.y1 = min(y1, y2)
        self.y2 = max(y1, y2)

    def __hash__(self) -> int:
        return hash((self.x1, self.y1, self.x2, self.y2))

    def scaled(self, amount: float) -> "Rect":
        """Scales a Rect by a given amount about its center

        Args:
            amount (float): The amount to scale by

        Returns:
            Rect: The scaled Rect
        """
        return Rect.from_center(self.center, self.width * amount, self.height * amount)

    def scale_x(self, amount: float):
        """Scales the width of a Rect by a given amount

        Args:
            amount (float): The amount to scale by

        Returns:
            Rect: The scaled Rect
        """
        return Rect(self.x1, self.y1, self.x2 * amount, self.y2)

    def scale_y(self, amount: float):
        """Scale the height of a Rect by a given amount

        Args:
            amount (float): The amount to scale by

        Returns:
            Rect: The scaled Rect
        """
        return Rect(self.x1, self.y1, self.x2, self.y2 * amount)

    def translate(self, _pos: Point):
        """Translates a Rect by using a Point as a vector   

        Args:
            _pos (Point): The vector to translate by

        Returns:
            Rect: The translated Rect
        """
        return Rect(
            self.x1 + _pos.x, self.y1 + _pos.y, self.x2 + _pos.x, self.y2 + _pos.y
        )

    def inflate(self, amount: float) -> "Rect":
        """Inflates a Rect by a given amount

        Args:
            amount (float): The amount to inflate by

        Returns:
            Rect: The inflated Rect
        """
        return Rect(
            self.x1 - amount,
            self.y1 - amount,
            self.x2 + amount,
            self.y2 + amount,
        )

    def draw_props(self):
        """Returns the coordinates of the Rect in a format that can be passed to stddraw.filledRectangle

        Returns:
            tuple[float,float,float,float]: the coordinates of the bottom-left corner, followed by the width and height
        """
        return self.x1, self.y1, self.width, self.height

    def intersection(self, __o: "Rect"):
        """Finds the intersection of this and another Rect

        Args:
            __o (Rect): The other Rect

        Returns:
            Rect: The intersection of the two Rects
        """
        return Rect(
            max(self.x1, __o.x1),
            max(self.y1, __o.y1),
            min(self.x2, __o.x2),
            min(self.y2, __o.y2),
        )

    def bounding_union(self, __o: "Rect"):
        """Finds the smallest Rect that contains both this and another Rect

        Args:
            __o (Rect): The other Rect

        Returns:
            Rect: The bounding Rect
        """
        return Rect(
            min(self.x1, __o.x1),
            min(self.y1, __o.y1),
            max(self.x2, __o.x2),
            max(self.y2, __o.y2),
        )

    def transform(self, outer: "Rect") -> "Rect":
        """Transforms a proportional Rect into a Rect with absolute coordinates

        Parameters
        ----------
        parent : Rect
            The parent Rect

        Returns
        -------
        Rect
            The transformed Rects
        """
        left = outer.x1 + self.x1 * outer.width
        bottom = outer.y1 + self.y1 * outer.height
        return Rect(
            left,
            bottom,
            left + outer.width * self.width,
            bottom + outer.height * self.height,
        )

    def __str__(self) -> str:
        return f"Rect({self.x1:.2f}, {self.y1:.2f}, {self.x2:.2f}, {self.y2:.2f})"

    def __repr__(self) -> str:
        return str(self)

    def __contains__(self, __o: Union["Rect", Point]) -> bool:
        if isinstance(__o, Point):
            return self.x1 <= __o.x <= self.x2 and self.y1 <= __o.y <= self.y2
        return self & __o in [self, __o]

    def __and__(self, __o: "Rect"):
        return self.intersection(__o)

    def __rand__(self, __o: "Rect"):
        return __o.intersection(self)

    def __or__(self, __o: "Rect"):
        return self.bounding_union(__o)

    def __ror__(self, __o: "Rect"):
        return __o.bounding_union(self)

    def __mul__(self, __o: Union[Point, float, int]):
        if isinstance(__o, Point):
            return Rect(
                self.x1 * __o.x,
                self.y1 * __o.y,
                self.x2 * __o.x,
                self.y2 * __o.y,
            )
        elif isinstance(__o, (float, int)):
            return Rect(
                self.x1 * __o,
                self.y1 * __o,
                self.x2 * __o,
                self.y2 * __o,
            )
        else:
            return NotImplemented

    @property
    def center(self) -> Point:
        """The center of this Rect"""
        return Point((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def width(self):
        """The width of this rect"""
        return self.x2 - self.x1

    @property
    def height(self):
        """The height of this Rect"""
        return self.y2 - self.y1

    @property
    def area(self):
        """The area of this Rect"""
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @classmethod
    def from_center(cls, center: Point, width: float, height: float):
        """Creates a Rect from a center point and a width and height"""
        return cls(
            center.x - width / 2,
            center.y - height / 2,
            center.x + width / 2,
            center.y + height / 2,
        )


class WidgetInner(dict):
    """A dict that stores widgets in order, allowing them to be iterated over in the order they were added"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._keys: List[Rect] = []

    def values(self):
        """Returns an iterator over the values of the dict in the order they were added"""
        return iter(self[key] for key in self._keys)

    def keys(self):
        """Returns an iterator over the keys of the dict in the order they were added"""
        return iter(self._keys)

    def items(self):
        """Returns an iterator over the items of the dict in the order they were added"""
        yield from ((k, v) for k, v in zip(self._keys, self.values()))

    def __setitem__(self, key, value):
        self._keys.append(key)
        super().__setitem__(key, value)

    def clear(self) -> None:
        """Clears the dict"""
        self._keys.clear()
        super().clear()

    def __iter__(self) -> Iterator:
        """Yields the values of the dict in the order they were added"""
        yield from (self[key] for key in self._keys)

    def __getitem__(self, __key: Rect) -> "AppWidget":
        return super().__getitem__(__key)

    def __delitem__(self, __key: Rect) -> None:
        self._keys.remove(__key)
        return super().__delitem__(__key)


class AppWidget:
    """A hierachical widget that can be drawn on the canvas. Widgets can contain other widgets, and can be clicked on to return a result up the hierarchy."""

    DEFAULTS = {"font-weight": 24, "color": stddraw.BLACK, "bg-color": stddraw.WHITE}

    def __init__(self, rect, _id: str = "", **props) -> None:
        self.id: str = _id or make_id(self)
        self.rect: Rect = rect
        self.inner: WidgetInner = WidgetInner()
        self.parent: Union["AppWidget", None] = None
        self._props = {**copy.deepcopy(AppWidget.DEFAULTS), **props}

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.id})"

    def __repr__(self) -> str:
        return str(self)

    def set_prop(self, attr, value):
        """Sets a graphical property of the widget

        Args:
            attr (str): The property to set
            value (Any): The value to set the property to

        Returns:
            Self: Returns self to allow chaining
        """
        if attr not in self._props:
            raise ValueError(f"Attribute {attr} does not exist")
        if not isinstance(value, type(self._props[attr])):
            print(
                self, list(map(lambda k: str(k) + str(type(k)), self._props.values()))
            )
            raise TypeError(
                f"Attribute '{attr}' must be of type {type(self._props[attr])}, supplied {type(value)}"
            )
        self._props[attr] = value
        return self  # to allow chaining

    def get_prop(self, attr):
        """Gets a graphical property of the widget

        Args:
            attr (str): The property to get

        Returns:
            Self: Returns self to allow chaining
        """
        if attr not in self._props:
            raise ValueError(f"Attribute {attr} does not exist")
        return self._props[attr]

    def update(self, context):
        """Updates the widget and all of its childrens' states

        Args:
            context (Context): The context to update from
        """
        self.update_self(context=context)
        for child in self.inner.values():
            child.update(context=context)

    def update_self(self, context):
        """Performs any updates that are specific to this widget

        Args:
            context (Context): The context to update from
        """
        ...

    def draw_debug(self, draw_rect: Rect, depth=0):
        """Draws the widget's debug information"""
        if DEBUG_FLAGS & DebugFlags.WIDGET:
            stddraw.setPenColor(Colors.BLACK.value)
            stddraw.filledRectangle(*draw_rect.inflate(2).draw_props())
            stddraw.setPenColor(Colors.MAGENTA.rotate(30 * depth))
            stddraw.filledRectangle(*draw_rect.draw_props())
            stddraw.setPenColor(Colors.BLACK.value)
            stddraw.filledRectangle(*draw_rect.inflate(-5).draw_props())
            stddraw.setPenColor(Colors.MAGENTA.value)
            stddraw.setFontSize(16)
            stddraw.text(*draw_rect.center, self.id)
            stddraw.show(30)
            for rect, item in self.inner.items():
                item.draw_debug(rect.transform(draw_rect), depth + 1)

    def _apply_props(self):
        """Applies the widget's properties for drawing"""
        stddraw.setFontSize(self._props["font-weight"])

    def draw(self, draw_rect: Rect):
        """Draws the widget and all of its children

        Args:
            draw_rect (Rect): The Rect to draw the widget in (in absolute coordinates)
        """
        self._apply_props()
        if DEBUG_FLAGS & DebugFlags.TIME:
            start = time.perf_counter()
        self.draw_self(draw_rect)
        if DEBUG_FLAGS & DebugFlags.TIME:
            delta = time.perf_counter() - start
        times = []
        for rect, item in self.inner.items():
            times.append(item.draw(rect.transform(draw_rect)))
            
        if DEBUG_FLAGS & DebugFlags.TIME:
            return ((self.id, delta), times)

    def draw_self(self, rect: Rect):
        """Draws the widget itself

        Args:
            rect (Rect): The Rect to draw the widget in (in absolute coordinates)
        """
        ...

    def handle_click(self, x: float, y: float, _rect=None, depth: int = 0):
        """Propagates a click event through the widget hierarchy

        Args:
            x (float): The x coordinate of the click
            y (float): The y coordinate of the click
            _rect (Rect, optional): The Rect of the parent. Defaults to None.
            depth (int, optional): The depth of the recursion, for debug purposes. Defaults to 0.

        Returns:
            Any: The result of the click, or None if no handler was found
        """
        if DEBUG_FLAGS & DebugFlags.INSPECT:
            self._print_inspect()
        if DEBUG_FLAGS & DebugFlags.CLICK:
            print(" " * depth + ("\-  " if depth else "") + f"Clicked {self}")
        if _rect is None:
            _rect = self.rect
        try:
            targets = reversed(
                [
                    (rect.transform(_rect), item)
                    for rect, item in self.inner.items()
                    if Point(x, y) in rect.transform(_rect)
                ]
            )

            res = None
            for target in targets:
                if DEBUG_FLAGS & DebugFlags.CLICK:
                    print(
                        " " * depth + (" |- " if depth else "") + f"Testing {target[1]}"
                    )
                res = target[1].handle_click(x, y, _rect=target[0], depth=depth + 1)
                if res is not None:
                    if DEBUG_FLAGS & DebugFlags.CLICK:
                        print(
                            " " * depth
                            + ("/-  " if depth else "")
                            + f"Matched {target[1]}"
                        )
                    break
            if DEBUG_FLAGS & DebugFlags.CLICK:
                if res is not None:
                    print(" " * depth + ("|- " if depth else "") + f"Returned {res}")
                elif not depth:
                    print("Propagation terminated, no handler found")
            return res
        except (KeyError, ValueError, AttributeError):
            return None

    def _print_inspect(self):
        """Prints the widget's inspect information (for debug purposes)"""
        print(f"{self.id}:")
        print(f"      rect: {self.rect}")
        print(f"  children: {'|'.join(x.id for x in self.inner.values())}")
        print(f"    parent: {self.parent}")
        self.print_inspect()

    def print_inspect(self):
        """Prints this widget's specific inspect information (for debug purposes)"""
        ...

    def register(self, registree: Widget) -> Widget:
        """Registers a widget as a child of this widget

        Args:
            registree (Widget): The widget to register

        Returns:
            Widget: The registered widget
        """
        self.inner[registree.rect] = registree
        registree.parent = self
        return registree

    def deregister(self, registree: Widget) -> Widget:
        """Deregisters a widget from this widget

        Args:
            registree (Widget): The widget to deregister

        Returns:
            Widget: The deregistered widget
        """
        del self.inner[registree.rect]
        registree.parent = None
        return registree

    def clear(self):
        """Clears the widget's children"""
        self.inner.clear()

    def print_hierarchy(self, depth: int = 0):
        """Prints the widget hierarchy (for debug purposes)

        Args:
            depth (int, optional): The depth of the recursion. Defaults to 0.
        """
        print("  " * depth + str(self.id))
        for child in self.inner.values():
            child.print_hierarchy(depth + 1)

    def get_by_id(self, id: str) -> Union["AppWidget", None]:
        """Search for a widget by its id

        Implemented vis DFS

        Returns:
            Widget|None: The widget with the given id, or None if no widget was found
        """
        for item in self.inner.values():
            if item.id == id:
                return item
            else:
                result = item.get_by_id(id)
                if result:
                    return result
        return None

    def resolve_draw_rect(self):
        """Returns a widgets resolved Rect (in absolute coordinates) by querying up the hierarchy

        Returns:
            Rect: The resolved Rect
        """
        if self.parent:
            return self.rect.transform(self.parent.resolve_draw_rect())
        else:
            return self.rect


class Container(AppWidget):
    """An invisible container for organizing widgets"""
    def draw_self(self, rect: Rect):
        pass


class BoardTile(AppWidget):
    """A tile on a chess board. Maintains its own state."""

    def __init__(self, pos: Position) -> None:
        super().__init__(
            Rect.from_center(
                Point((pos.x + 0.5) / 8, (pos.y + 0.5) / 8), 1.01 / 8, 1 / 8
            )
        )
        self.pos = pos
        self.potential_move = None
        self.tile = None

    def __str__(self) -> str:
        return super().__str__() + f"<{self.pos.canonical()}>"

    def update_self(self, context: Context):
        for move in context.potential_moves:
            if move.destination == self.pos:
                self.potential_move = move
                break
        else:
            self.potential_move = None

        self.tile = context.game.board[self.pos]

    def draw_self(self, draw_rect: Rect):
        global SETTINGS
        super().draw_self(draw_rect)
        # base tile
        if (self.pos.x + self.pos.y) % 2 == 0:
            stddraw.setPenColor(Colors.BOARD.value)
            coord_color = Colors.BOARD_ALT.value
        else:
            stddraw.setPenColor(Colors.BOARD_ALT.value)
            coord_color = Colors.BOARD.value

        # potential move overlay colours
        if self.potential_move and SETTINGS["move_overlay"]:
            if (self.pos.x + self.pos.y) % 2 == 0:
                stddraw.setPenColor(Colors.BOARD.clerp(Colors.MOVE_OVERLAY.value, 0.3))
            else:
                stddraw.setPenColor(
                    Colors.BOARD_ALT.clerp(Colors.MOVE_OVERLAY.value, 0.3)
                )

        # draw tile
        stddraw.filledRectangle(*draw_rect.draw_props())

        # draw tile coordinates
        stddraw.setFontSize(16)
        stddraw.setPenColor(Colors.clerp(Colors.BLACK, coord_color, 0.9))
        stddraw.text(draw_rect.x1 + 15, draw_rect.y1 + 10, self.pos.canonical())
        stddraw.setFontSize(24)

        # walls
        if self.tile.walls:
            stddraw.setPenColor(Colors.WALL.value)

            if self.tile.walls & Wall.NORTH:
                stddraw.filledRectangle(
                    draw_rect.x1, draw_rect.y2 - 5, draw_rect.width, 5
                )

            if self.tile.walls & Wall.SOUTH:
                stddraw.filledRectangle(draw_rect.x1, draw_rect.y1, draw_rect.width, 5)

            if self.tile.walls & Wall.EAST:
                stddraw.filledRectangle(
                    draw_rect.x2 - 5, draw_rect.y1, 5, draw_rect.height
                )

            if self.tile.walls & Wall.WEST:
                stddraw.filledRectangle(draw_rect.x1, draw_rect.y1, 5, draw_rect.height)

        # pieces and obstacles
        if self.tile.contents is not None:
            stddraw.picture(
                pic=PIECE_IMAGE_FILES[self.tile.contents.canonical()],
                x=draw_rect.center.x,
                y=draw_rect.center.y,
            )
        elif self.tile.trapdoor == TrapdoorState.OPEN:
            stddraw.picture(
                pic=OBSTACLE_IMAGE_FILES["TRAPDOOR"],
                x=draw_rect.center.x,
                y=draw_rect.center.y,
            )
            
    
    def handle_click(self, *args, **kwargs):
        return self

    def print_inspect(self):
        print(f"      pos: {self.pos}")
        print(f"  content: {self.tile.contents}")
        print(f" trapdoor: {self.tile.trapdoor}")
        print(f"     mine: {self.tile.mine}")
        print(f"    walls: {self.tile.walls}")
        print(f"potential: {self.potential_move}")


class BoardWidget(AppWidget):
    """A chessboard. Instantiates all the required BoardTiles."""
    def __init__(self, rect, _id: str = None) -> None:
        super().__init__(rect, _id)
        for pos in Position.all():
            self.register(BoardTile(pos))


class Animation(AppWidget):
    """A widget that can be used to create animations"""
    def __init__(self, rect, _id: str = "", **props) -> None:
        super().__init__(rect, _id, **props)
        self._progress = 0
        """The progress of the animation, as a part per 100"""
        self.complete = False

    def progress(self, amt=1):
        """Progress the animation

        Args:
            amt (int, optional): The percentage to progress by. Defaults to 1.
        """
        if self._progress >= 100:
            self.complete = True
        self._progress += amt


class TileAnimation(Animation):
    """An animation bound to a BoardTile"""
    def __init__(self, pos, _id: str = "", **props) -> None:
        super().__init__(
            Rect.from_center(
                Point((pos.x + 0.5) / 8, (pos.y + 0.5) / 8), 1.01 / 8, 1 / 8
            ),
            _id,
            **props,
        )


class BoardAnimation(Animation):
    """An animation bound to the board"""
    def __init__(self, _id: str = "", **props) -> None:
        super().__init__(Rect(0, 0, 1, 1), _id, **props)


class PieceMoveAnimation(BoardAnimation):
    def __init__(self, start_pos, end_pos, piece, _id: str = "", **props) -> None:
        super().__init__(_id, **props)
        self.start_pos = start_pos
        self.start = Rect.from_center(
            Point((start_pos.x + 0.5) / 8, (start_pos.y + 0.5) / 8), 1.02 / 8, 1.02 / 8
        )
        self.end_pos = end_pos
        self.end = Rect.from_center(
            Point((end_pos.x + 0.5) / 8, (end_pos.y + 0.5) / 8), 1.02 / 8, 1.02 / 8
        )
        self.piece = piece

    def draw_self(self, rect: Rect):
        lerp = 0.1

        if (self.start_pos.x + self.start_pos.y) % 2 == 0:
            stddraw.setPenColor(Colors.BOARD.clerp(stddraw.BLUE, lerp))
        else:
            stddraw.setPenColor(Colors.BOARD_ALT.clerp(stddraw.BLUE, lerp))
        stddraw.filledRectangle(*self.start.transform(rect).draw_props())

        if (self.end_pos.x + self.end_pos.y) % 2 == 0:
            stddraw.setPenColor(Colors.BOARD.clerp(stddraw.BLUE, lerp))
        else:
            stddraw.setPenColor(Colors.BOARD_ALT.clerp(stddraw.BLUE, lerp))
        stddraw.filledRectangle(*self.end.transform(rect).draw_props())

        center = (
            self.start.center.x + (self.end.center.x - self.start.center.x) * self._progress / 100,
            self.start.center.y + (self.end.center.y - self.start.center.y) * self._progress / 100,
            )
        stddraw.picture(
            PIECE_IMAGE_FILES[self.piece.canonical()],
            *Rect.from_center(Point(*center),1/8,1/8).transform(rect).center
        )


class MineAnimation(TileAnimation):
    """The mine detonation animation"""
    def draw_self(self, rect: Rect):
        max_outer_radius = 1.5 * (rect.width + rect.height) / 2
        # cloud
        stddraw.setPenColor(stddraw.GRAY)
        stddraw.filledCircle(*rect.center, max_outer_radius * self._progress / 100)

        # red circle
        stddraw.setPenColor(stddraw.RED)
        stddraw.filledCircle(
            *rect.center, max_outer_radius * self._progress / 100 * 0.9
        )

        # orange circle
        stddraw.setPenColor(stddraw.ORANGE)
        stddraw.filledCircle(
            *rect.center, max_outer_radius * self._progress / 100 * 0.7
        )

        # yellow circle
        stddraw.setPenColor(stddraw.YELLOW)
        stddraw.filledCircle(
            *rect.center, max_outer_radius * self._progress / 100 * 0.5
        )

        # white circle
        stddraw.setPenColor(stddraw.WHITE)
        stddraw.filledCircle(
            *rect.center, max_outer_radius * self._progress / 100 * 0.1
        )


class Box(AppWidget):
    """A box with a border"""
    def draw_self(self, rect: Rect, context: Context = None):
        stddraw.setPenColor(Colors.DIALOG_BORDER.value)
        stddraw.filledRectangle(*rect.draw_props())
        stddraw.setPenColor(Colors.DIALOG_INNER.value)
        stddraw.filledRectangle(*rect.inflate(-5).draw_props())


class Label(AppWidget):
    """A text label"""
    def __init__(
        self,
        rect: Rect,
        text: str,
        color: color.Color = Colors.DIALOG_TEXT.value,
        _id=None,
    ) -> None:
        super().__init__(rect, _id=_id)
        self.text = text
        self.color = color

    def draw_self(self, rect: Rect, context: Context = None):
        stddraw.setPenColor(self.color)
        stddraw.text(rect.center.x, rect.center.y, self.text)


class ButtonSignal(enum.Enum):
    """A signal that a button can send to the app"""

    # GENERAL
    QUIT = enum.auto()
    RETURN = enum.auto()
    DONE = enum.auto()
    ACCEPT = enum.auto()
    DECLINE = enum.auto()
    SAVE = enum.auto()
    BLACK = enum.auto()
    WHITE = enum.auto()

    # MAIN MENU
    NEW_GAME = enum.auto()
    LOAD_GAME = enum.auto()
    SETTINGS = enum.auto()

    # GAME SETUP
    STANDARD_BOARD = enum.auto()
    MINE = enum.auto()
    TRAPDOOR = enum.auto()
    SKIP = enum.auto()
    PASS = enum.auto()

    # NEW GAME
    LOCAL = enum.auto()
    AI = enum.auto()
    ONLINE = enum.auto()

    # LOAD GAME
    FROM_FILE = enum.auto()
    REPLAY = enum.auto()

    # SAVE GAME
    SAVE_GAME = enum.auto()

    # SETINGS
    CREDITS = enum.auto()
    MOVE_OVERLAY_TOGGLE = enum.auto()

    # IN GAME
    WALL = enum.auto()
    UNDO = enum.auto()
    REDO = enum.auto()
    MENU = enum.auto()

    # REPLAY
    NEXT = enum.auto()
    PREV = enum.auto()


class Button(AppWidget):
    """A button"""

    def __init__(self, rect: Rect, text: str, signal: ButtonSignal, _id=None) -> None:
        super().__init__(rect, _id=_id)
        box = self.register(
            Box(
                Rect(0, 0, 1, 1),
                _id=self.id + "_box",
            )
        ).register(
            Label(
                Rect(0, 0, 1, 1),
                text,
                Colors.BUTTON_TEXT.value,
                _id=self.id + "_label",
            )
        )
        self.signal = signal

    def draw_self(self, rect: Rect, context: Context = None):
        stddraw.setPenColor(Colors.BUTTON_BORDER.value)
        stddraw.filledRectangle(*self.rect.draw_props())
        stddraw.setPenColor(Colors.BUTTON_INNER.value)
        stddraw.filledRectangle(*self.rect.inflate(-0.1).draw_props())

    def handle_click(self, *args, **kwargs):
        return self.signal


class CheckboxState:
    """The state of a checkbox"""
    class _State(enum.Enum):
        def __bool__(self) -> bool:
            return self == CheckboxState._State.CHECKED

        UNCHECKED = enum.auto()
        CHECKED = enum.auto()

    def __bool__(self) -> bool:
        return bool(self.state)

    def __init__(self, initial) -> None:
        self.state: CheckboxState._State = (
            CheckboxState._State.CHECKED if initial else CheckboxState._State.UNCHECKED
        )

    def toggle(self) -> bool:
        """Toggle the state of the checkbox

        Returns:
            bool: The new state of the checkbox
        """
        if self.state == CheckboxState._State.UNCHECKED:
            self.state = CheckboxState._State.CHECKED
        elif self.state == CheckboxState._State.CHECKED:
            self.state = CheckboxState._State.UNCHECKED
        return bool(self.state)


class CheckBox(AppWidget):
    """A checkbox"""
    def __init__(
        self,
        rect,
        _label: str,
        initial_state: bool,
        _signal: ButtonSignal,
        _id: str = None,
    ) -> None:
        super().__init__(rect, _id)
        self.label = _label
        self.state = CheckboxState(initial_state)
        self.signal = _signal

    def __str__(self) -> str:
        return super().__str__().rstrip(")") + f"|{self.state.state})"

    def draw_self(self, rect: Rect, context: Context = None):
        box = Rect.from_center(
            rect.center, min(rect.width, rect.height), min(rect.width, rect.height)
        )
        stddraw.setPenColor(Colors.BUTTON_BORDER.value)
        stddraw.filledRectangle(*box.draw_props())
        stddraw.setPenColor(Colors.BUTTON_INNER.value)
        stddraw.filledRectangle(*box.inflate(-5).draw_props())

        if self.state:
            stddraw.setPenColor(Colors.CHECKBOX_CHECKED.value)
            stddraw.filledRectangle(*box.inflate(-10).draw_props())

        stddraw.setPenColor(Colors.BUTTON_TEXT.value)
        stddraw.text(
            box.x2 + CHAR_WIDTH * len(self.label) / 2 + 10, box.center.y, self.label
        )

    def handle_click(self, *args, **kwargs):
        self.state.toggle()
        return self


class MoveListItem(AppWidget):
    """An entry in a MoveList item"""
    def __init__(self, rect, index, _id: str = None) -> None:
        super().__init__(rect, _id)
        self.set_prop("font-weight", 16)
        self.index = index
        self.moves = []
        self.turn = 0

    def update_self(self, context: Context):
        self.moves = context.last_moves
        self.turn = context.game.board.turn

    def draw_self(self, rect: Rect):
        self._apply_props()
        try:
            move = self.moves[self.index - 9]
        except IndexError:
            move = None
        if self.turn - self.index > self.turn:
            stddraw.text(
                *rect.center,
                f"{self.turn - self.index}: {('-'*3) if move is None else move.canonical()}",
            )

    def print_inspect(self):
        print(f"      index: {self.index}")
        print(f"       turn: {self.turn}")


class MoveList(AppWidget):
    """A list of moves"""
    def __init__(self, rect: Rect, _id: str = None) -> None:
        super().__init__(rect, _id)
        box = self.register(Box(Rect(0, 0, 1, 1), _id=_id + "_box"))
        box.register(
            Label(
                Rect.from_center(Point(0.5, 0.9), 1, 0.2), "History", _id=_id + "_label"
            )
        )
        for i in range(9):
            box.register(
                MoveListItem(
                    Rect.from_center(Point(0.5, 0.8 - i * 0.07), 1, 0.07),
                    i,
                    _id=_id + f"_item_{i}",
                )
            )


class BoardBackground(AppWidget):
    """The background used for main menus"""
    def draw_self(self, rect: Rect, context: Context = None):
        ratio = rect.height / rect.width
        x_count = 40
        dim = rect.width / x_count
        y_count = int(x_count * ratio)
        for x in range(x_count):
            for y in range(y_count):
                # light_mod = 1-max(0,min(1,((2*(x_count/2-x)/x_count)**2 + ((2*(y_count/2 - y)/y_count)**2)/2)))
                if (x + y) % 2 == 0:
                    stddraw.setPenColor(Colors.BOARD.value)
                else:
                    stddraw.setPenColor(Colors.BOARD_ALT.value)
                stddraw.filledRectangle(dim * x, dim * y, dim, dim)


class MainMenu(AppWidget):
    """The base for all main menus"""
    def __init__(self, _id: str = None) -> None:
        super().__init__(Rect(0, 0, 1, 1), _id)
        bg = self.register(BoardBackground(Rect(0, 0, 1, 1), _id="bg"))
        # create title bar
        title_bar = bg.register(Box(Rect(0.4, 0.8, 0.98, 0.98), _id="title_bar_box"))
        title = title_bar.register(
            Label(
                Rect.from_center(Point(0.37, 0.63), 0.4, 0.5),
                "Obstacle Chess",
                _id="title_bar_label",
            )
        )
        title.set_prop("font-weight", int(title.get_prop("font-weight") * 1.5))
        title_bar.register(
            Label(
                Rect.from_center(Point(0.21, 0.33), 0.4, 0.5),
                "By: Adam Kent",
                color=Colors.DIALOG_TEXT_ALT.value,
                _id="title_bar_credits_label",
            )
        )

        # menu button container
        self.button_box = self.register(
            Box(Rect.from_center(Point(0.5, 0.4), 0.5, 0.6), _id="menu_box")
        )


class PieceButton(AppWidget):
    """A button to select a Piece"""
    def __init__(self, rect: Rect, _piece: Piece, _id=None) -> None:
        super().__init__(rect, _id)
        self.piece = _piece
        self.selected = False

    def handle_click(self, *args, **kwargs):
        return self

    def draw_self(self, rect: Rect, context: Context = None):
        if self.selected:
            stddraw.setPenColor(Colors.WHITE.clerp(stddraw.GREEN, 0.6))
            stddraw.filledCircle(*rect.center,rect.width/2.2)
        stddraw.picture(
            pic=PIECE_IMAGE_FILES[self.piece.canonical()],
            x=rect.center.x,
            y=rect.center.y,
        )


class PieceSelector(AppWidget):
    """Holds a PieceButton for each Piece to allow selecting"""
    def __init__(self, rect, _id: str = None) -> None:
        super().__init__(rect, _id)
        piece_count = len(PIECE_IMAGE_FILES)
        for i, name in enumerate(PIECE_IMAGE_FILES):
            self.register(
                PieceButton(
                    Rect.from_center(
                        Point(
                            0.5 + 0.2 * ((i % 2) * 2 - 1),
                            1 - (i - i % 2 + 1) / (piece_count),
                        ),
                        0.45,
                        2 / piece_count,
                    ),
                    Piece.from_str(name).unwrap(),
                    _id=f"piece_button_{name}",
                )
            )


class BoardConstructor(AppWidget):
    """A widget for contructing a Board layout"""
    def __init__(self, rect, board_width, _id: str = None) -> None:
        super().__init__(rect, _id)
        self.board = self.register(
            BoardWidget(Rect(0, 0, board_width, 1).inflate(-0.01), _id="play_box")
        )

        build_menu = self.register(Box(Rect(board_width, 0, 1, 1), _id="play_menu_box"))

        build_menu.register(
            Button(
                Rect.from_center(Point(0.5, 0.90), 0.7, 0.075),
                "Confirm",
                ButtonSignal.DONE,
                _id="done_button",
            )
        )

        self.piece_selector = build_menu.register(
            PieceSelector(
                Rect.from_center(Point(0.5, 0.550), 1, 0.525), _id="move_list_box"
            )
        )

        build_menu.register(
            Button(
                Rect.from_center(Point(0.5, 0.2), 0.7, 0.075),
                "Wall",
                ButtonSignal.WALL,
                _id="wall_button",
            )
        )

        build_menu.register(
            Button(
                Rect.from_center(Point(0.5, 0.1), 0.7, 0.075),
                "Standard",
                ButtonSignal.STANDARD_BOARD,
                _id="standard_board_button",
            )
        )


class ObstacleButton(AppWidget):
    """A button to select an obstacle"""
    def __init__(self, rect, obs_signal, _id: str = None) -> None:
        super().__init__(rect, _id)
        self.obs_signal = obs_signal

    def handle_click(self, *args, **kwargs):
        return self.obs_signal

    def draw_self(self, rect: Rect, context: Context = None):
        stddraw.picture(
            pic=OBSTACLE_IMAGE_FILES[self.obs_signal.name],
            x=rect.center.x,
            y=rect.center.y,
        )


class ObstacleSelector(AppWidget):
    """Holds an ObstacleButton for each obstacle to allow selecting one"""
    def __init__(self, rect, _id: str = None) -> None:
        super().__init__(rect, _id)
        self.register(
            ObstacleButton(
                Rect.from_center(Point(0.5, 0.75), 0.9, 0.2),
                ButtonSignal.MINE,
                _id="mine_button",
            )
        )
        self.register(
            ObstacleButton(
                Rect.from_center(Point(0.5, 0.5), 0.9, 0.2),
                ButtonSignal.TRAPDOOR,
                _id="trapdoor_button",
            )
        )
        self.register(
            Button(
                Rect.from_center(Point(0.5, 0.25), 0.9, 0.2),
                "Pass",
                ButtonSignal.PASS,
                _id="skip_button",
            )
        )

    def draw_self(self, rect: Rect, context: Context = None):
        stddraw.setPenColor(Colors.DIALOG_INNER.value)
        stddraw.filledRectangle(*rect.draw_props())


class ObstaclePlacement(AppWidget):
    """A widget to allow placing obstacles on the board"""
    def __init__(self, rect, board_width, _id: str = None) -> None:
        super().__init__(rect, _id)
        self.board = self.register(
            BoardWidget(Rect(0, 0, board_width, 1).inflate(-0.01), _id="play_box")
        )
        menu = self.register(Container(Rect(0, 0, 1, 1)))
        self.obstacle_selector = menu.register(
            ObstacleSelector(Rect(board_width, 0.2, 1, 1), _id="play_menu_box")
        )
        menu.register(Container(Rect(board_width, 0, 1, 0.2))).register(
            Button(
                Rect.from_center(Point(0.5, 0.5), 0.8, 0.8),
                "Skip",
                ButtonSignal.SKIP,
                _id="skip_button",
            )
        )


class ReplayArea(AppWidget):
    """A widget to display a replay"""
    def __init__(self, rect, board_width, _id: str = "", **props) -> None:
        super().__init__(rect, _id, **props)
        self.board = self.register(
            BoardWidget(
                Rect.from_center(Point(0.5, 0.5), board_width, 1).inflate(-0.01),
                _id="play_box",
            )
        )
        self.register(
            Button(
                Rect.from_center(Point(0.05, 0.5), 0.08, 0.8),
                "<",
                ButtonSignal.PREV,
                _id="prev_button",
            )
        )
        self.register(
            Button(
                Rect.from_center(Point(0.95, 0.5), 0.08, 0.8),
                ">",
                ButtonSignal.NEXT,
                _id="next_button",
            )
        )
        

class PlayArea(AppWidget):
    """The main play area"""
    def __init__(self, rect, board_width, _id: str = None) -> None:
        super().__init__(rect, _id)
        self.board = self.register(
            BoardWidget(Rect(0, 0, board_width, 1).inflate(-0.01), _id="play_box")
        )

        play_menu = self.register(Box(Rect(board_width, 0, 1, 1), _id="play_menu_box"))

        self.move_list = play_menu.register(
            MoveList(Rect(0, 0.6, 1, 1), _id="move_list_box")
        )

        button_box = play_menu.register(Box(Rect(0, 0, 1, 0.6), _id="button_box"))

        buttons = [
            ("Wall", ButtonSignal.WALL),
            ("Undo", ButtonSignal.UNDO),
            ("Redo", ButtonSignal.REDO),
            ("Menu", ButtonSignal.MENU),
        ]
        slots = len(buttons)
        for i, (name, signal) in enumerate(buttons):
            button_box.register(
                Button(
                    Rect.from_center(
                        Point(0.5, (slots - i - 0.5) / slots * 0.8 + 0.1), 0.7, 0.15
                    ),
                    name,
                    signal,
                    _id=f"play_button_{signal.name}",
                )
            )

    def draw_self(self, rect: Rect, context: Context = None):
        stddraw.setPenColor(stddraw.BLACK)
        stddraw.filledRectangle(*rect.draw_props())


class WallPlacerButton(AppWidget):
    """A button to place a wall"""
    def __init__(self, wall, pos, _id: str = "", **props) -> None:
        square_rect = Rect.from_center(
            Point((pos.x + 0.5) / 8, (pos.y + 0.5) / 8), 1.01 / 8, 1.01 / 8
        )
        if wall == Wall.SOUTH:
            button_rect = Rect.from_center(
                Point(square_rect.center.x, square_rect.y1), 1.01 / 8, 0.101 / 8
            )
        elif wall == Wall.WEST:
            button_rect = Rect.from_center(
                Point(square_rect.x1, square_rect.center.y), 0.101 / 8, 1.01 / 8
            )
        super().__init__(button_rect, _id, **props)
        self.wall = wall
        self.pos = pos

    def draw_self(self, rect: Rect):
        stddraw.setPenColor(Colors.MOVE_OVERLAY.value)
        stddraw.filledRectangle(*rect.draw_props())

    def __str__(self) -> str:
        return super().__str__() + f"<{self.wall.name} {self.pos.canonical()}>"

    def handle_click(self, x: float, y: float, _rect=None, depth: int = 0):
        return self


class WallPlacer(AppWidget):
    """An overlay on the board to place walls"""
    def __init__(self, rect, _id: str = "", **props) -> None:
        super().__init__(rect, _id, **props)

        for pos in Position.all():
            if pos.x > 0 and pos.y > 0:
                for wall in [Wall.WEST, Wall.SOUTH]:
                    self.register(WallPlacerButton(wall, pos))
            elif pos.x > 0:
                self.register(WallPlacerButton(Wall.WEST, pos))
            elif pos.y > 0:
                self.register(WallPlacerButton(Wall.SOUTH, pos))



class SettingsMenu(AppWidget):
    """The settings menu"""
    def __init__(self, rect, _id: str = "") -> None:
        super().__init__(rect, _id)
        self.register(BoardBackground(Rect(0, 0, 1, 1), _id="bg"))
        inner_box = self.register(Box(Rect(0.1, 0.1, 0.9, 0.9), _id="inner_box"))
        inner_box.register(
            Label(
                Rect.from_center(Point(0.5, 0.9), 1, 0.2),
                "Settings",
                _id="settings_title",
            )
        )

        self.overlay_check = inner_box.register(
            CheckBox(
                Rect.from_center(Point(0.2, 0.7), 0.07, 0.07),
                "Show Move Overlay",
                initial_state=SETTINGS["move_overlay"],
                _signal=ButtonSignal.MOVE_OVERLAY_TOGGLE,
                _id="move_overlay_checkbox",
            )
        )

        self.animation_check = inner_box.register(
            CheckBox(
                Rect.from_center(Point(0.2, 0.6), 0.07, 0.07),
                "Animated Moves",
                initial_state=SETTINGS["move_animation"],
                _signal=ButtonSignal.MOVE_OVERLAY_TOGGLE,
                _id="move_animation_checkbox",
            )
        )

        inner_box.register(
            Button(
                Rect.from_center(Point(0.33, 0.1), 0.3, 0.15),
                "Return",
                ButtonSignal.RETURN,
                _id="return_button",
            )
        )

        inner_box.register(
            Button(
                Rect.from_center(Point(0.66, 0.1), 0.3, 0.15),
                "Credits",
                ButtonSignal.CREDITS,
                _id="credits_button",
            )
        )


class AppDelegate(AppWidget):
    """The lowest level widget, which handles click delegation, draw and update calls, and is never removed."""
    def draw_self(self, rect: Rect, context: Context = None):
        stddraw.setPenColor(stddraw.BLACK)
        stddraw.filledRectangle(*rect.draw_props())


class App:
    """A class that handles the main loop of the app"""

    def __init__(self, size) -> None:
        self.size = size
        """The size of the app"""
        AppWidget.DEFAULTS[
            "font-weight"
        ] = size.font  # sets this globally as the default font size
        self.current_game: game.Game = None
        """The game currently being played"""
        self.root: AppDelegate = AppDelegate(
            Rect(0, 0, self.size.width, self.size.height), _id="root"
        )
        """The root widget of the app"""
        self.move_queue: movehandler.MoveQueue = movehandler.MoveQueue()
        """The queue of moves to be executed"""
        
        # initialise the window
        self.init_size()

    def __call__(self, *args, **kwargs):
        self.run()

    def run(self):
        """Starts the app"""
        self.start_menu()

    def init_size(self):
        """Initialise the size of the window, the scale, and the font
        """
        stddraw.setCanvasSize(self.size.width, self.size.height)
        stddraw.setXscale(0, self.size.width)
        stddraw.setYscale(0, self.size.height)
        stddraw.setFontFamily("Consolas")
        stddraw.setFontSize(self.size.font)
        stddraw.show(0)

    def await_click(self, timeout: float = None):
        """Waits for a click, and returns the result of the click

        If timeout is specified, will return None if no click is received within the timeout

        Args:
            timeout (float, optional): The maximum time to wait for a click. Defaults to None.

        Returns:
            Any: The result of the click
        """
        
        start = stddraw.time.perf_counter()

        # wait for a click
        while not stddraw.mousePressed():
            # check if the timeout has been reached
            if (
                timeout is not None
                and stddraw.time.perf_counter() - start > timeout * 1000
            ):
                # timeout reached, return None
                return None
            # brief pause to keep the window alive
            stddraw.show(1 / REFRESH_RATE * 1000)

        # get the coordinates of the click
        x, y = stddraw.mouseX(), stddraw.mouseY()

        # recursively handle the click
        res = self.root.handle_click(x, y)

        # print debug info
        if DEBUG_FLAGS & DebugFlags.CLICK:
            print(f"Clicked ({x}, {y}), yields {res}")

        # return the result of the click
        return res

    def start_menu(self):
        """Present the menu to the user to start a new game"""
        while True:
            click_res = None
            self.root.clear()

            # create the menu widget
            menu = self.root.register(MainMenu(_id="main_menu"))
            menu.button_box.clear()
            buttons = [
                ("New Game", ButtonSignal.NEW_GAME),
                ("Load Game", ButtonSignal.LOAD_GAME),
                ("Settings", ButtonSignal.SETTINGS),
                ("Quit", ButtonSignal.QUIT),
            ]
            slots = len(buttons)
            for button in [
                Button(
                    Rect.from_center(
                        Point(0.5, (slots - i - 0.5) / slots * 0.8 + 0.1), 0.7, 0.15
                    ),
                    name,
                    signal,
                    _id=f"menu_button_{signal.name}",
                )
                for i, (name, signal) in enumerate(buttons)
            ]:
                menu.button_box.register(button)


            # draw the menu
            self.draw()

            # wait for a click
            click_res = self.await_click()

            # handle the click
            if isinstance(click_res, ButtonSignal):
                if click_res == ButtonSignal.NEW_GAME:
                    self.new_game()
                elif click_res == ButtonSignal.LOAD_GAME:
                    self.load_game_menu()
                elif click_res == ButtonSignal.SETTINGS:
                    self.settings_menu()
                elif click_res == ButtonSignal.QUIT:
                    break

    def settings_menu(self):
        """Present the settings menu"""
        global SETTINGS
        self.root.clear()

        # create the settings menu widget
        settings = self.root.register(
            SettingsMenu(
                Rect(0, 0, 1, 1),
                _id="settings_menu",
            )
        )
        while True:
            # draw the menu
            self.draw()

            
            # wait for a click
            click_res = self.await_click()


            # handle the click
            if isinstance(click_res, ButtonSignal):
                if click_res == ButtonSignal.CREDITS:
                    with open("CREDITS.txt") as f:
                        self.dialog(
                            "Credits:",
                            f.read(),
                            [("Return", ButtonSignal.RETURN)],
                            None,
                        )
                elif click_res == ButtonSignal.RETURN:
                    break
            elif isinstance(click_res, CheckBox):
                # if the click was on a checkbox, set all settings to the relevant checkbox state
                SETTINGS["move_overlay"] = bool(settings.overlay_check.state)
                SETTINGS["move_animation"] = bool(settings.animation_check.state)

    def construct_game(self):
        """Construct a new game from scratch"""
        self.root.clear()

        # create the board constructor widget
        self.root.register(
            BoardConstructor(
                Rect(0, 0, 1, 1),
                self.size.height / self.size.width,
                _id="board_constructor",
            )
        )

        

        # initialise the current game
        self.current_game = game.Game(board.Board.empty_board().unwrap())

        # describe mechanics to user
        context = Context(self.current_game, [], [])
        self.update(context)
        self.notice(
            "Constuct your starting board by putting pieces on the board\nSelect Standard for a standard chess board.\nMines and trapdoors can only be\nplaced on standard boards."
        )
        # the most recently selected piece
        selected_piece = None

        # the number of placed walls
        placed_walls = 0

        # the second most recently selected PieceButton
        prev = None

        # begin the main loop
        while True:
            self.update(context)
            self.draw()

            # wait for a click
            click_res = self.await_click()

            # handle the click
            if isinstance(click_res, ButtonSignal):
                if click_res == ButtonSignal.DONE: # board construction finished
                    if placed_walls > 6:
                        self.notice("Too many walls placed!")
                        continue
                    # standarise the status osthat castling rights are consistent with the state of the board
                    self.current_game.board.standardise_status()
                   
                    # distribute the remaining walls among players 
                    self.distribute_walls(placed_walls)

                    # validate the game and board
                    validation_res = self.current_game.validate()

                    # if the validation fails, notify the user and continue, else break from the loop
                    if isinstance(validation_res, Failure):
                        self.notice(f"Invalid board\n{validation_res.unwrap()}")
                        continue
                    else:
                        starting_player = self.dialog(
                            "Starting player",
                            "Select the starting player:",
                            [("Black", ButtonSignal.BLACK), ("White", ButtonSignal.WHITE)]
                        )
                        if starting_player == ButtonSignal.BLACK:
                            self.current_game.board.state.player = Player.BLACK
                        elif starting_player == ButtonSignal.WHITE:
                            self.current_game.board.state.player = Player.WHITE
                            
                        break

                elif click_res == ButtonSignal.STANDARD_BOARD: # create a standard board
                    self.current_game = game.Game(board.Board.standard_board().unwrap())
                    # begin the setup phase
                    self.setup_phase()
                    break

                elif click_res == ButtonSignal.WALL:
                    # check that the player can play a wall
                    if sum(self.current_game.board.state.walls.values())> 0:
                        # create the wall placement widget
                        placer = self.root.get_by_id("play_box").register(WallPlacer(Rect(0, 0, 1, 1)))
                        while True:
                            self.draw()

                            # wait for a click
                            click_res = self.await_click()

                            # handle the click
                            if isinstance(click_res, WallPlacerButton): # overlay clicked
                                if self.current_game.board[click_res.pos].walls & click_res.wall: 
                                    # remove the wall
                                    placed_walls -= 1
                                    self.current_game.board[click_res.pos].walls &= ~click_res.wall
                                    self.current_game.board[click_res.wall.blocking(click_res.pos)].walls &= ~click_res.wall.alternate()
                                else:
                                    # add the wall
                                    placed_walls += 1
                                    self.current_game.board[click_res.pos].walls |= click_res.wall
                                    self.current_game.board.normalise_walls()
                                    # remove the wall placement widget
                                self.root.get_by_id("play_box").deregister(placer)
                                break
                            
                            elif isinstance(click_res, ButtonSignal): # button clicked
                                # the only button that can be clicked is the wall button, to close the wall overlay
                                if click_res == ButtonSignal.WALL:
                                    self.root.get_by_id("play_box").deregister(placer)
                                    break
                    else:
                        # inform player that they have no walls remaining
                        self.notice(
                            f"No walls remaining for player {self.current_game.board.state.player.name.capitalize()}!"
                        )
            
            elif isinstance(click_res, BoardTile): # tile selected
                # if a piece has been selected, place that piece, else clear that tile
                if selected_piece:
                    self.current_game.board[click_res.pos].contents = selected_piece
                else:
                    self.current_game.board[click_res.pos].contents = None
            
            elif isinstance(click_res, PieceButton): # piece selected
                # if the piece selected is the same as the last selected, clear the selection
                # else, select the new piece
                # in both cases, update the selected properties to highlight only the selected piece
                if selected_piece == click_res.piece:
                    selected_piece = None
                    click_res.selected = False
                    prev = None
                else:
                    selected_piece = click_res.piece
                    click_res.selected = True
                    if prev:
                        prev.selected = False
                    prev = click_res
                
    def distribute_walls(self, placed_walls):
        
        remaining_walls = 6-placed_walls

        # check that there are walls to distribute
        if remaining_walls == 0:
            self.current_game.board.state.walls = {
                Player.WHITE:0,
                Player.BLACK:0
            }
            return

        constructor = self.root.get_by_id("play_box")
        box = constructor.register(
            Box(Rect(0.10,0.3,0.9,0.7))
        )
        box.register(
            Label(
                Rect.from_center(Point(0.5, 0.9), 1, 0.2),
                f"Distribute {remaining_walls} remaining walls"
            )
        )
        box.register(
            Label(
                Rect.from_center(Point(0.1, 0.4), 0.2, 0.8),
                "White"
            )
        )
        dist_cont = box.register(
            Container(
                Rect(0.2,0.0,0.8,0.8)
            )
        )
        box.register(
            Label(
                Rect.from_center(Point(0.9, 0.4), 0.2, 0.8),
                "Black"
            )
        )

        for i in range(remaining_walls + 1):
            dist_cont.register(
                Button(
                    Rect.from_center(Point(0.1 + (i)*0.8/remaining_walls, 0.5), 0.15, 0.2),
                    "<" if i<remaining_walls/2 else (">" if i>remaining_walls/2 else "O"),
                    i
                )
            )
        white_walls = 0
        while True:
            self.draw()
            click_res = self.await_click()
            if isinstance(click_res, int):
                white_walls = click_res
                accept = self.dialog(
                    "Confirm",
                    f"White: {white_walls}\nBlack: {remaining_walls - white_walls}",
                    [("Accept", ButtonSignal.ACCEPT), ("Cancel", ButtonSignal.DECLINE)],
                    None,
                )
                if accept == ButtonSignal.ACCEPT:
                    self.current_game.board.state.walls = {
                        Player.WHITE:white_walls,
                        Player.BLACK:remaining_walls - white_walls
                    }
                    break
                else:
                    continue

        

    
    def setup_phase(self):
        """Allow the user to place obstacles on the board as part of the setup phase"""
        remaining_moves = 4
        # Generate a list of all the spaces each obstacle can be placed
        mine_moves = [
            PlaceMine(p, P(x, y + 3))
            for x in range(8)
            for y in range(2)
            for p in [Player.WHITE, Player.BLACK]
        ]
        trap_moves = [
            PlaceTrapdoor(p, P(x, y + 2))
            for x in range(8)
            for y in range(4)
            for p in [Player.WHITE, Player.BLACK]
        ]


        self.root.clear()

        # create the obstacle placemnet widget
        self.root.register(
            ObstaclePlacement(
                Rect(0, 0, 1, 1),
                self.size.height / self.size.width,
                _id="obstacle_placement",
            )
        )

        # the most recently selected obstacle
        selected_obstacle = None

        while remaining_moves > 0:
            potential_moves = (
                []
                if selected_obstacle is None
                else mine_moves
                if selected_obstacle == ButtonSignal.MINE
                else trap_moves
            )
            self.update(Context(self.current_game, potential_moves, []))
            self.draw()
            click_res = self.await_click()

            if isinstance(click_res, ButtonSignal):
                if click_res == ButtonSignal.PASS: # player has passed on their opportunity to place an obstacle
                    # push a null move to the game
                    self.move_queue.push(NullMove(self.current_game.board.state.player))
                    self.play_next()
                    remaining_moves -= 1
                elif click_res == ButtonSignal.SKIP: # user has decided to progress
                    # ensure that both players have had the same number of placement opportunities
                    if remaining_moves % 2 != 0:
                        self.notice("Both players must make the same number of placements/passes!")
                    else:
                        break
                else:
                    # obstacle selected
                    selected_obstacle = click_res

                    # check that the player can place one of the selected obstacles
                    if (
                        self.current_game.board.initial_moves[
                            self.current_game.board.state.player
                        ][selected_obstacle.name.lower() + "s"]
                        == 0
                    ):
                        self.notice(
                            f"No more obstacles of that type for player {self.current_game.board.state.player.name.capitalize()}"
                        )
                        selected_obstacle = None

            elif isinstance(click_res, BoardTile) and selected_obstacle: # place the obstacle
                # get the current player
                player = self.current_game.board.state.player

                # push the required move to the game and update initial move counts
                if selected_obstacle == ButtonSignal.MINE:
                    self.move_queue.push(PlaceMine(player, click_res.pos))
                elif selected_obstacle == ButtonSignal.TRAPDOOR:
                    self.move_queue.push(PlaceTrapdoor(player, click_res.pos))
                selected_obstacle = None
                remaining_moves -= 1
                self.play_next()

    def new_game(self):
        """Present the menu to the user to start a new game
        
        (DEFUNCT: Only local play is currently implemented)
        """
        # construct the game
        self.construct_game()

        # begin play loop
        self.play()

    
    def load_game_menu(self):
        """Presents the load game menu to the user"""
        while True:
            self.root.clear()

            # create the load game widget
            menu_box = self.root.register(MainMenu(_id="new_game_menu")).button_box
            buttons = [
                ("From File", ButtonSignal.FROM_FILE),
                ("Replay", ButtonSignal.REPLAY),
                ("Return", ButtonSignal.RETURN),
            ]
            slots = len(buttons)
            for button in [
                Button(
                    Rect.from_center(
                        Point(0.5, (slots - i - 0.5) / slots * 0.8 + 0.1), 0.7, 0.15
                    ),
                    name,
                    signal,
                )
                for i, (name, signal) in enumerate(buttons)
            ]:
                menu_box.register(button)

            self.draw()

            # wait for a click
            click_res = self.await_click()

            # handle the click
            if isinstance(click_res, ButtonSignal):
                if click_res == ButtonSignal.FROM_FILE: # open a board file
                    # attempt to get a file from the user
                    try:
                        board_file = askopenfile(
                            filetypes=[
                                ("Board Files", "*.board"),
                                ("Board Files", "*.txt"),
                                ("All Files", "*.*"),
                            ],
                            mode="r",
                        )
                    except Exception:
                        self.notice("Invalid file!")
                        continue

                    # ensure that a valid file was selected
                    if board_file is None:
                        self.notice("Invalid file!")
                        continue

                    # read in the file and strip comments
                    board_str = [
                        line
                        for line in board_file.read().split("\n")
                        if not (line.startswith("%") or line == "")
                    ]

                    # create the board
                    board_res = board.Board.from_strs(board_str)

                    # ensure that the board is valid, and if so, instantiae the game and play
                    if isinstance(board_res, Failure):
                        self.notice(f"Invalid board!\n{board_res.unwrap()}")
                        continue
                    elif isinstance(board_res, Success):
                        self.current_game = game.Game(board_res.unwrap())
                        self.current_game.set_move_source(
                            movehandler.QueuedMoveSource(self.move_queue)
                        )
                        self.play()

                elif click_res == ButtonSignal.REPLAY: # replay a saved game
                    # attempt to get the board and game files from the user
                    self.notice("Select a board file to replay from", timeout=0)
                    board_file = askopenfile(title="Select a board file", filetypes=[("Board Files", "*.board"),("All Files", "*.*")])
                    self.notice("Select a move file to replay from", timeout=0)
                    move_file = askopenfile(title="Select a gem file", filetypes=[("Move Files", "*.game"),("All Files", "*.*")])
                    
                    # ensure files are valid
                    if board_file is None or move_file is None:
                        self.notice("Invalid file!")
                        continue

                    # read in the board file and remove comments
                    board_str = [
                        line
                        for line in board_file.read().split("\n")
                        if not (line.startswith("%") or line == "")
                    ]

                    # validate the board
                    board_res = board.Board.from_strs(board_str)
                    if isinstance(board_res, Failure):
                        self.notice(f"Invalid board!\n{board_res.unwrap()}")
                        continue
                    elif isinstance(board_res, Success):
                        self.current_game = game.Game(board_res.unwrap())

                    # set the move source to be the move file
                    self.current_game.set_move_source(movehandler.FileSource(move_file))

                    # confirmdetials with user
                    self.notice(
                        f"Replaying\n'{os.path.relpath(move_file.name)}'\non board\n'{os.path.relpath(board_file.name)}'"
                    )

                    # close the board file, as it is no longer needed
                    board_file.close()

                    # begin the replay
                    self.replay()

                    # close the move file as it is no longer needed
                    move_file.close()

                elif click_res == ButtonSignal.RETURN: # return to main menu
                    return

    def play(self):
        """Plays the game from the currently loaded game"""
        self.root.clear()

        # initialise the move queue
        self.current_game.set_move_source(movehandler.QueuedMoveSource(self.move_queue))

        # create the play area widget
        self.root.register(
            PlayArea(
                Rect(0, 0, 1, 1), self.size.height / self.size.width, _id="play_area"
            )
        )

        # the position moves are coming from
        move_origin = None

        context = Context(self.current_game, [], [])
        self.update(context)

        # announce the first player
        self.announce_start()


        while True:
            self.update(context=context)
            self.draw()
            player = context.game.board.state.player
            pushed_move = False

            # wait for a click
            click_res = self.await_click()

            # handle the click
            if isinstance(click_res, BoardTile): # clicked the board
                # get the contents of the clicked position
                contents = context.game.board[click_res.pos].contents

                # if a move construction is in progress, and the click position is a valid move, create and push the move
                if move_origin is not None and click_res.pos in list(
                    map(lambda x: x.destination, context.potential_moves)
                ):  
                    # semipromotions are used do describe the motion, but not the promotion made by a pawn
                    if isinstance(click_res.potential_move, SemiPromotion):
                        # if the returned move is a semi promotion, complete the promotion and create the move
                        promotion = self.ask_promotion(click_res.potential_move.player)
                        new_move = Promotion.from_semi(
                            click_res.potential_move, promotion
                        )
                    else:
                        new_move = click_res.potential_move

                    # push the move to the game
                    self.move_queue.push(new_move)
                    pushed_move = True

                # select a piece
                elif contents is not None:
                    move_origin = click_res
                    allowed_moves = context.game.board.get_moves(
                        click_res.pos, strict=True
                    )
                    context.potential_moves = allowed_moves
                # deselect a piece
                else:
                    context.potential_moves = []
                    move_origin = None

            elif isinstance(click_res, ButtonSignal): # menu button clicked
                if click_res == ButtonSignal.WALL: # player wants to play a wall
                    # check that the player can play a wall
                    if (
                        self.current_game.board.state.walls[
                            self.current_game.board.state.player
                        ]
                        > 0
                    ):
                        # show the wall placement overlay
                        if self.place_wall():
                            # if a wall was placed, inform the player of their remaining walls
                            self.notice(
                                f"{self.current_game.board.state.walls[self.current_game.board.state.player.opponent()]} walls remaining for player {self.current_game.board.state.player.opponent().name.capitalize()}"
                            )
                            pushed_move = True
                    else:
                        # inform player that they have no walls remaining
                        self.notice(
                            f"No walls remaining for player {self.current_game.board.state.player.name.capitalize()}!"
                        )
                elif click_res == ButtonSignal.UNDO: # undo the most recent move
                    self.current_game.undo()
                elif click_res == ButtonSignal.REDO: # redo the most recent undo
                    self.current_game.redo()
                elif click_res == ButtonSignal.MENU: # open the in-game menu
                    menu_result = self.ingame_menu()
                    if menu_result == ButtonSignal.QUIT: # quit the game
                        return
                    elif menu_result == ButtonSignal.SAVE_GAME: # save the game
                        self.save_game()
            
            if pushed_move:
                # clear the potential moves and update in preparation for the move animation
                context.potential_moves = []
                self.update(context)

                # tell the game to pull the next move
                play_res = self.play_next()

                # check that the move is valid
                if isinstance(play_res, Failure) or play_res.unwrap() is None:
                    # here to ensure that only valid moves can be played, but shouldn't eveer happen
                    self.notice(f"Invalid move: {play_res.unwrap()}")
                elif isinstance(play_res, Success):
                    self.update(context)
                    self.draw()
                    signals = play_res.unwrap()
                    if (
                        signals & GameSignal.ILLEGAL_MOVE
                    ):  # same as above
                        self.notice(f"Invalid move: {play_res.unwrap()}")
                    if signals & GameSignal.CHECKMATE:
                        # player has been checkmated
                        self.win(player, GameSignal.CHECKMATE)
                        return
                    
                    if signals & GameSignal.STALEMATE:
                        self.notice("The game has stalemated!")
                        return

                    if signals & GameSignal.CHECK:
                        # player is in check
                        pass
                    if signals & (
                        GameSignal.FIFTY_AVAILABLE | GameSignal.THREEFOLD_AVAILABLE
                    ):
                        # a draw is available

                        # allow the player to offer a draw
                        draw_accepted = self.ask_offer_draw(signals & (
                        GameSignal.FIFTY_AVAILABLE ^ GameSignal.THREEFOLD_AVAILABLE
                    ))

                        # if the draw is accepted, notify and quit
                        if draw_accepted == ButtonSignal.ACCEPT:
                            self.notice("Draw has been accepted.")
                            return
                        
                    # if a mine was detonated, run the mine detonation animation
                    if self.current_game.board.mine_detonated:
                        self.mine_animation(click_res.pos)

    def save_game(self):
        """Presents a dialog to save the board and game to a file"""
        # attempt to get a file to save the board to
        self.notice("Select a file to save the board to", timeout=0)
        while True:
            save_file = asksaveasfile(
                filetypes=[("Board file", "*.board")], mode="w", title="Save board"
            )
            if save_file is None:
                self.notice("Invalid file!")
                continue
            self.notice(f"Saving to {os.path.relpath(save_file.name)}", timeout=1)
            save_file.write(self.current_game.board.canonical())
            save_file.close()
            break

        # attempt to get a file to save the moves to
        self.notice("Select a file to save the moves to", timeout=0)
        while True:
            save_file = asksaveasfile(
                filetypes=[("Game file", "*.game")], mode="w", title="Save game"
            )
            if save_file is None:
                self.notice("Invalid file!")
                continue
            self.notice(f"Saving to {os.path.relpath(save_file.name)}", timeout=1)
            save_file.writelines(
                "\n".join(move.canonical() for move in self.current_game.history.moves)
            )
            break

    def mine_animation(self, pos):
        """Displays the mine detonation animation"""
        animation = self.root.get_by_id("play_box").register(MineAnimation(pos))
        while not animation.complete:
            self.draw()
            animation.progress(2)
            stddraw.show(0.1)
        stddraw.show(50)
        self.root.get_by_id("play_box").deregister(animation)
        self.draw()

    def place_wall(self):
        """Allow the user to place a wall by displaying the wall placement overlay"""

        # create the wall placement widget
        placer = self.root.get_by_id("play_box").register(WallPlacer(Rect(0, 0, 1, 1)))
        while True:
            self.draw()

            # wait for a click
            click_res = self.await_click()

            # handle the click
            if isinstance(click_res, WallPlacerButton): # overlay clicked
                # create and push the wall placement move
                self.move_queue.push(
                    PlaceWall(
                        self.current_game.board.state.player,
                        click_res.pos,
                        click_res.wall,
                    )
                )

                # remove the wall placement widget
                self.root.get_by_id("play_box").deregister(placer)
                return True
            
            elif isinstance(click_res, ButtonSignal): # button clicked
                # the only button that can be clicked is the wall button, to close the wall overlay
                if click_res == ButtonSignal.WALL:
                    self.root.get_by_id("play_box").deregister(placer)
                return False

    def ingame_menu(self):
        """Present the in-game menu to the user"""
        # create the menu widget
        menu_box = self.root.register(Box(Rect.from_center(Point(0.5, 0.5), 0.7, 0.7)))

        menu_box.register(
            Label(
                Rect.from_center(Point(0.5, 0.9), 0.8, 0.1),
                "Menu",
                _id="menu_label",
            )
        )
        buttons = [
            ("Quit game", ButtonSignal.QUIT),
            ("Save game", ButtonSignal.SAVE_GAME),
            ("Return", ButtonSignal.RETURN),
        ]
        slots = len(buttons)
        for i, (name, signal) in enumerate(buttons):
            menu_box.register(
                Button(
                    Rect.from_center(Point(0.5, (slots - i) * 0.75 / slots), 0.7, 0.15),
                    name,
                    signal,
                    _id=f"menu_button_{signal.name}",
                )
            )

        while True:
            self.draw()

            # wait for a click
            click_res = self.await_click()

            # return the click if its a button, ignore otherwise
            if isinstance(click_res, ButtonSignal):
                self.root.deregister(menu_box)
                self.draw()
                return click_res

    def ask_promotion(self, player):
        """Display the promotion selection dialog to the user"""

        # create the promotion selection dialog
        play_box = self.root.get_by_id("play_box")
        box = play_box.register(Box(Rect.from_center(Point(0.5, 0.5), 0.8, 0.5)))
        box.register(
            Label(
                Rect.from_center(Point(0.5, 0.8), 0.8, 0.1),
                "Select a promotion",
                _id="promotion_label",
            )
        )
        piece_str = "qbrn"
        for i, piece in enumerate(
            piece_str.upper() if player == Player.WHITE else piece_str
        ):
            box.register(
                PieceButton(
                    Rect.from_center(Point(0.2 + i * 0.2, 0.5), 0.2, 0.3),
                    _piece=Piece.from_str(piece).unwrap(),
                    _id=f"promotion_button_{piece}",
                )
            )


        self.draw()
        while True:
            # wait for a click
            click_res = self.await_click()

            # return the selected piece class
            if isinstance(click_res, Piece):
                play_box.deregister(box)
                return click_res.__class__

    def replay(self):
        """Replay a game from a file
        
        The game should already be loaded, with the source set to a FileSource"""
        context = Context(self.current_game, [], [])
        self.root.clear()

        # create the replay widget
        self.root.register(
            ReplayArea(
                Rect(0, 0, 1, 1), self.size.height / self.size.width, _id="play_area"
            )
        )
        self.update(context)

        # describe mechanics to user
        self.notice("Replay starting...\nClick anywhere on the board to pause replay,\n and again to resume.\n Use the buttons on the left and right to step through the game.", timeout=1)
        
        # announce the beginning of the game
        self.announce_start()

        # while there are still unplayed moves in the file, play them (without animations)
        while not self.current_game.source.exhausted:
            res = self.play_next(animate=False)

            # if the move file contains invalid moves, notify and exit
            if isinstance(res, Failure):
                self.notice(f"Invalid move!\n{res.unwrap()}\nTerminating replay.")
                break
            self.update(context)
            self.draw()

            # wait for a clik, or for 0.1 seconds to pass
            click_res = self.await_click(timeout=0.1)
            if click_res: # if a click happened, handle it
                if isinstance(click_res, ButtonSignal): # next/prev buttons clicked
                    while click_res in [ButtonSignal.NEXT, ButtonSignal.PREV]:
                        if click_res == ButtonSignal.NEXT: # step forwards through the game
                            # if moves have been undone, via stepping backwards, redo those, else play the next move
                            if len(self.current_game.redo_stack) > 0:
                                self.current_game.redo()
                            elif not self.current_game.source.exhausted:
                                # play the next move
                                res = self.play_next(animate=False)

                                # same as above
                                if isinstance(res, Failure):
                                    self.notice(f"Invalid move!\n{res.unwrap()}\nTerminating replay.")
                                    break
                            else: # no moves left to play
                                break

                        elif click_res == ButtonSignal.PREV: # undo the latest move if possible
                            self.current_game.undo()
                        self.update(context)
                        self.draw()

                        # wait for click
                        # if its a button press, the above logic for stepping will run again, else it will return to the main replay loop
                        click_res = self.await_click()
                else:
                    self.await_click()
        else:
            self.notice("Game complete!")

    def announce_start(self):
        """Announces the start of the game, and who is to play first based on the current game state"""
        self.dialog(
            "Game starting!",
            f"{'<NO GAME>' if not self.current_game else self.current_game.board.state.player.name.capitalize()} to start.",
            [],
            _timeout=2,
        )

    def update(self, context):
        """Recursively updates the widget hierarchy"""
        self.root.update(context)

    def draw(self):
        """Recursively draws the widget hierarchy"""
        if DEBUG_FLAGS & DebugFlags.HIERARCHY:
            self.root.print_hierarchy()
        self.root.draw_debug(self.root.rect)
        time_tree = self.root.draw(self.root.rect)
        
        if DEBUG_FLAGS & DebugFlags.TIME:
            print_time_tree(time_tree)
        stddraw.show(0)

    def play_next(self, animate = True):
        """Plays the next move on the currently loaded game

        Returns:
            Result[GameSignal]: The result of the move
        """
        if animate and SETTINGS["move_animation"]:
            move = self.move_queue.top()
            if isinstance(move, Move) and not isinstance(move, (NullMove, PlaceMine, PlaceTrapdoor, PlaceWall)):
                start = move.origin
                end = move.destination
                piece = self.current_game.board[move.origin].contents
                box = self.root.get_by_id("play_box")
                animation = box.register(
                    PieceMoveAnimation(start, end, piece)
                )
                while not animation.complete:
                    self.draw()
                    animation.progress(3)
                    stddraw.show(0)
                stddraw.show(50)
                box.deregister(animation)
        return self.current_game.play_next()

    def dialog(
        self,
        title,
        text,
        buttons: List[Tuple[str, ButtonSignal]],
        _timeout=None,
    ):
        """Displays a modular dialog box to the user

        Args:
            title (str): The title of the dialog box
            text (str): The text content of the dialog box
            buttons (List[Tuple[str, ButtonSignal]]): The buttons to display
            _timeout (None|flaot, optional): The timeout before the dialog disappears. Defaults to None.

        Returns:
            ButtonSignal|None: The button signal associated with the clicked button, or None if no buttons were specified/timeout was reached
        """
        lines = text.split("\n")
        notice_box = self.root.register(
            Box(
                Rect.from_center(
                    Point(0.5, 0.5),
                    0.9,
                    min(0.2 + 0.1 * len(lines) + 0.2 * bool(buttons), 0.95),
                ),
                _id="notice_box",
            )
        )
        notice_box.register(
            Label(
                Rect.from_center(Point(0.5, 0.875), 1, 0.25), title, _id="dialog_title"
            )
        ).set_prop("font-weight", int(self.size.font * 1.2))
        for i, line in enumerate(lines):
            label = notice_box.register(
                Label(
                    Rect.from_center(
                        Point(0.5, 0.50 + (len(lines) // 2 - i) * 0.5 / len(lines)),
                        1,
                        0.1,
                    ),
                    line,
                    _id=f"dialog_text_{i}",
                )
            )
            if len(lines) > 10:
                label.set_prop("font-weight", int(self.size.font * 0.75))

        for i, (b_text, b_signal) in enumerate(buttons):
            notice_box.register(
                Button(
                    Rect.from_center(
                        Point(0.1 + (i+0.5)*0.8/len(buttons), 0.125),
                        min(0.2, (0.9 / len(buttons))),
                        0.15,
                    ),
                    b_text,
                    b_signal,
                )
            )
        self.draw()
        while True:
            click_res = self.await_click(timeout=_timeout)
            if not buttons:
                break
            elif isinstance(click_res, ButtonSignal):
                break
        self.root.deregister(notice_box)
        return click_res

    def notice(self, text: str, timeout=2):
        """Display a simple notice to the user"""
        self.dialog("", text, [], _timeout=timeout)

    def win(self, player: Player, reason: GameSignal):
        """Announce a winner to the user"""
        self.dialog("We have a winner!", f"Player {player.name} has won!", [])

    def ask_offer_draw(self, reason):
        reason_str = "threefold repetition" if reason == GameSignal.THREEFOLD_AVAILABLE else "fifty-move rule"
        ask = self.dialog(
            "Draw Available",
            f"A draw is available due to {reason_str}.\n Would you like to propose a draw?",
            [("Yes", ButtonSignal.ACCEPT), ("No", ButtonSignal.DECLINE)],
        )
        return self.offer_draw(reason_str) if ask == ButtonSignal.ACCEPT else ask

    def offer_draw(self, reason_str):
        """Offer a draw to the user"""
        return self.dialog(
            "Draw Offer",
            f"A draw due to {reason_str} has been offered.\n Would you like to accept?",
            [("Accept", ButtonSignal.ACCEPT), ("Decline", ButtonSignal.DECLINE)],
        )


if __name__ == "__main__":
    import re


    # parse cmdline args
    size = APP_SIZES[2]
    args = sys.argv[1:]
    for arg in args[:]:
        if re.match(r"-d[\w]+", arg):
            if "w" in arg:
                DEBUG_FLAGS |= DebugFlags.WIDGET
            if "h" in arg:
                DEBUG_FLAGS |= DebugFlags.HIERARCHY
            if "c" in arg:
                DEBUG_FLAGS |= DebugFlags.CLICK
            if "i" in arg:
                DEBUG_FLAGS |= DebugFlags.INSPECT
            if "t" in arg:
                DEBUG_FLAGS |= DebugFlags.TIME
            args.remove(arg)
        elif re.match(r"-s\d+x\d+", arg):
            spec = arg.lstrip("-s").split("x")
            size = _AppSize(int(spec[0]), int(spec[1]))
            args.remove(arg)
        elif re.match(r"-s\d", arg):
            size = APP_SIZES[int(arg[2])]
            args.remove(arg)
    if args:
        print("Unrecognised arguments:\n\t-:" + "\n\t-: ".join(map(repr, args)))
    else:
        app = App(size)
        app.run()