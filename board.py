from typing import Iterator, TextIO
from piece import Piece, Pawn, Knight, Bishop, Rook, Queen, King
from common import *
from output import *
from move import (
    Move,
    PlaceMine,
    PlaceTrapdoor,
    PlaceWall,
    Castle,
    KingCastle,
    Promotion,
    QueenCastle,
)
from copy import deepcopy
import re


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
    def get_wall_direction(
        _from: tuple[int, int], _to: tuple[int, int]
    ) -> tuple[int, int]:
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
                return (Wall.SOUTH, Wall.NORTH) if y2 > y1 else (Wall.NORTH, Wall.SOUTH)
            # North-South movement
            case (False, True):
                return (Wall.EAST, Wall.WEST) if x2 > x1 else (Wall.WEST, Wall.EAST)
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
                return (from_walls, to_walls)
            case _:
                return (Wall.NONE, Wall.NONE)

    @staticmethod
    def coords_to_walls(
        _from: tuple[int, int], _to: tuple[int, int]
    ) -> tuple[int, int]:
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
        match (x1 == x2, y1 == y2):
            # East-West movement
            case (True, False):
                return (Wall.SOUTH, Wall.NORTH) if y2 > y1 else (Wall.NORTH, Wall.SOUTH)
            # North-South movement
            case (False, True):
                return (Wall.EAST, Wall.WEST) if x2 > x1 else (Wall.WEST, Wall.EAST)
            case _:
                return (Wall.NONE, Wall.NONE)


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
        return f"Node({self.contents=}, {self.mined=}, {self.trapdoor=}, {Wall.to_str(self.walls)})"

    def __repr__(self):
        return f"Node({self.contents if self.contents is None else self.contents.canonical()})"

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
    def from_str(cls, char: str) -> Result["BoardNode"]:
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

        new_piece = Piece.from_str(char[0])
        if isinstance(new_piece, Success):
            return Success(BoardNode(new_piece.unwrap(), False, TrapdoorState.none()))

        # If the character could not be converted into a piece, return a Failure.
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

    def copy(self):
        """Creates a copy of the board state.

        Returns
        -------
        BoardState
            The copied board state.
        """
        return deepcopy(self)

    @classmethod
    def from_str(cls, string: str) -> Result["BoardState"]:
        """Creates a BoardState from a string.

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
        if not re.match(r"(w|b)\s\d\s\d\s((\+|-)\s){4}(-|\w\d)\s\d+", string):
            return Failure(Error.ILLEGAL_STATUSLINE)

        blocks = string.split()

        player_result = Player.from_str(blocks[0])
        # check player is valid
        if isinstance(player_result, Failure):
            return Failure(Error.ILLEGAL_STATUSLINE)
        else:
            player = player_result.unwrap()

        walls = tuple(map(int, blocks[1:3]))
        # check walls are in range
        if not (0 <= walls[0] <= 3 and 0 <= walls[1] <= 3):
            return Failure(Error.ILLEGAL_STATUSLINE)

        castling = tuple(map(lambda x: x == "+", blocks[3:7]))

        enpassant_str = blocks[7]
        enpassant = None if (enpassant_str == "-") else coords(enpassant_str)
        # check target square is on the board
        if enpassant is not None and 0 <= enpassant[0] <= 7 and 0 <= enpassant[1] <= 7:
            return Failure(Error.ILLEGAL_STATUSLINE)

        clock = int(blocks[8])
        # check clock is in range
        if not (0 <= clock <= 100):
            return Failure(Error.ILLEGAL_STATUSLINE)

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

    def __setitem__(self, index: tuple[int, int], value: BoardNode):
        self.__nodes[index[0]][index[1]] = value

    def __iter__(self) -> Iterator[list[BoardNode]]:
        """Iterates over rows of the boards nodes."""
        yield from self.__nodes
        return StopIteration()

    def __repr__(self) -> str:
        return f"Board({self.state=})"

    def __str__(self) -> str:
        return repr(self)

    def copy(self) -> "Board":
        """Returns a copy of the board."""
        return deepcopy(self)

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

    @staticmethod
    def on_board(position: tuple[int, int]):
        return 0 <= position[0] < 8 and 0 <= position[1] < 8

    def get_line(
        self, origin: tuple[int, int], direction: tuple[int, int]
    ) -> list[tuple[int, int]]:
        """Returns a list of the coordinates of the nodes along the given direction starting from the origin.

        The origin is included in the list.

        Parameters
        ----------
        origin : tuple[int,int]
            The origin of the line.
        direction : tuple[int, int]
            The direction of the line.

        Returns
        -------
        list[tuple[int,int]]
            The coordinates of the nodes along the line.
        """
        return [
            origin + direction * i
            for i in range(8)
            if Board.on_board(origin + direction * i)
        ]

    @classmethod
    def from_strs(cls, strings: list[str], state: BoardState) -> Result["Board"]:
        """Returns a board that is in the state described by the given string ,or list of strings.

        This string should not contain any comments, or a status line.
        It also should not contain any empty lines in the strings.

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

        # transform the board lines into a 3D array of characters, such that each coordinate holds a list containing the specifier for that node and then the modifiers for that node
        lines: list[list[list[str]]] = []
        for line in strings:
            mod_list: list[str] = []
            new_line: list[list[str]] = []
            # append a dummy character to absorb any trailing modifiers
            # TODO: what to do with spaces in board?
            for node_list in f"{line}#".replace(" ", ""):
                # if the character is a modifier, add it to the modifier list
                if node_list in ["|", "_"]:
                    mod_list.append(node_list)
                    continue

                # add the character to the new line
                new_line.append([node_list] + mod_list)

                # clear the modifier list
                mod_list = []
            lines.append(new_line)

        # create the board from the lines
        board = []
        for y, row_list in enumerate(lines):
            if y > 7:
                return Failure(Error.ILLEGAL_STATUSLINE)
            board.append([])
            # Create a node for each character in the line
            for x, node_list in enumerate(row_list):
                # if its the dummy character

                if node_list[0] == "#":
                    # if we've reached the end of the line, but its not the ninth position
                    if x != 8:
                        # return a Failure at the last correct node
                        return Failure(
                            Error.ILLEGAL_BOARD
                            % algebraic(min(x, len(row_list)) - 1, y)
                        )
                    # else if there are modifiers on the dummy
                    elif len(node_list) > 1:
                        # return a failure on the right edge of the board
                        return Failure(Error.ILLEGAL_BOARD % algebraic(7, y))

                    # skip further processing
                    continue
                # check that the line is not too long
                elif x > 7:
                    return Failure(Error.ILLEGAL_BOARD % algebraic(7, y))
                # Attempt to create the node from the character
                new_node_result: Result = BoardNode.from_str(node_list[0])
                if isinstance(new_node_result, Failure):
                    # Node creation failed, return Failure
                    return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                # Node creation succeeded, unwrap result
                new_node: BoardNode = new_node_result.unwrap()

                # check for duplicate modifiers
                if len(node_list) > 3 or (
                    len(node_list) == 3 and node_list[1] == node_list[2]
                ):
                    return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

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

            # check that the row is the right length (9 becuse of dummy character)
            if len(row_list) < 9:
                return Failure(Error.ILLEGAL_BOARD % algebraic(len(row_list), y))
        return Success(cls(board, state))

    @classmethod
    def standard_board(cls) -> Result["Board"]:
        """Returns a board that is in standard starting positions."""
        standard_board_str = [
            "rnbqkbnr",  # black pieces
            "pppppppp",
            "........",
            "........",
            "........",
            "........",
            "PPPPPPPP",
            "RNBQKBNR",  # white pieces
        ]
        return cls.from_strs(standard_board_str, BoardState.standard_state())

    def validate_move(self, move: Move) -> Result[Move]:
        """Validates the supplied move against this board, returning a Failure if the move is invalid, and a Success otherwise.

        Parameters
        ----------
        move : Move
            The move to validate.

        Returns
        -------
        Result
            The result of vaildation
        """
        # check that the move starts/end on the board
        if not all(0 <= x <= 7 for x in move.origin + move.destination):
            return Failure(Error.ILLEGAL_MOVE % move.canonical())

        match move:
            case Move():
                # get the current player
                active_player = self.state.player

                # get the active piece
                active_piece = self[move.origin].contents
                if active_piece is None:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # check that the active piece is owned by the current player, and the move is being made by the current player
                if active_piece.owner != active_player != move.player:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # extract the origin and destination
                x1, y1, x2, y2 = *move.origin, *move.destination

                # The absolute change in position for each of x and y
                delta = move.delta

                # The change in position for each of x and y
                sdelta = (x1 - x2, y1 - y2)

                # generate a list of all the nodes that the piece will pass through
                intermediate_nodes: list[tuple[int, int]] = []
                current = move.origin
                while current != move.destination:
                    intermediate_nodes.append(current)
                    current = (current[0] + sdelta[0], current[1] + sdelta[1])

                # check that the piece is not jumping over any pieces or walls
                if not active_piece.jumps and self.blocked(intermediate_nodes):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # check that the move is not a null move
                if delta == (0, 0):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # basic validation that the move fits the pieces move pattern
                if move not in active_piece.delta:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                match active_piece:
                    case Pawn():
                        # check that the pawn is not moving backwards
                        # if the move is north, and the piece is black, or the move is south and the piece is white
                        # use the fact that the player is either 1 or -1 to determine the direction of the move
                        if (y2 - y1) * active_player < 0:
                            return Failure(Error.ILLEGAL_MOVE % move.canonical())
                    case King():
                        # check that the king is not moving into check (i.e. that the king is not moving into a position that is attacked by the opponent)
                        if self.attacking(move.destination, -1 * active_player):
                            return Failure(Error.ILLEGAL_MOVE % move.canonical())

                    case _:
                        pass  # TODO: are there any other pieces that need special validation?
                # return a success
                return Success(move)

            case PlaceWall():
                # Due to the way the PlaceWall move is constructed, we can assume that the move is valid if both the origin and destination are on the board, which is checked above
                back, front = Wall.coords_to_walls(move.origin, move.destination)
                # check that the wall does not already exist
                if (self[move.origin].walls & back == back) or (
                    self[move.destination].walls & front == front
                ):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

            case PlaceMine():
                # check that the mine does not already exist
                if self[move.origin].mined:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # check that the mine is on the allowed rows
                if move.origin[1] not in (3, 4):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

            case PlaceTrapdoor():
                # check that the trapdoor does not already exist
                if self[move.origin].trapdoor is not TrapdoorState.NONE:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # check that the trapdoor is on the allowed rows
                if move.origin[1] not in (2, 3, 4, 5):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

            case Castle():
                # check that the king is not moving into check (i.e. that the king is not moving into a position that is attacked by the opponent)
                if self.attacking(move.destination, -1 * self.state.player):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # check that the player has the right to castle
                match move:
                    case KingCastle():
                        if not self.state.castling[self.state.player]["king"]:
                            return Failure(Error.ILLEGAL_MOVE % move.canonical())
                    case QueenCastle():
                        if not self.state.castling[self.state.player]["queen"]:
                            return Failure(Error.ILLEGAL_MOVE % move.canonical())

            case Promotion():
                # check that the moving piece is a pawn
                if not isinstance(self[move.origin].contents, Pawn):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # check that the pawn is moving to the correct row
                if not (
                    (move.destination[1] == 0 and move.player == Player.WHITE)
                    or (move.destination[1] == 7 and move.player == Player.BLACK)
                ):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # check that the pawn is not promoting to a king or pawn
                if move.promotion is King or move.promotion is Pawn:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

    def detonate_mine(self, pos: tuple[int, int]):
        """Applies the effect of a mine detonation to the board.

        Parameters
        ----------
        pos : tuple[int,int]
            THe position of the mine that is detonating
        """
        # clear this node
        self[pos].contents = None

        # TODO: remove the mine? (assume yes)
        # remove th mine
        self[pos].mined = False

        # clear the nodes around this node if the walls allow for that
        for neighbour in self.neighbours(pos):
            from_walls, to_walls = Wall.coords_to_walls(pos, neighbour)
            if self[pos].walls & from_walls or self[neighbour].walls & to_walls:
                self[neighbour].contents = None

    def apply_move(self, move: Move) -> Result["Board"]:
        """Applies the given move to the board, returning a new Result holding the board and leaving the original unchanged."""

        # initialise the new board
        new_board = self.copy()

        # Validate the move against this board
        if isinstance(k := self.validate_move(move), Failure):
            # If validation fails, return the failure
            return k

        # Apply the move
        match move:  # TODO: complete move application
            case Move():  # TODO: piece captures, check, checkmate
                # extract origin and destination
                origin, dest = move.origin, move.destination

                # swap contents of positions
                new_board[origin].contents, new_board[dest].contents = (
                    self[dest].contents,
                    self[origin].contents,
                )

                dest_node = new_board[dest]
                # mine detonation
                if dest_node.mined:
                    self.detonate_mine(dest)

                if dest_node.trapdoor is not TrapdoorState.NONE:
                    if dest_node.trapdoor is TrapdoorState.HIDDEN:
                        dest_node.trapdoor = TrapdoorState.OPEN
                    dest_node.contents = None
                # Return a Success
                return Success(move)

            case PlaceWall():
                back, front = Wall.coords_to_walls(move.origin, move.destination)
                new_board[move.origin].walls |= back
                new_board[move.destination].walls |= front
                return Success(move)

            case PlaceMine():
                new_board[move.origin].mined = True

            case PlaceTrapdoor():
                new_board[move.origin].trapdoor = TrapdoorState.HIDDEN

            case Castle():
                rook_move = move.rook_move()
                # pop out the king
                king_piece = new_board[move.origin].contents
                new_board[move.origin].contents = None
                # pop out the rook
                rook_piece = new_board[rook_move.origin].contents
                new_board[rook_move.origin].contents = None

                # place the king and rook in their new positions
                new_board[move.destination].contents = king_piece
                new_board[rook_move.destination].contents = rook_piece

            case Promotion():
                new_board[move.origin].contents = move.promotion(move.player)

    def apply_moves(self, moves: list[Move]) -> Result["Board"]:
        """Applies a list of moves to the board"""
        # The most recent result of a move
        last = Success(self)

        # For each move
        for move in moves:
            last.and_then(
                # Apply that move to the board
                self.apply_move,
                move=move,
            )
            # If the move failed, return the Failure early
            if isinstance(last, Failure):
                return last
        # Return the new success
        return last

    def neighbours(self, position: tuple[int, int]) -> list[tuple[int, int]]:
        potential_neighbours = [
            (position[0] + 1, position[1]),
            (position[0] - 1, position[1]),
            (position[0], position[1] + 1),
            (position[0], position[1] - 1),
            (position[0] + 1, position[1] + 1),
            (position[0] - 1, position[1] - 1),
            (position[0] + 1, position[1] - 1),
            (position[0] - 1, position[1] + 1),
        ]
        return [
            node
            for node in potential_neighbours
            if 0 <= node[0] <= 7 and 0 <= node[1] <= 7
        ]

    def blocked(self, positions: list[tuple[int, int]]) -> bool:
        """Determines whether the given positions are blocked by walls.

        Parameters
        ----------
        positions : list[tuple[int, int]]
            The positions to check.

        Returns
        -------
        bool
            Whether the positions are blocked.
        """
        # get the walls that would block movement for each pair of the intermediate nodes
        for walls, from_node, to_node in zip(
            map(Wall.get_wall_direction, positions, positions[1:]),
            positions,
            positions[1:],
        ):
            # if there are no walls, skip
            if walls is None:
                continue
            # check that the piece is not jumping over a wall
            if self[from_node].walls & walls[0] or self[to_node].walls & walls[1]:
                return False
        return True

    def attacking(
        self, position: tuple[int, int], attacking_player: int
    ) -> list[BoardNode]:
        """Returns a list of nodes with pieces that are attacking the given position.

        Parameters
        ----------
        position : tuple[int, int]
            The position to check for attacks on.
        player : int
            The player to check for attacks from.

        Returns
        -------
        list[BoardNode]
            The list of attacking nodes.
        """
        # TODO: finish this (better to do nodes or positions?)

        attacking: list[BoardNode] = []
        # check pawns
        neighbours = self.neighbours(position)
        for neighbour in neighbours:
            pass  # TODO: check for pawns

        # check for knights
        element_add = lambda x, y: (x[0] + y[0], x[1] + y[1])
        knight_positions = list(
            map(
                element_add,
                position,
                [
                    (1, 2),
                    (2, 1),
                    (-1, 2),
                    (-2, 1),
                    (1, -2),
                    (2, -1),
                    (-1, -2),
                    (-2, -1),
                ],
            )
        )
        for knight_position in knight_positions:
            node = self[knight_position]
            if (
                isinstance(node.contents, Knight)
                and node.contents.owner == attacking_player
            ):
                attacking.append(node)

        # check for queen, bishop and rook

        cardinal_lines: list[tuple[int, int]] = []
        # vertical down
        cardinal_lines.extend(self.get_line(position, (1, 0)))
        # vertical up
        cardinal_lines.extend(self.get_line(position, (-1, 0)))
        # horizontal right
        cardinal_lines.extend(self.get_line(position, (0, 1)))
        # horizontal left
        cardinal_lines.extend(self.get_line(position, (0, -1)))

        # check cardinal lines for rooks and queens
        for pos in cardinal_lines:
            node = self[pos]
            if (
                isinstance(node.contents, (Rook, Queen))
                and node.contents.owner == attacking_player
            ):
                attacking.append(node)

        diagonal_lines: list[tuple[int, int]] = []
        # diagonal down right
        diagonal_lines.extend(self.get_line(position, (1, 1)))
        # diagonal down left
        diagonal_lines.extend(self.get_line(position, (1, -1)))
        # diagonal up right
        diagonal_lines.extend(self.get_line(position, (-1, 1)))
        # diagonal up left
        diagonal_lines.extend(self.get_line(position, (-1, -1)))

        # check diagonal lines for bishops and queens
        for pos in diagonal_lines:
            node = self[pos]
            if (
                isinstance(node.contents, (Bishop, Queen))
                and node.contents.owner == attacking_player
            ):
                attacking.append(node)

        return attacking

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
