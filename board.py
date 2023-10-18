"""Classes for representing the board state and the board itself."""

import re
from copy import deepcopy
from typing import Dict, List, Tuple, Union, overload


from common import *
from move import (
    Castle,
    KingCastle,
    Move,
    NullMove,
    PlaceMine,
    PlaceTrapdoor,
    PlaceWall,
    Promotion,
    QueenCastle,
    SemiPromotion,
)
from piece import Bishop, King, Knight, Pawn, Piece, Queen, Rook


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
        return f"Node({self.contents}, {self.mined}, {self.trapdoor}, {Wall.to_str(self.walls)})"

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
        return f"BoardState({self.player}, ...)"

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

    empty_board_str = [
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        BoardState.standard_state().canonical(),  # standard state
    ]

    ############
    #  Dunder  #
    ############

    def __init__(
        self,
        board: list,
        state: BoardState,
        initial_moves: Dict[Player, Dict[str, int]],
        turn: int,
    ) -> None:
        # The boards nodes, as a 2D array
        self.nodes: List[List[BoardNode]] = board
        """The tiles on the board"""
        self.state: BoardState = state
        """The state of the board"""
        self.turn = turn
        """Which turn this board is on"""
        # determine the number of obstacles (either 0 or 1)
        self.initial_moves = initial_moves
        """The number of initial moves allowed (i.e. the number of trap placements remaining)"""
        self.mine_detonated = False
        """Whether this board was the result of a mine detonation"""
        
        # Ensure that the walls are normalised (i.e. that each wall corresponds to a wall on the opposite side of the adjacent node)
        self.normalise_walls()

    def __getitem__(self, pos: Position) -> BoardNode:
        """Returns the node at the given coordinates."""
        return self.nodes[pos.file][pos.rank]

    def __setitem__(self, pos: Position, value: BoardNode):
        """Sets the node at the given index to the given value."""
        print(f"Setting {pos.canonical()} to {value}")
        self.nodes[pos.file][pos.rank] = value

    def __iter__(self) -> List[List[BoardNode]]:
        """Iterates over rows of the boards nodes."""
        yield from self.nodes
        return StopIteration()

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        return f"Board(player:{self.state.player.name})"

    def __str__(self) -> str:
        return repr(self)
    
    def __eq__(self, __o:"Board") -> bool:
        # only compares the actual board, not the status line
        return self.canonical().split("\n")[:-1] == __o.canonical().split("\n")[:-1]

    def copy(self) -> "Board":
        """Returns a copy of the board."""
        return Board(
            deepcopy(self.nodes), self.state.copy(), self.initial_moves, self.turn
        )

    ############
    #   Info   #
    ############

    def canonical(self) -> str:
        """Returns a string representation of the board in canonical form.

        This is the representation used when writing the game to a file.

        """
        row_strings = []
        for row in self.nodes:
            row_string = "".join(node.canonical() for node in row)
            row_strings.append(row_string)
        return "\n".join(row_strings + [self.state.canonical()])

    @overload
    def in_check(self) -> Union[Player, None]:
        ...

    @overload
    def in_check(self, player: Player) -> bool:
        ...

    def in_check(self, player=None):
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
        in_check = []
        for owner, king_pos in self.get_kings_pos().items():
            if self.being_attacked_at(king_pos, owner.opponent()):
                in_check.append(owner)
                continue
        if player is None:
            return in_check[0] if len(in_check) > 0 else None
        else:
            return player in in_check

    @overload
    def checkmate(self) -> Union[Player, None]:
        ...

    @overload
    def checkmate(self, player: Player) -> bool:
        ...

    def checkmate(
        self, player: Union[Player, None] = None
    ) -> Union[Player, None, bool]:
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
        popped_king = self[king_pos].contents
        self[king_pos].contents = None

        # check if the king can move out of check
        for neighbour in self.get_neighbours(king_pos):
            target = self[neighbour].contents
            # check that the king is not moving into check again
            if self.being_attacked_at(neighbour, player.opponent()):
                continue
            # check that the king is not moving into a piece of the same colour
            if target is not None and target.owner == player:
                continue
            # if the king can move out of check, return None
            # put the king back
            self[king_pos].contents = popped_king
            return None
        # put the king back
        self[king_pos].contents = popped_king

        # king cannot move out of check, check if any pieces can block the check
        attacking_positions = self.being_attacked_at(king_pos, player.opponent())
        # check if a wall can block the check
        if self.state.walls[player] > 0 and len(attacking_positions) == 1:
            delta = (attacking_positions[0] - king_pos).norm()
            # cardinal motion can always be blocked by a wall
            if delta.x == 0 or delta.y == 0:
                return None
            # diagonal can only be blocked if a wall already exists somewhere between the attacker and the king
            elif any(self[tile].walls for tile in self.get_between(king_pos, attacking_positions[0])):
                return None

        for attacker in attacking_positions:
            # get the line between the attacker and the king
            line = self.get_line(attacker, (king_pos - attacker).norm())
            # get the run of the line
            run = self.get_run(line)
            # get all the pieces belonging to the player on the board
            pieces = [
                pos
                for pos in run
                if self[pos].contents is not None and self[pos].contents.owner == player
            ]
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
        for y, row in enumerate(self):
            for x, node in enumerate(row):
                # check that the node is not empty, and that the piece belongs to a player that has not already been checked
                if node.contents is None or node.contents.owner not in players:
                    continue
                # check if the piece has any valid moves
                if len(self.get_moves(P(x, y))) > 0:
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

    def being_attacked_at(
        self, position: Position, attacking_player: Player
    ) -> List[Position]:
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

        def _get_attacker(run: List[Position], pieces: Tuple) -> List[Position]:
            for pos in run[
                1:
            ]:  # slicing to avoid the first position, which is the position being checked
                opp = self[pos].contents
                if opp is None:  # empty node, keep going
                    continue
                elif opp.owner == attacking_player and isinstance(
                    opp, pieces
                ):  # enemy piece, stop as it blocks the run
                    return [pos]
                else:  # friendly piece, stop as it blocks the run
                    break
            return []


        positions: List[Position] = []
        # immediate neighbours
        neighbours = self.get_neighbours(position)
        for neighbour in neighbours:
            target = self[neighbour].contents
            # check for kings
            if isinstance(target, King) and target.owner == attacking_player:
                positions.append(neighbour)
            # check for pawns
            if isinstance(target, Pawn) and target.owner == attacking_player:
                delta = neighbour - position
                # check that the pawn is attacking from the correct direction TODO: confirm logic here is correct
                if target.owner.value * delta.y == -1 and abs(delta.x) == 1:
                    positions.append(neighbour)

        straights: List[List[Position]] = []
        # vertical and horizontal lines
        straights.append(
            self.get_run(
                self.get_line(position, P(1, 0), allow_pieces=attacking_player)
            )
        )
        straights.append(
            self.get_run(
                self.get_line(position, P(-1, 0), allow_pieces=attacking_player)
            )
        )
        straights.append(
            self.get_run(
                self.get_line(position, P(0, 1), allow_pieces=attacking_player)
            )
        )
        straights.append(
            self.get_run(
                self.get_line(position, P(0, -1), allow_pieces=attacking_player)
            )
        )
        for straight in straights:
            positions.extend(_get_attacker(straight, (Queen, Rook)))

        diags = []
        # diagonal lines
        diags.append(
            self.get_run(
                self.get_line(position, P(1, 1), allow_pieces=attacking_player)
            )
        )
        diags.append(
            self.get_run(
                self.get_line(position, P(-1, -1), allow_pieces=attacking_player)
            )
        )
        diags.append(
            self.get_run(
                self.get_line(position, P(1, -1), allow_pieces=attacking_player)
            )
        )
        diags.append(
            self.get_run(
                self.get_line(position, P(-1, 1), allow_pieces=attacking_player)
            )
        )
        for diag in diags:
            positions.extend(_get_attacker(diag, (Queen, Bishop)))

        bends = []
        # knight moves
        for offset in Knight.offsets:
            pot_pos = position + offset
            if Board.on_board(pot_pos):
                bends.append(pot_pos)
        for bend in bends:
            target = self[bend].contents
            if isinstance(target, Knight) and target.owner == attacking_player:
                positions.append(bend)

        return positions

    def get_kings_pos(self) -> Dict[Player, Position]:
        kings: dict = {}
        for y, row in enumerate(self):
            for x, node in enumerate(row):
                inner = node.contents
                if isinstance(inner, King):
                    kings[inner.owner] = P(x, y)
        return kings

    def get_moves(self, position: Position, strict=False) -> List[Position]:
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
        # if the piece is not owned by the current player, return an empty list
        if strict and player != self.state.player:
            return []

        potentials: List[Move] = []

        def get_potentials(pos: Position, directions: List[Move]):
            positions = []
            runs = {}
            for direction in directions:
                runs[direction] = self.get_line(pos, direction)
                # runs[direction] = []
                # line = self.get_line(pos, direction)
                # if not line: # skip zero length lines
                #     continue
                # elif len(line) > 1: # if the line is longer than 1, get the run
                #     runs[direction].extend(self.get_run(line))
                # elif not self.wall_blocked(pos, direction): # if the line is 1 long, check if that position is blocked by a wall
                #     runs[direction].extend(line)

            for direction, run in runs.items():
                for i, (posA, posB) in enumerate(zip(run, run[1:])):
                    target = self[posB].contents
                    if not self.wall_blocked(posA, posB - posA):
                        if target and target.owner == player:
                            break
                        elif target:
                            positions.append(posB)
                            break
                        else:
                            positions.append(posB)
                    else:
                        break
                # for pos in run:
                #     opp = self[pos].contents
                #     if opp is None:
                #         positions.append(pos)
                #     elif opp.owner != player:
                #         positions.append(pos)
                #         break
                #     else:
                #         break
            return positions

        ###########################################################
        #                        PAWNS                            #
        ###########################################################

        if isinstance(actor, Pawn):
            # determine whether this pawn will promote if it moves forwards
            movetype = (
                SemiPromotion if position.y == int(3.6 + 2.5 * player.value) else Move
            )
            # single move forward
            front = position + P(0, player.value)
            if (
                Board.on_board(front)
                and self[front].contents is None
                and not self.wall_blocked(position, front - position)
            ):
                potentials.append(movetype(player, position, front))
                # double move forward
                dfront = position + P(0, player.value * 2)
                if (
                    Board.on_board(dfront)
                    and self[dfront].contents is None
                    and position.y == int(3.6 - 2.5 * player.value)
                    and not self.wall_blocked(front, dfront - front)
                ):
                    potentials.append(Move(player, position, dfront))

            # diagonal moves
            for x_off in [P(x, 0) for x in (-1, 1)]:
                target = front + x_off
                if Board.on_board(target) and not self.wall_blocked(
                    position, target - position
                ):
                    opp = self[target].contents
                    if opp is not None and opp.owner != player:
                        potentials.append(movetype(player, position, target))

            # en passant
            if self.state.enpassant is not None and self.state.enpassant.y == front.y:
                for x_off in [P(x, 0) for x in (-1, 1)]:
                    target = front + x_off
                    if (
                        Board.on_board(target)
                        and target == self.state.enpassant
                        and (
                            self[target].contents is None
                            or self[target].contents.owner != player
                        )
                    ):
                        potentials.append(Move(player, position, target))

        ###########################################################
        #                       KNIGHTS                           #
        ###########################################################

        elif isinstance(actor, Knight):
            for offset in Knight.offsets:
                pot_pos = position + offset
                if Board.on_board(pot_pos):
                    opp = self[pot_pos].contents
                    if opp is None or opp.owner != player:
                        potentials.append(Move(player, position, pot_pos))

        ###########################################################
        #                       BISHOPS                           #
        ###########################################################

        elif isinstance(actor, Bishop):
            directions = [P(x, y) for x in (-1, 1) for y in (-1, 1)]
            potential_targets = get_potentials(position, directions)
            potentials.extend(
                Move(player, position, target) for target in potential_targets
            )

        ###########################################################
        #                        ROOKS                            #
        ###########################################################

        elif isinstance(actor, Rook):
            directions = [
                P(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if abs(x) != abs(y)
            ]
            potential_targets = get_potentials(position, directions)
            potentials.extend(
                Move(player, position, target) for target in potential_targets
            )

        ###########################################################
        #                        QUEENS                           #
        ###########################################################

        elif isinstance(actor, Queen):
            directions = [
                P(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if (x, y) != (0, 0)
            ]
            potential_targets = get_potentials(position, directions)
            potentials.extend(
                Move(player, position, target) for target in potential_targets
            )

        ###########################################################
        #                         KINGS                           #
        ###########################################################

        elif isinstance(actor, King):
            for neighbour in self.get_neighbours(position):
                target = self[neighbour].contents
                if (target is None or target.owner != player) and not self.wall_blocked(
                    position, neighbour - position
                ):
                    potentials.append(Move(player, position, neighbour))
            # remove moves that would put the king in check
            # pop the king out of the board so that it doesn't interfere with the check for check
            tmp = self[position].contents
            self[position].contents = None
            for i, move in enumerate(potentials):
                # check if the king would be in check after the move
                if self.being_attacked_at(move.destination, player.opponent()):
                    potentials.pop(i)
                    break
            # put the king back
            self[position].contents = tmp

            # castling
            # very long logic checks the following (in this order):
            #   -: The player has the castling right
            #   -: There are no walls blocking the castling
            #   -: None of the positions between the king and the rook are being attacked
            #   -: There are no pieces between the king and the rook
            if self.state.castling[player]["king"] and all(
                self[pos].contents is None
                for pos in [position + P(1, 0), position + P(2, 0)]
                if self.on_board(pos)
                and not self.wall_blocked(position, pos - position)
                and not self.being_attacked_at(pos, player.opponent())
            ):
                potentials.append(KingCastle(player))
            if self.state.castling[player]["queen"] and all(
                self[pos].contents is None
                for pos in [
                    position + P(-1, 0),
                    position + P(-2, 0),
                    position + P(-3, 0),
                ]
                if self.on_board(pos)
                and not self.wall_blocked(position, pos - position)
                and not self.being_attacked_at(pos, player.opponent())
            ):
                potentials.append(QueenCastle(player))

        # simulate each potential move to see if it is legal
        danger = self.in_check(player)
        for potential in potentials[:]:
            move_res = self.apply_move(potential)
            if isinstance(move_res, Failure):
                potentials.remove(potential)
            else:
                dummy = move_res.unwrap()
                if dummy.in_check(player):
                    potentials.remove(potential)

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
        if direction.y == 0:
            if (  # horizontal movement
                direction.x > 0 and from_node.walls & Wall.EAST
            ) or (direction.x < 0 and from_node.walls & Wall.WEST):
                return True
        elif direction.x == 0:
            if (  # vertical movement
                direction.y > 0 and from_node.walls & Wall.NORTH
            ) or (direction.y < 0 and from_node.walls & Wall.SOUTH):
                return True

        else:  # diagonal movement
            # get the alternate positions
            # hori neighbour, vert neighbour
            hori_alt, vert_alt = Position(to_pos.x, from_pos.y), Position(
                from_pos.x, to_pos.y
            )
            #
            #   a\   b
            #     \
            #   c  \d
            #
            # get the motion in terms of walls
            #        (hori wall, vert wall)
            motion = (Wall(0), Wall(0))
            if direction.y < 0:  # South
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
            if from_node.walls & motion[0] and from_node.walls & motion[1]:
                return True
            # from_node has horizontal motion wall, and horizontal neighbour has that same wall
            elif from_node.walls & motion[0] and self[hori_alt].walls & motion[0]:
                return True
            # from_node has vertical motion wall, and vertical neighbour has that same wall
            elif from_node.walls & motion[1] and self[vert_alt].walls & motion[1]:
                return True
            # to_node has inverses of both motion walls
            elif to_node.walls & inv_motion[0] and to_node.walls & inv_motion[1]:
                return True
        return False

    ############
    #  Slicing #
    ############

    def get_between(self, start: Position, end: Position) -> List[Position]:
        """Returns a list of the positions between the two given positions.

        The start and end positions are not included in the list.

        Parameters
        ----------
        start : Position
            The start of the range.
        end : Position
            The end of the range.

        Returns
        -------
        List[Position]
            The positions between the two given positions.
        """
        # get the direction of the movement
        direction = (end-start).norm()
        # get the line between the two positions
        line = self.get_line(start, direction)
        if line:
            # remove positions past the end
            while line[-1] != end:
                line.pop()
            # remove the end position
            line.pop()
            # return the run of the line
            return line
        return []

    def get_line(
        self,
        origin: Position,
        direction: Position,
        allow_pieces: Union[Player, None] = None,
    ) -> List[Position]:
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
        line_pos = origin
        while Board.on_board(line_pos):
            base.append(line_pos)
            i += 1
            line_pos += direction
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
        if len(positions) < 2:
            return positions
        run = []
        # get each pair of positions
        delta = (positions[1] - positions[0]).norm()
        for pos in positions:
            run.append(pos)
            if self.wall_blocked(pos, delta):
                # if the movement is blocked, return the run
                return run
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
        potential_neighbours = [
            Position(*x)
            for x in [
                (position.x + 1, position.y),
                (position.x - 1, position.y),
                (position.x, position.y + 1),
                (position.x, position.y - 1),
                (position.x + 1, position.y + 1),
                (position.x - 1, position.y - 1),
                (position.x + 1, position.y - 1),
                (position.x - 1, position.y + 1),
            ]
        ]
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
            # south wall
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
    def from_strs(cls, strings: list, _init=False) -> Result["Board"]:
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
                            Error.ILLEGAL_BOARD
                            % Position(min(x, len(row_list)), y).canonical()
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
                mod_result = cls._apply_node_modifiers(
                    Position(x, y), new_node, board_chars[1:]
                )
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

        initial_moves = {
            "total": 4,
            Player.WHITE: {"mines": _init, "trapdoors": _init},
            Player.BLACK: {"mines": _init, "trapdoors": _init},
        }
        return Success(cls(board, state, initial_moves, 1))

    @classmethod
    def standard_board(cls) -> Result["Board"]:
        """Returns a board that is in standard starting positions."""
        return cls.from_strs(Board.standard_board_str, _init=True)

    @classmethod
    def empty_board(cls) -> Result["Board"]:
        """Returns an empty board."""
        return cls.from_strs(Board.empty_board_str, _init=True)

    ##############
    # Validation #
    ##############
    def normalise_walls(self):
        """Adds the appropriate walls to each node, such that each wall corresponds to a wall on the opposite side of the adjacent node.

        Called automatically when the board is created, but will not fail if called multiple times.
        """
        # normalise the board walls
        for y, row in enumerate(self.nodes):
            for x, node in enumerate(row):
                if node.walls & Wall.WEST:
                    # if this node has a west wall, the node to the west must have an east wall
                    self.nodes[y][x - 1].walls |= Wall.EAST

                if node.walls & Wall.SOUTH:
                    # if this node has a south wall, the node to the south must have a north wall
                    self.nodes[y - 1][x].walls |= Wall.NORTH

                if node.walls & Wall.NORTH:
                    # if this node has a north wall, the node to the north must have a south wall
                    self.nodes[y + 1][x].walls |= Wall.SOUTH

                if node.walls & Wall.EAST:
                    # if this node has an east wall, the node to the east must have a west wall
                    self.nodes[y][x + 1].walls |= Wall.WEST

    def standardise_status(self):
        """Standardises the status of the board, such that castling rights are correct, and the current player is white."""
        # make the current player white
        self.state.player = Player.WHITE

        # set the castling rights
        self.state.castling = {
            Player.WHITE: {
                "king": self[P(4, 0)].contents is King
                and self[P(0, 0)].contents is Rook,
                "queen": self[P(4, 0)].contents is King
                and self[P(7, 0)].contents is Rook,
            },
            Player.BLACK: {
                "king": self[P(4, 7)].contents is King
                and self[P(0, 7)].contents is Rook,
                "queen": self[P(4, 7)].contents is King
                and self[P(7, 7)].contents is Rook,
            },
        }

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
        if isinstance(move, PlaceMine):
            # check that the player has mines remaining
            if self.initial_moves[move.player]["mines"] <= 0:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # check that the mine is on the allowed rows
            if move.origin.y not in (3, 4):
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

        elif isinstance(move, PlaceTrapdoor):
            # check that the player has trapdoors remaining
            if self.initial_moves[move.player]["trapdoors"] <= 0:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # check that the trapdoor is on the allowed rows
            if move.origin.y not in (2, 3, 4, 5):
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

        elif isinstance(move, NullMove):
            # Null moves are only valid if there are initial moves remaining
            if (
                self.initial_moves[move.player]["trapdoors"] <= 0
                and self.initial_moves[move.player]["mines"] <= 0
            ):
                return Failure(Error.ILLEGAL_MOVE % move.canonical())

        else:
            # check that an even number of initial moves have been made
            # the values of initial_moves at this point can be 0, 2 or 4
            if self.initial_moves["total"] % 2 != 0:
                return Failure(Error.ILLEGAL_MOVE % move.canonical())
            # set the initial moves to 0 for both players and both types of obstacle
            self.initial_moves = {
                "total": 0,
                Player.WHITE: {"mines": 0, "trapdoors": 0},
                Player.BLACK: {"mines": 0, "trapdoors": 0},
            }
            if isinstance(move, PlaceWall):
                # Due to the way the PlaceWall move is constructed, we can assume that the move is valid if both the origin and destination are on the board, which is checked above
                back, front = Wall.coords_to_walls(move.origin, move.destination)
                # check that the wall does not already exist
                if self[move.origin].walls & move.wall:
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())
            else:
                if move not in self.get_moves(move.origin):
                    return Failure(move)
                return Success(move)
            # elif isinstance(move, Castle):
            #     # check that the king is not moving into or across check or another piece
            #     pos = move.origin
            #     while pos != move.destination:
            #         # adjust the position
            #         pos = pos + move.delta
            #         target = self[pos]
            #         if target.contents is None and not self.being_attacked_at(
            #             pos, move.player.opponent()
            #         ):
            #             continue
            #         return Failure(Error.ILLEGAL_MOVE % move.canonical())

            #     # check that the player has the right to castle
            #     if isinstance(move, KingCastle):
            #         if not self.state.castling[self.state.player]["king"]:
            #             return Failure(Error.ILLEGAL_MOVE % move.canonical())

            #     elif isinstance(move, QueenCastle):
            #         if not self.state.castling[self.state.player]["queen"]:
            #             return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # elif isinstance(move, Promotion):
            #     # check that the moving piece is a pawn
            #     if not isinstance(self[move.origin].contents, Pawn):
            #         return Failure(Error.ILLEGAL_MOVE % move.canonical())

            #     # check that the pawn is moving to the correct row
            #     if not (
            #         (move.destination.y == 0 and move.player == Player.WHITE)
            #         or (move.destination.y == 7 and move.player == Player.BLACK)
            #     ):
            #         return Failure(Error.ILLEGAL_MOVE % move.canonical())

            #     # check that the pawn is not promoting to a king or pawn
            #     if move.promotion is King or move.promotion is Pawn:
            #         return Failure(Error.ILLEGAL_MOVE % move.canonical())

            # elif isinstance(move, Move):
            #     self[move.origin].contents
            #     # check that the piece is moving to a valid position
            #     valid_moves = self.get_moves(move.origin)
            #     if move.destination not in valid_moves:
            #         return Failure(Error.ILLEGAL_MOVE % move.canonical())

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
        if isinstance(move, PlaceMine):
            new_board[move.origin].mined = True
            new_board.state.clock = 0
            new_board.initial_moves[move.player]["mines"] -= 1
            new_board.initial_moves["total"] -= 1

        elif isinstance(move, PlaceTrapdoor):
            new_board[move.origin].trapdoor = TrapdoorState.HIDDEN
            new_board.state.clock = 0
            new_board.initial_moves[move.player]["trapdoors"] -= 1
            new_board.initial_moves["total"] -= 1

        elif isinstance(move, NullMove):
            # decrement the initial moves counter to show that a move has been made
            new_board.initial_moves["total"] -= 1
        else:
            if isinstance(move, PlaceWall):
                new_board.state.walls[move.player] -= 1
                new_board[move.origin].walls |= move.wall
                new_board[move.wall.blocking(move.origin)].walls |= move.wall.alternate()

            elif isinstance(move, Castle):
                new_board._castle(move)

            elif isinstance(move, Promotion):
                new_board.move_piece(move)
                new_board[move.destination].contents = move.promotion(move.player)

            elif isinstance(move, Move):
                new_board.move_piece(move)

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

    def move_piece(
        self, move: Move
    ):
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
            elif (
                self.state.enpassant and dest == self.state.enpassant
            ):  # perform enpassant capture
                capture_pos = Position(
                    dest.x, origin.y
                )  # the capture position has the same y as the origin and the same x as the destination
                capture = self[capture_pos].contents
                self[capture_pos].contents = None
            else:  # reset enpassant target
                self.state.enpassant = None
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
        # check for mine detonation
        if dest_node.mined:
            # set the halfmove clock to 0
            self.state.clock = 0

            self.detonate_mine(dest)

            self.mine_detonated = True

        # check for trapdoor opening
        if dest_node.trapdoor is not TrapdoorState.NONE:
            # set the halfmove clock to 0
            self.state.clock = 0
            # open the trapdoor if it is hidden
            if dest_node.trapdoor is TrapdoorState.HIDDEN:
                dest_node.trapdoor = TrapdoorState.OPEN
            dest_node.contents = None

        return capture
