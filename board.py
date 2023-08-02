from typing import Iterator, TextIO
from piece import Piece
from common import *
from output import *
from move import Move


class TrapdoorState:
    """The possible states of a trapdoor as an "enum"."""

    NONE = 1
    """No trapdoor"""
    HIDDEN = 2
    """Trapdoor present (Hidden)"""
    OPEN = 3
    """Trapdoor present (Open)"""

    @classmethod
    def hide(cls):
        return cls.HIDDEN

    @classmethod
    def open(cls):
        return cls.OPEN

    @classmethod
    def none(cls):
        return cls.NONE


class Wall:  # TODO: confirm  anything using this now conforms to new behaviour
    """A bitmask class for walls

    By using bitwise operators membership for any of these can be easily checked.
    """

    NONE = 0b0000
    """No walls"""
    NORTH = 0b0001
    """North wall"""
    SOUTH = 0b0010
    """South wall"""
    EAST = 0b0100
    """East wall"""
    WEST = 0b1000
    """West wall"""

    @staticmethod
    def to_str(walls: int) -> str:
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

    @staticmethod
    def get_wall_direction(_from: tuple[int, int], _to: tuple[int, int]):
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
        match (x1 == x2, y1 == y2):
            # East-West movement
            case (True, False):
                return Wall.SOUTH, Wall.NORTH if y2 > y1 else Wall.NORTH, Wall.SOUTH
            # North-South movement
            case (False, True):
                return Wall.EAST, Wall.WEST if x2 > x1 else Wall.WEST, Wall.EAST
            # Diagonal movement
            case (True, True):
                from_walls = 0b0000
                to_walls = 0b0000
                if y1 > y2:  # Going Northwards
                    from_walls &= Wall.NORTH
                    to_walls &= Wall.SOUTH
                    if x1 > x2:
                        from_walls &= Wall.WEST
                        to_walls &= Wall.EAST
                    else:
                        from_walls &= Wall.EAST
                        to_walls &= Wall.WEST
                else:  # Going Southwards
                    from_walls &= Wall.SOUTH
                    to_walls &= Wall.NORTH
                    if x1 > x2:
                        from_walls &= Wall.WEST
                        to_walls &= Wall.EAST
                    else:
                        from_walls &= Wall.EAST
                        to_walls &= Wall.WEST


class BoardNode:
    """Logical representation of a node on the board.

    Maintains info on mines, trapdoors and pieces on the node.
    """

    def __init__(self, contents: Piece | None, mined: bool, trapdoor: int) -> None:
        self.contents = contents
        """The contents of a tile (`None` or `Piece`)"""
        self.mined = mined
        """Whether there is a mine on this tile"""
        self.trapdoor = trapdoor
        """Whether there is a trapdoor on this tile, and its state"""
        self.walls = Wall.NONE
        """Which walls are present on this tile"""

    def __str__(self) -> str:
        return f"Node({self.contents=}, {self.mined=}, {self.trapdoor=}, {self.walls=})"

    def canonical(self) -> str:
        node_str = ""
        # If there is a piece on the node, add it to the string
        match self.contents:
            case None:
                match (self.trapdoor, self.mined):
                    case (TrapdoorState.HIDDEN, False):
                        node_str += "D"
                    case (TrapdoorState.OPEN, False):
                        node_str += "O"
                    case (TrapdoorState.HIDDEN, True):
                        node_str += "X"
                    case (TrapdoorState.NONE, True):
                        node_str += "M"
                    case (TrapdoorState.NONE, False):
                        node_str += "."
                    case _:
                        raise ValueError(f"Invalid node state: {self}")
            case _:
                node_str += self.contents.canonical()
        # prepend walls to the string
        if self.walls & Wall.SOUTH:
            node_str = f"_{node_str}"
        if self.walls & Wall.WEST:
            node_str = f"|{node_str}"

        return node_str

    @classmethod
    def from_str(cls, char: str) -> Result:
        """Creates a BoardNode from a character.

        Parameters
        ----------
        char : str
            The character to create the node from.

        Returns
        -------
        BoardNode
            The created node.
        """
        # Empty node
        if char[0] == ".":
            return Success(BoardNode(None, False, TrapdoorState.none()))

        # a mine or trapdoor
        elif char[0] in ["D", "O", "M", "X"]:
            match char:
                # hidden trapdoor
                case "D":
                    return Success(BoardNode(None, False, TrapdoorState.hide()))
                # open trapdoor
                case "O":
                    return Success(BoardNode(None, False, TrapdoorState.open()))
                # mine
                case "M":
                    return Success(BoardNode(None, True, TrapdoorState.none()))
                # hidden trapdoor and a mine
                case "X":
                    return Success(BoardNode(None, True, TrapdoorState.hide()))

        # a piece
        # This is evaluated last, so that isupper and islower can be used to check for pieces and dont get caught on mines/trapdoors
        elif char[0].islower():
            return Success(
                BoardNode(Piece.from_str(char[0]), False, TrapdoorState.none())
            )
        elif char[0].isupper():
            return Success(
                BoardNode(Piece.from_str(char[0]), False, TrapdoorState.none())
            )

        # If the character is not recognised, return Failure
        return Failure()


class BoardState:
    """Represents the state of the board during a game of obstacle chess.

    Holds info about:
     - The current player
     - Castling rights
     - En passant
     - Halfmove clock
    """

    def __init__(
        self,
        player: int,
        walls: tuple[int, int],
        castling: tuple[bool, bool, bool, bool],
        enpassant: tuple[int, int] | None,
        clock: int,
    ) -> None:
        self.player = player
        """The current player"""
        self.walls = {Player.WHITE: walls[0], Player.BLACK: walls[1]}
        """The number of walls available to each player"""
        self.castling = {
            Player.WHITE: {"king": castling[0], "queen": castling[1]},
            Player.BLACK: {"king": castling[2], "queen": castling[3]},
        }
        """The players castling rights"""
        self.enpassant = enpassant
        """The current target for an en-passant"""
        self.clock = clock
        """The halfmove clock"""

    def __repr__(self) -> str:
        return f"BoardState({self.player=}, ...)"

    def __str__(self) -> str:
        return repr(self)

    def canonical(self) -> str:
        """Returns a representing the board state in canonical form.

        This is the representation used when writing the game to a file.

        Returns
        -------
        str
            The canonical representation of the board state.
        """
        return " ".join(
            [
                Player.canonical(self.player),
                str(self.walls[Player.WHITE]),
                str(self.walls[Player.BLACK]),
                "+" if self.castling[Player.WHITE]["king"] else "-",
                "+" if self.castling[Player.WHITE]["queen"] else "-",
                "+" if self.castling[Player.BLACK]["king"] else "-",
                "+" if self.castling[Player.BLACK]["queen"] else "-",
                algebraic(*self.enpassant) if self.enpassant else "-",
                str(self.clock),
            ]
        )

    @classmethod
    def from_str(cls, string: str) -> Result:
        """Creates a BoardState from a string.

        The string should be sripped of whitespace.

        Parameters
        ----------
        board : Board
            The board to create the state for.
        string : str
            The string to create the state from.

        Returns
        -------
        BoardState
            The created state.
        """
        blocks = list(string)

        player = Player.from_str(blocks[0])

        walls = tuple(map(int, blocks[1:3]))

        castling = tuple(map(lambda x: x == "+", blocks[3:7]))

        enpassant_str = blocks[7]
        enpassant = None if (enpassant_str == "-") else coords(enpassant_str)

        clock = int(blocks[8])

        return Success(cls(player, walls, castling, enpassant, clock))

    @classmethod
    def standard_state(cls):
        """Generates a standard starting state, as in standard chess"""
        # TODO: how many walls to start with?
        return cls(Player.WHITE, (3, 3), (True, True, True, True), None, 0)


class Board:
    """A representation of the board state.

    Maintains the boards current state, and provides methods for manipulating it.
    """

    def __init__(self, board: list[list[BoardNode]], state: BoardState) -> None:
        # The boards nodes, as a 2D array
        self.__nodes: list[list[BoardNode]] = board
        """The tiles on the board"""
        self.state: BoardState = state
        # Ensure that the walls are normalised
        self.normalise_walls()

    def __getitem__(self, index: tuple[int, int]) -> BoardNode:
        """Returns the node at the given index."""
        return self.__nodes[index[0]][index[1]]

    def __iter__(self) -> Iterator[list[BoardNode]]:
        """Iterates over rows of the boards nodes."""
        yield from self.__nodes
        return StopIteration()

    def __repr__(self) -> str:
        return f"Board({self.state=})"

    def __str__(self) -> str:
        return repr(self)

    def pprint(self) -> str:
        """Returns a pretty-printed version of the board as a single string with newlines.

        Draws the board as a table, with the pieces in their correct positions, with walls, mines and trapdoors marked.

        Parameters
        ----------
        file : TextIO, optional
            _description_, by default sys.stdout
        """
        table: list[list[tuple[BoardNode, str]]] = []
        for i, row in enumerate(self.__nodes):
            table.append([])
            for j, node in enumerate(row):
                table[-1].append((node, algebraic(i, j)))

        string_arr = ["┌────┬────┬────┬────┬────┬────┬────┬────┐"]
        center = ""
        bottom = ""
        for y, row in enumerate(table):
            center = "│"
            bottom = "├" if y < 7 else "└"
            for x, (node, alg) in enumerate(row):
                inside = (
                    node.canonical()[-1].center(4)
                    if any(
                        [
                            node.contents is not None,
                            node.mined,
                            node.trapdoor is not TrapdoorState.NONE,
                        ]
                    )
                    else alg.center(4)
                )
                center += f"{inside}{'│' if (node.walls & Wall.EAST) or x==7 else ' '}"
                bottom += f"─{'──' if (node.walls & Wall.SOUTH) or y == 7 else '  '}─{'┘' if  y == 7 and x == 7 else ('┤' if x == 7 else ('┴' if  y == 7 else '┼'))}"
            string_arr.extend((center, bottom))
        return "\n".join(string_arr)

    def canonical(self) -> str:
        """Returns a string representation of the board in canonical form.

        This is the representation used when writing the game to a file.

        """
        row_strings = []
        for row in self.__nodes:
            row_string = "".join(node.canonical() for node in row)
            row_strings.append(row_string)
        return "\n".join(row_strings)

    @classmethod
    def from_str(cls, string: str | list[str], state: BoardState) -> Result:
        """Returns a board that is in the state described by the given string ,or list of strings.

        This string should not contain any comments, or a status line.
        It also should not contain any empty lines, newlines, or whitespace at the start or end of the string.

        Both

        `["rnbqkbnr",`

        `"pppppppp",`

        `"........",`

        `"........",`

        `"........",`

        `"........",`

        `"PPPPPPPP",`

        `"RNBQKBNR"]`

        and

        `"rnbqkbnr\\npppppppp\\n........\\n........\\n........\\n........\\nPPPPPPPP\\nRNBQKBNR"`

        are valid.
        """

        # Split the string by lines if it is a single string, or ensure that it is a list of strings passed
        raw_lines = []
        match string:
            case str():
                raw_lines = string.split("\n")
            case list():
                if all(isinstance(line, str) for line in string):
                    raw_lines = string

        # transform the board lines into a list of lists of characters, such that the wall modifiers are at the end
        lines = []
        for line in raw_lines:
            mod_list = []
            new_line = []
            for node_list in line:
                # while the character is a modifier, add it to the list
                if node_list.lower() in ["|", "_"]:
                    mod_list.append(node_list)
                    continue
                # add the character and the modifiers to the line, with the wall modifiers at the end
                new_line.append([node_list] + mod_list)
                # clear the list of modifiers
                mod_list = []
            # add the line to the list of lines
            lines.append(new_line)

        # create the board from the lines
        board = []
        for y, row in enumerate(lines):
            board.append([])
            # Create a node for each character in the line
            for x, node_list in enumerate(row):
                # Attempt to create the node from the character
                new_node_result: Result = BoardNode.from_str(node_list[0])
                if isinstance(new_node_result, Failure):
                    # Node creation failed, return Failure
                    return Failure(algebraic(x, y))
                # Node creation succeeded, unwrap result
                new_node: BoardNode = new_node_result.unwrap()

                # apply the wall modifiers to the node
                for modifier in node_list[1:]:
                    match modifier:
                        # west wall
                        case "|":
                            new_node.walls |= Wall.WEST
                        # east wall
                        case "_":
                            new_node.walls |= Wall.SOUTH
                        case _:
                            # if the modifier is not recognised, raise an error
                            return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                board[-1].append(new_node)

        return Success(cls(board, state))

    @classmethod
    def standard_board(cls) -> Result:
        """Returns a board that is in standard starting positions."""
        standard_board_str = "\n".join(
            [
                "rnbqkbnr",  # black pieces
                "pppppppp",
                "........",
                "........",
                "........",
                "........",
                "PPPPPPPP",
                "RNBQKBNR",  # white pieces
            ]
        )
        return cls.from_str(standard_board_str, BoardState.standard_state())

    def apply_move(self, move: Move) -> "Board":
        """Applies the given move to the board, returning a new board and leaving the original unchanged."""
        raise NotImplementedError

    def normalise_walls(self):
        # normalise the board walls
        for y, row in enumerate(self.__nodes):
            for x, node in enumerate(row):
                match node.walls:
                    case Wall.WEST:
                        # if this node has a west wall, the node to the west must have an east wall
                        self.__nodes[y][x - 1].walls |= Wall.EAST
                        # remove the NONE flag from this node and its neighbour
                        self.__nodes[y][x - 1].walls &= ~Wall.NONE
                        self.__nodes[y][x].walls &= ~Wall.NONE
                    case Wall.SOUTH:
                        # if this node has a south wall, the node to the south must have a north wall
                        self.__nodes[y - 1][x].walls |= Wall.NORTH
                        # remove the NONE flag from this node and its neighbour
                        self.__nodes[y - 1][x].walls &= ~Wall.NONE
                        self.__nodes[y][x].walls &= ~Wall.NONE
