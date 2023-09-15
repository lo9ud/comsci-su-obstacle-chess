"""Classes for representing the board state and the board itself."""

from typing import Dict, Iterator, List, Tuple, Union, overload
from piece import Piece, Pawn, Knight, Bishop, Rook, Queen, King
from common import *
from move import (
    Move,
    NullMove,
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


class BoardNode:
    """Logical representation of a node on the board.

    Maintains info on mines, trapdoors and pieces on the node.

    Provides a `canonical()` method for transforming this node into a string that describes it, in the format required by the spec.
    """

    def __init__(
        self, contents: Union[Piece, None], mined: bool, trapdoor: TrapdoorState
    ) -> None:
        self.contents = contents
        """The contents of a tile (`None` or `Piece`)"""
        self.mined = mined
        """Whether there is a mine on this tile"""
        self.trapdoor = trapdoor
        """Whether there is a trapdoor on this tile, and its state"""
        self.walls = Wall(0)
        """Which walls are present on this tile"""

    def __str__(self) -> str:
        return f"Node({self.contents=}, {self.mined=}, {self.trapdoor=}, {Wall.to_str(self.walls)})"

    def __repr__(self):
        return self.canonical()

    def canonical(self) -> str:
        """Return a string representation of the node in canonical form.

        Returns
        -------
        str
            The canonical representation of the node.
        """
        node_str = ""
        # If there is a piece on the node, add it to the string
        if self.contents is None:
            if self.mined:
                if self.trapdoor == TrapdoorState.HIDDEN:
                    node_str += "X"
                # no trapdoor and a mine
                elif self.trapdoor == TrapdoorState.NONE:
                    node_str += "M"
            # no mine and a hidden trapdoor
            elif self.trapdoor == TrapdoorState.HIDDEN:
                node_str += "D"
            # no mine and an open trapdoor
            elif self.trapdoor == TrapdoorState.OPEN:
                node_str += "O"
            # no mine and no trapdoor
            elif self.trapdoor == TrapdoorState.NONE:
                node_str += "."
        else:
            # if there is a piece, add it to the string
            node_str += self.contents.canonical()
        # prepend walls to the string
        if self.walls & Wall.SOUTH:
            node_str = f"_{node_str}"
        if self.walls & Wall.WEST:
            node_str = f"|{node_str}"

        # return the string
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
            return Success(BoardNode(None, False, TrapdoorState.NONE))

        # a mine or trapdoor
        elif char[0] in ["D", "O", "M", "X"]:
            if char == "D":
                return Success(BoardNode(None, False, TrapdoorState.HIDDEN))
            # open trapdoor
            elif char == "O":
                return Success(BoardNode(None, False, TrapdoorState.OPEN))
            # mine
            elif char == "M":
                return Success(BoardNode(None, True, TrapdoorState.NONE))
            # hidden trapdoor and a mine
            elif char == "X":
                return Success(BoardNode(None, True, TrapdoorState.HIDDEN))

        # a piece
        # This is evaluated last, so that isupper and islower can be used to check for pieces and dont get caught on mines/trapdoors

        new_piece = Piece.from_str(char[0])
        if isinstance(new_piece, Success):
            return Success(BoardNode(new_piece.unwrap(), False, TrapdoorState.NONE))

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
        player: Player,
        walls: tuple,
        castling: tuple,
        enpassant: Union[Position, None],
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
                # the current player
                Player.canonical(self.player),
                # the number of walls for each player
                str(self.walls[Player.WHITE]),
                str(self.walls[Player.BLACK]),
                # the castling rights for each player
                "+" if self.castling[Player.WHITE]["king"] else "-",
                "+" if self.castling[Player.WHITE]["queen"] else "-",
                "+" if self.castling[Player.BLACK]["king"] else "-",
                "+" if self.castling[Player.BLACK]["queen"] else "-",
                # the enpassant target
                self.enpassant.canonical() if self.enpassant else "-",
                # the halfmove clock
                str(self.clock),
            ]
        )

    def copy(self) -> "BoardState":
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

        The string should match the following format:
            `(w|b) ([0-3] ){2} ((\\+|-) ){4}(-|[a-g][1-8]) [1-9]\\d*`

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
        # check that the string is valid, and conforms to the required format
        # this guarantees that any later operations will not fail
        # matches as follows:
        #   - `(w|b)`: either w or b
        #   - `([0-3] ){2}`:  two of a number between 0 and 3 followed by a space
        #   - `((\+|-) ){4}`: four of either + or - followed by a space
        #   - `(-|[a-g][1-8])`: either a dash, or a letter between a and g followed by a number between 1 and 8
        #   - `([1-9]\d*|0)`: one or more digits, not starting with 0, or just 0
        if not re.match(
            r"(w|b) ([0-3] ){2}((\+|-) ){4}(-|[a-g][1-8]) ([1-9]\d*|0)", string
        ):
            return Failure(Error.ILLEGAL_STATUSLINE)

        # split the string into blocks
        blocks = string.split()

        # extract the player
        player = Player.from_str(blocks[0]).unwrap()

        # extract the number of walls
        walls = tuple(map(int, blocks[1:3]))

        # extract the castling rights
        castling = tuple(map(lambda x: x == "+", blocks[3:7]))

        # extract the enpassant target
        enpassant_str = blocks[7]
        enpassant = None if (enpassant_str == "-") else Position.from_str(enpassant_str)

        # extract the halfmove clock
        clock = int(blocks[8])

        return Success(cls(player, walls, castling, enpassant, clock))

    @classmethod
    def standard_state(cls):
        """Generates a standard starting state, as in standard chess"""
        return cls(Player.WHITE, (3, 3), (True, True, True, True), None, 0)


class Board:
    """A representation of the board state.

    Maintains the boards current state, and provides methods for manipulating it.
    """

    standard_board_str = [
        "rnbqkbnr",  # black pieces
        "pppppppp",
        "........",
        "........",
        "........",
        "........",
        "PPPPPPPP",
        "RNBQKBNR",  # white pieces
        BoardState.standard_state().canonical(),  # standard state
    ]

    ############
    #  Dunder  #
    ############
    
    def __init__(self, board: list, state: BoardState, initial_moves: int, turn: int) -> None:
        # The boards nodes, as a 2D array
        self._nodes: list = board
        """The tiles on the board"""
        self.state: BoardState = state
        """The state of the board"""
        self.initial_moves = initial_moves
        """The number of initial moves allowed (i.e. the number of trap placements remaining)"""
        self.turn = turn
        """Which turn this board is on"""
        # Ensure that the walls are normalised (i.e. that each wall corresponds to a wall on the opposite side of the adjacent node)
        self.normalise_walls()

    def __getitem__(self, pos: Position) -> BoardNode:
        """Returns the node at the given coordinates."""
        return self._nodes[pos.file][pos.rank]

    def __setitem__(self, pos: Position, value: BoardNode):
        """Sets the node at the given index to the given value."""
        self._nodes[pos.file][pos.rank] = value

    def __iter__(self) -> Iterator[list]:
        """Iterates over rows of the boards nodes."""
        yield from self._nodes
        return StopIteration()

    def __repr__(self) -> str:
        return f"Board(player:{self.state.player.name})"

    def __str__(self) -> str:
        return repr(self)

    def copy(self) -> "Board":
        """Returns a copy of the board."""
        return deepcopy(self)
    
    ############
    #   Info   #
    ############
    
    def canonical(self) -> str:
        """Returns a string representation of the board in canonical form.

        This is the representation used when writing the game to a file.

        """
        row_strings = []
        for row in self._nodes:
            row_string = "".join(node.canonical() for node in row)
            row_strings.append(row_string)
        return "\n".join(row_strings + [self.state.canonical()])

    @overload
    def in_check(self) -> Union[Player, None]: ...
    @overload
    def in_check(self, player: Player) -> bool: ...
    def in_check(self, player = None):
        """Determines if any player is in check

        Arguments
        ----------
        player : Player, optional
            The player to check for, if None, checks for any player, by default None
        
        Returns
        -------
        Player|None
            The player in check, if any, or None
        """
        for owner, king_pos in self.get_kings_pos().items():
            if k:=self.being_attacked_at(king_pos, owner.opponent()):
                return owner == player if player else owner
        return player if player is None else False
    
    
    @overload
    def checkmate(self) -> Union[Player, None]: ...
    @overload
    def checkmate(self, player:Player) -> bool: ...
    def checkmate(self, player:Union[Player, None] = None) -> Union[Player, None, bool]: #TODO
        """Determines if any player is in checkmate

        Returns
        -------
        Player|None
            The player in checkmate, if any
        """
        # get the king in check
        player = self.in_check()
        # if there is no king in check, return None
        if player is None:
            return None if player is None else False
        
        king_pos = self.get_kings_pos()[player]
        
        
        # pop the king out of the board so that it doesn't interfere with the check for check
        tmp = self[king_pos].contents
        self[king_pos].contents = None
        
        # check if the king can move out of check
        for neighbour in self.get_neighbours(king_pos):
            target = self[neighbour].contents
            # check that the king is not moving into check again
            if self.being_attacked_at(neighbour, player.opponent()):
                continue
            # check that the king is not moving into a piece of the same colour
            if target is None or target.owner == player:
                continue
            # if the king can move out of check, return None
            return None
        # put the king back
        self[king_pos].contents = tmp
        
        # king cannot move out of check, check if any pieces can block the check
        attacking_positions = self.being_attacked_at(king_pos, player.opponent())
        # check if a wall can block the check
        if self.state.walls[player] > 0 and len(attacking_positions) == 1:
            return None
        
        for attacker in attacking_positions:
            # get the line between the attacker and the king
            line = self.get_line(attacker, (king_pos - attacker).norm())
            # get the run of the line
            run = self.get_run(line)
            # get all the pieces belonging to the player on the board
            pieces = [pos for pos in run if (inner:=self[pos].contents) is not None and inner.owner == player]
            # check if any pieces can block the run
            # for each piece
            for piece in pieces:
                moves = self.get_moves(piece)
                # check if the piece can capture the attacker
                if attacker in moves:
                    return None
                # check if the piece can block the run
                for pos in run:
                    if pos in moves:
                        return None
        # player is in checkmate
        return player or True
        
    def stalemate(self) -> Union[Player, None]:
        """Returns whether the game is in stalemate

        Returns the player in stalemate, if any, or None

        Returns
        -------
        Union[Player, None]
            The player in stalemate, if any, or None
        """
        
        # check if the player has any valid moves
        # the list of playesr that need to be checked
        players = [Player.WHITE, Player.BLACK]
        for y,row in enumerate(self):
            for x,node in enumerate(row):
                # check that the node is not empty, and that the piece belongs to a player that has not already been checked
                if node.contents is None or node.contents.owner not in players:
                    continue
                # check if the piece has any valid moves
                if len(self.get_moves(P(x,y))) > 0:
                    # if so, remove the player from the list
                    players.remove(node.contents.owner)
                    if not players:
                        # if there are no players left, return None
                        return None

        # return the player in stalemate
        return players[0]

    @staticmethod
    def on_board(position: Position):
        """Determines whether the given position is on the board."""
        return 0 <= position.x < 8 and 0 <= position.y < 8

    def being_attacked_at(self, position: Position, attacking_player: Player) -> List[Position]:
        """Check whether a position is being attacked by a piece belonging to `attacking_player.

        Returns a list of the positions of the pieces attacking the position.
        
        Parameters
        ----------
        position: Position
            The position to check for attacks on.
        player : int
            The player to check for attacks from.

        Returns
        -------
        List[Position]
            The attacking positions.
        """
        def _get_attacker(run: List[Position], pieces:Tuple) -> List[Position]:
            for pos in run:
                opp = self[pos].contents
                if opp is None: # empty node, keep going
                    continue
                elif opp.owner == attacking_player and isinstance(opp, pieces): # enemy piece, stop as it blocks the run
                    return [pos]
                else: # friendly piece, stop as it blocks the run
                    break
            return []
        
        positions:List[Position] = []
        # immediate neighbours
        neighbours = self.get_neighbours(position)
        for neighbour in neighbours:
            target = self[neighbour].contents
            # check for kings
            if (
                isinstance(target, King)
                and target.owner == attacking_player
            ):
                positions.append(neighbour)
            # check for pawns
            if (
                isinstance(target, Pawn)
                and target.owner == attacking_player
            ):
                delta = neighbour - position
                # check that the pawn is attacking from the correct direction TODO: confirm logic here is correct
                if target.owner.value * delta.y == 1 and abs(delta.x) == 1:
                    positions.append(neighbour)

        straights:List[List[Position]] = []
        # vertical and horizontal lines
        straights.append(self.get_line(position, P(1, 0), allow_pieces = attacking_player))
        straights.append(self.get_line(position, P(-1, 0), allow_pieces = attacking_player))
        straights.append(self.get_line(position, P(0, 1), allow_pieces = attacking_player))
        straights.append(self.get_line(position, P(0, -1), allow_pieces = attacking_player))
        for straight in straights:
            positions.extend(_get_attacker(straight, (Queen, Rook)))

        diags = []
        # diagonal lines
        diags.append(self.get_line(position, P(1, 1), allow_pieces = attacking_player))
        diags.append(self.get_line(position, P(-1, -1), allow_pieces = attacking_player))
        diags.append(self.get_line(position, P(1, -1), allow_pieces = attacking_player))
        diags.append(self.get_line(position, P(-1, 1), allow_pieces = attacking_player))
        for diag in diags:
            positions.extend(_get_attacker(diag,(Queen, Bishop)))

        bends = []
        # knight moves
        for offset in Knight.offsets:
            pot_pos = position + offset
            if Board.on_board(pot_pos):
                bends.append(pot_pos)
        for bend in bends:
            target = self[bend].contents
            if (
                isinstance(target, Knight)
                and target.owner == attacking_player
            ):
                positions.append(bend)

        return positions

    def get_kings_pos(self) -> Dict[Player, Position]:
        kings:dict = {}
        for y,row in enumerate(self):
            for x,node in enumerate(row):
                inner = node.contents
                if isinstance(inner, King):
                    kings[inner.owner] = P(x,y)
        return kings
    
    def get_moves(self, position: Position) -> List[Position]:
        """Returns a list of all the moves a piece at the given position could make.

        Does not take context into account (i.e. whether the move would put the player in check etc.).

        Parameters
        ----------
        position : Position
            The position of the piece to check.

        Returns
        -------
        List[Position]
            The list of positions the piece could move to.
        """
        actor = self[position].contents
        if actor is None:
            return []
        player = actor.owner
        potentials = []
        def get_potentials(pos: Position, directions: List[Position]):
            positions = []
            runs = {}
            for direction in directions:
                runs[direction] = []
                line = self.get_line(pos, direction)
                if not line: # skip zero length lines
                    continue
                elif len(line) > 1: # if the line is longer than 1, get the run
                    runs[direction].extend(self.get_run(line))
                elif not self.wall_blocked(pos, direction): # if the line is 1 long, check if that position is blocked by a wall
                    runs[direction].extend(line)
                    
            
            for direction, run in runs.items():
                for pos in run:
                    opp = self[pos].contents
                    if opp is None:
                        positions.append(pos)
                    elif opp.owner != player:
                        positions.append(pos)
                        break
                    else:
                        break
            return positions
        ###########################################################
        #                        PAWNS                            #
        ###########################################################

        if isinstance(actor, Pawn):
            # single move forward
            front = position + P(0, player.value)
            if Board.on_board(front) and self[front].contents is None:
                potentials.append(front)
                # double move forward
                dfront = position + P(0, player.value * 2)
                if Board.on_board(dfront) and self[dfront].contents is None:
                    potentials.append(dfront)

            # diagonal moves
            for x_off in [P(x,0) for x in (-1, 1)]:
                target = front + x_off
                if Board.on_board(target):
                    opp = self[target].contents
                    if opp is not None and opp.owner != player:
                        potentials.append(target)

        ###########################################################
        #                       KNIGHTS                           #
        ###########################################################
        
        elif isinstance(actor, Knight):
            for offset in Knight.offsets:
                pot_pos = position + offset
                if Board.on_board(pot_pos):
                    opp = self[pot_pos].contents
                    if opp is None or opp.owner != player:
                        potentials.append(pot_pos)

        ###########################################################
        #                       BISHOPS                           #
        ###########################################################
        
        elif isinstance(actor, Bishop):
            directions = [P(x, y) for x in (-1, 1) for y in (-1, 1)]
            potentials = get_potentials(position, directions)
        
        ###########################################################
        #                        ROOKS                            #
        ###########################################################
        
        elif isinstance(actor, Rook):
            directions = [P(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if abs(x) != abs(y)]
            potentials = get_potentials(position, directions)
        
        ###########################################################
        #                        QUEENS                           #
        ###########################################################
        
        elif isinstance(actor, Queen):
            directions = [P(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if (x,y) != (0,0)]
            potentials = get_potentials(position, directions)
            
        ###########################################################
        #                         KINGS                           #
        ###########################################################
        
        elif isinstance(actor, King):
            for neighbour in self.get_neighbours(position):
                target = self[neighbour].contents
                if target is None or target.owner != player:
                    potentials.append(neighbour)

        # return the list of potentials
        return potentials
    
    def wall_blocked(self, position: Position, direction: Position) -> bool:
        """Determines whether a wall blocks movement in the given direction from the given position.

        Parameters
        ----------
        position : Position
            The position to check from.
        direction : Position
            The direction to check in.

        Returns
        -------
        bool
            Whether the movement is blocked.
        """
        from_pos = position
        from_node = self[from_pos]
        to_pos = position + direction
        if not Board.on_board(to_pos):
            # if the movement is off the board, it is blocked
            return True
        # check for walls
        if direction.y == 0 and ( # horizontal movement
            (direction.x > 0 and from_node.walls & Wall.EAST) or
            (direction.x < 0 and from_node.walls & Wall.WEST)
        ):
            return True
        elif direction.x == 0 and ( # vertical movement
            (direction.y > 0 and from_node.walls & Wall.SOUTH) or
            (direction.y <= 0 and from_node.walls & Wall.NORTH)
        ):
            return True

        else:  # diagonal movement
            # get the alternate positions
            # hori neighbour, vert neighbour
            hori_alt, vert_alt = Position(from_pos.x, to_pos.y), Position(to_pos.x, from_pos.y)
            #
            #   a\   b
            #     \
            #   c  \d
            #
            # get the motion in terms of walls
            #        (hori wall, vert wall)
            motion = (Wall(0), Wall(0))
            if direction.y > 0:  # South
                if direction.x > 0:  # East
                    motion = Wall.SOUTH, Wall.EAST
                else:  # West
                    motion = Wall.SOUTH, Wall.WEST
            else:  # North
                if direction.x > 0:  # East
                    motion = Wall.NORTH, Wall.EAST
                else:  # West
                    motion = Wall.NORTH, Wall.WEST
            inv_motion = tuple(map(Wall.alternate, motion))

            to_node = self[to_pos]
            # check for walls
            # check for from_node having both motion walls
            if (
                from_node.walls & motion[0]
                and from_node.walls & motion[1]
            ):
                return True
            # from_node has horizontal motion wall, and horizontal neighbour has that same wall
            elif (
                from_node.walls & motion[0]
                and self[hori_alt].walls & motion[0]
            ):
                return True
            # from_node has vertical motion wall, and vertical neighbour has that same wall
            elif (
                from_node.walls & motion[1]
                and self[vert_alt].walls & motion[1]
            ):
                return True
            # to_node has inverses of both motion walls
            elif (
                to_node.walls & inv_motion[0]
                and to_node.walls & inv_motion[1]
            ):
                return True
        return False
    
    ############
    #  Slicing #
    ############
    
    def get_line(self, origin: Position, direction: Position, allow_pieces:Union[Player, None] = None) -> List[Position]:
        """Returns a list of the coordinates of the nodes along the given direction starting from the origin.

        The origin is not included in the list.

        The list is truncated if it reaches the edge of the board, or if it encounters a wall/piece.

        Parameters
        ----------
        origin : tuple
            The origin of the line.
        direction : tuple
            The direction of the line.

        Returns
        -------
        list
            The coordinates of the nodes along the line.
        """
        # generate a list of the coordinates of the nodes along the line
        base = []
        i = 1
        while Board.on_board(pos:= origin + direction * i):
            i+=1
            base.append(pos)
        # get the run of the line
        return base

    def get_run(self, positions: List[Position]) -> List[Position]:
        """Determines how far a piece could move along the given list of positions in order (i.e. that there are no walls blocking the movement).
        
        Does not consider pieces blocking the movement.

        Parameters
        ----------
        positions : list
            The list of consecutive positions to check.

        Returns
        -------
        list[Positions]
            The run of accessible positions.
        """
        run = []
        # get each pair of positions
        delta = (positions[1] - positions[0]).norm()
        for pos in positions:
            if self.wall_blocked(pos, delta):
                # if the movement is blocked, return the run
                return run
            run.append(pos)
        # return the run
        return run

    def get_neighbours(self, position: Position) -> List[Position]:
        """Returns a list of all the neighbours of position that are on the board.

        Parameters
        ----------
        position: Position
            The position to work from

        Returns
        -------
        list
            The neighbours of that position
        """
        potential_neighbours = [Position(*x) for x in [
            (position.x + 1, position.y),
            (position.x - 1, position.y),
            (position.x,     position.y + 1),
            (position.x,     position.y - 1),
            (position.x + 1, position.y + 1),
            (position.x - 1, position.y - 1),
            (position.x + 1, position.y - 1),
            (position.x - 1, position.y + 1),
        ]]
        return [node for node in potential_neighbours if self.on_board(node)]

    ############
    #  Strings #
    ############
    
    @staticmethod
    def _board_list_transform(strs: list) -> list:
        """Transforms the board lines into a 3D array of characters,
        such that each coordinate holds a list containing the specifier for that node
        and then the modifiers for that node
        """
        lines: list = []
        for line in strs[:8]:
            mod_list: list = []
            new_line: list = []
            # append a dummy character to absorb any trailing modifiers
            for board_char in f"{line}#":
                # if the character is a modifier, add it to the modifier list
                if board_char in ["|", "_"]:
                    mod_list.append(board_char)
                    continue

                # add the character to the new line
                new_line.append([board_char] + mod_list)

                # clear the modifier list
                mod_list = []
            lines.append(new_line)
        return lines

    @staticmethod
    def _apply_node_modifiers(pos: Position, node: BoardNode, mods: list) -> Result:
        """Applies a list of modifiers to the supplied node"""
        for modifier in mods:
            # west wall
            if modifier == "|":
                node.walls |= Wall.WEST
                # check that the wall is not on the west edge of the board
                if pos.x == 0:
                    return Failure()
            # east wall
            elif modifier == "_":
                node.walls |= Wall.SOUTH
                # check that the wall is not on the south edge of the board
                if pos.y == 7:
                    return Failure()
            else:
                # if the modifier is not recognised, raise an error
                return Failure()
        return Success(None)

    @classmethod
    def from_strs(cls, strings: list, _init = False) -> Result["Board"]:
        """Returns a board that is in the state described by the given list of strings.

        This string should not contain any comments.
        It also should not contain any empty lines in the strings.
        """
        # check if the board is in standard starting positions
        if all(a == b for a, b in lzip(strings, cls.standard_board_str)) and not _init:
            # Return a standard board in the standard starting positions
            return cls.standard_board()

        # Transform the strings
        lines = cls._board_list_transform(strings)

        # create the board from the lines
        board = []
        for y, row_list in enumerate(lines):
            # append a new row to the board
            board.append([])
            # Create a node for each character in the line
            for x, board_chars in enumerate(row_list):
                # if its the dummy character

                if board_chars[0] == "#":
                    # we've reached the end of the line, but if its not the ninth position
                    if x != 8:
                        # return a Failure at the last correct node
                        return Failure(
                            Error.ILLEGAL_BOARD % Position(min(x, len(row_list)), y).canonical()
                        )
                    # else if there are modifiers on the dummy (i.e. there are trailing modifiers)
                    elif len(board_chars) > 1:
                        # return a failure on the right edge of the board
                        return Failure(Error.ILLEGAL_BOARD % Position(7, y).canonical())

                    # skip further processing, as we have reached the end of the line
                    continue
                # if its not the dummy char, check that the line is not too long
                elif x > 7:
                    return Failure(Error.ILLEGAL_BOARD % Position(7, y).canonical())

                # Attempt to create the node from the character
                new_node_result: Result = BoardNode.from_str(board_chars[0])
                if isinstance(new_node_result, Failure):
                    return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())
                # Node creation succeeded, unwrap result
                new_node: BoardNode = new_node_result.unwrap()

                # check for duplicate modifiers or too many modifiers
                if len(board_chars) > 3 or (
                    len(board_chars) == 3 and board_chars[1] == board_chars[2]
                ):
                    return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())

                # Attempt to apply the modifiers to the new node
                mod_result = cls._apply_node_modifiers(Position(x, y), new_node, board_chars[1:])
                if isinstance(mod_result, Failure):
                    return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())

                # append the node to the end of the row
                board[-1].append(new_node)

        state_result = BoardState.from_str(strings[8])
        if isinstance(state_result, Failure):
            return state_result
        state = state_result.unwrap()

        # check that there are no more lines
        if len(strings) > 9:
            return Failure(Error.ILLEGAL_STATUSLINE)

        return Success(cls(board, state, 4, 1))

    @classmethod
    def standard_board(cls) -> Result["Board"]:
        """Returns a board that is in standard starting positions."""
        return cls.from_strs(Board.standard_board_str, _init = True)

    def normalise_walls(self):
        """Adds the appropriate walls to each node, such that each wall corresponds to a wall on the opposite side of the adjacent node.

        Called automatically when the board is created, but will not fail if called multiple times.
        """
        # normalise the board walls
        for y, row in enumerate(self._nodes):
            for x, node in enumerate(row):
                if node.walls & Wall.WEST:
                    # if this node has a west wall, the node to the west must have an east wall
                    self._nodes[y][x - 1].walls |= Wall.EAST

                if node.walls & Wall.SOUTH:
                    # if this node has a south wall, the node to the south must have a north wall
                    self._nodes[y + 1][x].walls |= Wall.NORTH

                if node.walls & Wall.NORTH:
                    # if this node has a north wall, the node to the north must have a south wall
                    self._nodes[y - 1][x].walls |= Wall.SOUTH

                if node.walls & Wall.EAST:
                    # if this node has an east wall, the node to the east must have a west wall
                    self._nodes[y][x + 1].walls |= Wall.WEST
    
    ##############
    # Validation #
    ##############

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
        if not all(0 <= x <= 7 for x in tuple(move.origin) + tuple(move.destination)):
            return Failure(Error.ILLEGAL_MOVE % move.canonical())

        # Wall placement
        if isinstance(move, PlaceWall):
            # Due to the way the PlaceWall move is constructed, we can assume that the move is valid if both the origin and destination are on the board, which is checked above
            back, front = Wall.coords_to_walls(move.origin, move.destination)
            # check that the wall does not already exist
            if (self[move.origin].walls & back == back) or (
                self[move.destination].walls & front == front
            ):
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

        elif isinstance(move, PlaceMine):
            if self.initial_moves <= 0:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # check that the mine does not already exist
            if self[move.origin].mined:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # check that the mine is on the allowed rows
            if move.origin.y not in (3, 4):
                return Failure(Error.ILLEGAL_MOVE % move.canonical())
        elif isinstance(move, PlaceTrapdoor):
            # check that there are initail move remaining
            if self.initial_moves > 0:
                # check that the trapdoor does not already exist
                if self[move.origin].trapdoor is not TrapdoorState.NONE:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

                # check that the trapdoor is on the allowed rows
                if move.origin.y not in (2, 3, 4, 5):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())
            else:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

        elif isinstance(move, Castle):
            # check that the king is not moving into or across check or another piece
            pos = move.origin
            while pos != move.destination:
                # adjust the position
                pos = (pos + move.delta)
                target = self[pos]
                if target.contents is None and not self.being_attacked_at(
                    pos, move.player.opponent()
                ):
                    continue
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # check that the player has the right to castle
            if isinstance(move, KingCastle):
                if not self.state.castling[self.state.player]["king"]:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())
            elif isinstance(move, QueenCastle):
                if not self.state.castling[self.state.player]["queen"]:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())

        elif isinstance(move, Promotion):
            # check that the moving piece is a pawn
            if not isinstance(self[move.origin].contents, Pawn):
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # check that the pawn is moving to the correct row
            if not (
                (move.destination.y == 0 and move.player == Player.WHITE)
                or (move.destination.y == 7 and move.player == Player.BLACK)
            ):
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # check that the pawn is not promoting to a king or pawn
            if move.promotion is King or move.promotion is Pawn:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

        elif isinstance(move, NullMove):
            # Null moves are only valid if there are initial moves remaining
            if self.initial_moves > 0:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

        elif isinstance(move, Move):
            actor = self[move.origin].contents
            # check that the piece is moving to a valid position
            valid_moves = self.get_moves(move.origin)
            if move.destination not in valid_moves:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())




        return Success(move)

    ############
    #   Moves  #
    ############

    def detonate_mine(self, pos: Position):
        """Applies the effect of a mine detonation to the board.

        Parameters
        ----------
        pos: Position
            The position of the mine that is detonating
        """
        # clear this node
        self[pos].contents = None

        # TODO: remove the mine? (assume yes)
        # remove the mine
        self[pos].mined = False

        # clear the nodes around this node if the walls allow for that
        for neighbour in self.get_neighbours(pos):
            direction = (neighbour - pos).norm()
            if not self.wall_blocked(pos, direction):
                self[neighbour].contents = None
        
        # reset the halfmove clock
        self.state.clock = 0

    def apply_move(self, move: Move) -> Result["Board"]:
        """Applies the given (valid) move to the board, returning a new Result holding the board and leaving the original unchanged."""

        # initialise the new board
        new_board = self.copy()
        new_board.state.clock += 1

        # Apply the move
        piece, capture = False, False
        if isinstance(move, PlaceWall):
            back, front = Wall.coords_to_walls(move.origin, move.destination)
            new_board[move.origin].walls |= back
            new_board[move.destination].walls |= front

        elif isinstance(move, PlaceMine):
            new_board[move.origin].mined = True

        elif isinstance(move, PlaceTrapdoor):
            new_board[move.origin].trapdoor = TrapdoorState.HIDDEN

        elif isinstance(move, Castle):
            new_board._castle(move)

        elif isinstance(move, Promotion):
            capture = new_board._move_piece(move)
            new_board[move.destination].contents = move.promotion(move.player)

        elif isinstance(move, Move):
            capture = new_board._move_piece(move)

        # alternate the player
        new_board.state.player = new_board.state.player.opponent()
        
        # increment the move counter
        new_board.turn += 1

        return Success(new_board)

    def _castle(self, move: Castle):
        """Private method for castling.

        Performs the actual movement of the king and rook, without any validation.

        Parameters
        ----------
        move : Move
            The move to apply.
        new_board : Board
            The new board to apply the move to.
        """
        rook_move = move.rook_move()
        # pop out the king
        king_piece = self[move.origin].contents
        self[move.origin].contents = None
        # pop out the rook
        rook_piece = self[rook_move.origin].contents
        self[rook_move.origin].contents = None

        # place the king and rook in their new positions
        self[move.destination].contents = king_piece
        self[rook_move.destination].contents = rook_piece

    def _move_piece(self, move: Move):  # TODO: piece captures, check, checkmate, halfmoves
        """Private method for performing a standard move.

        Does not perform any validation.

        Performs the actual movement of the piece, and handles any special cases (e.g. mine detonation).

        Parameters
        ----------
        move : Move
            The move to apply.

        Returns
        -------
        Piece|None
            The piece captured, if any.
        """
        # extract origin and destination
        origin, dest = move.origin, move.destination

        capture = None
        if self[dest].contents is not None:  # capturing
            capture = self[dest].contents  # store the captured piece
            self.state.clock = 0  # reset halfmove clock
        piece = self[origin].contents
        if isinstance(piece, Pawn):  # pawn move
            self.state.clock = 0  # reset halfmove clock
            if abs(origin.y - dest.y) == 2:  # double move
                self.state.enpassant = Position(
                    origin.x,
                    (origin.y + dest.y) // 2,
                )  # set enpassant target
            elif self.state.enpassant and dest == self.state.enpassant: # perform enpassant capture
                capture_pos = Position(dest.x, origin.y) # the capture position has the same y as the origin and the same x as the destination
                capture = self[capture_pos].contents
                self[capture_pos].contents = None
        else:
            # reset enpassant target if another piece moves
            self.state.enpassant = None
            if isinstance(piece, King):
                self.state.castling[piece.owner] = {
                    "king": False,
                    "queen": False,
                }
            elif isinstance(piece, Rook):
                if origin.x == 0:
                    self.state.castling[piece.owner]["queen"] = False
                elif origin.x == 7:
                    self.state.castling[piece.owner]["king"] = False
        
        # move the piece
        self[dest].contents = self[origin].contents
        self[origin].contents = None

        dest_node = self[dest]
        # mine detonation
        if dest_node.mined:
            self.detonate_mine(dest)

        if dest_node.trapdoor is not TrapdoorState.NONE:
            if dest_node.trapdoor is TrapdoorState.HIDDEN:
                dest_node.trapdoor = TrapdoorState.OPEN
            dest_node.contents = None

        return capture
    
    