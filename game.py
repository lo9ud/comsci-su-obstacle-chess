from board import Board, TrapdoorState, Wall
from move import Move
from output import *
from common import *


class Game:
    """Represents a game of obstacle chess.

    This class is responsible for the game loop, and for handling the game state, including the board, pieces, and players.
    """

    class __BoardStack:
        """A stack implementation for game history."""

        def __init__(self) -> None:
            self.__stack: list[tuple[Board, Move]] = []

        def __iter__(self):
            return iter(self.__stack)

        def push(self, move: Move, board: Board) -> Result:
            self.__stack.append((board, move))
            return Success((move, board))

        def pop(self) -> tuple[Board, Move]:
            return self.__stack.pop()

        @property
        def boards(self) -> list[Board]:
            """The boards in the stack, in order."""
            return [board for board, _ in self.__stack]

        @property
        def moves(self) -> list[Move]:
            """The moves in the stack, in order."""
            return [move for _, move in self.__stack]

        def __len__(self) -> int:
            return len(self.__stack)

        def __getitem__(self, index: int) -> tuple[Board, Move]:
            return self.__stack[index]

        def as_move_string(self) -> str:
            """Returns a string representing the moves in the stack in standard algebraic notation.

            Returns
            -------
            str
                The moves in the stack in standard algebraic notation, separated by newlines.
            """
            return "".join([f"{move}\n" for move in self.moves])

    def __init__(self, board: Board | None = None) -> None:
        # The game's history, as a stack of (board, boardstate, move) tuples
        self.history: Game.__BoardStack = Game.__BoardStack()

        # The current board
        # If no board is provided, instantiate a standard one
        if board is None:
            board = Board.standard_board().unwrap()
        self.board: Board = board

    def __iter__(self):
        return iter(self.history)

    def __repr__(self) -> str:
        return f"Game({self.board})"

    def canonical(self) -> str:
        """Returns a string representing the game in canonical form.

        This is the representation used when writing the game to a file.

        Returns
        -------
        str
            The canonical representation of the game.
        """
        return f"{self.board.canonical()}\n{self.board.state.canonical()}"

    def validate(self) -> Result:
        # TODO: must pieces be in original order?
        # TODO: must we verify that the state is valid? (i.e. castling not possible if king has moved, etc.)
        # TODO: where to error on wall count incorrect? (defaulting to statusline for now)
        # all counts in the order [white, black]
        mines = 0
        trapdoors = 0
        # The number of walls in reserve is pre-determined, so we don't need to count them
        walls = 0
        bishops = {Player.WHITE: [], Player.BLACK: []}
        pieces = {
            Player.WHITE: {
                "pawn": 0,
                "knight": 0,
                "bishop": 0,
                "rook": 0,
                "queen": 0,
                "king": 0,
            },
            Player.BLACK: {
                "pawn": 0,
                "knight": 0,
                "bishop": 0,
                "rook": 0,
                "queen": 0,
                "king": 0,
            },
        }

        # populate data
        for y, row in enumerate(self.board):
            for x, node in enumerate(row):
                # trapdoor count and position
                if node.trapdoor in [
                    TrapdoorState.OPEN,
                    TrapdoorState.HIDDEN,
                ]:  # TODO: how to know number of trapdoors remaining? - Answered: They are placed in the beginning or not at all.
                    trapdoors += 1
                    # trapdoor out of bounds
                    if y not in [2, 3, 4, 5]:
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                    # too many trapdoors
                    if trapdoors > 2:
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                # mines count and position
                if (
                    node.mined
                ):  # TODO: how to know number of mines remaining? - Answered: They are placed in the beginning or not at all.
                    mines += 1
                    # mine out of bounds
                    if y not in [3, 4]:
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                    # too many mines
                    if mines > 2:
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                # walls count (South and West walls only, as the board errors on these walls)
                if node.walls & (Wall.SOUTH | Wall.WEST):
                    # Add one to the wall count if there is a wall to the south
                    walls += (node.walls & Wall.SOUTH) >> 1
                    # Add one to the wall count if there is a wall to the west
                    walls += (node.walls & Wall.WEST) >> 3
                    # too many walls on board and in reserve
                    if walls > 6:
                        # TODO: Board or statusline error?
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                # pieces count
                if node.contents is not None:
                    # update the piece count
                    pieces[node.contents.player][node.contents.name] += 1

                    # we only need to check piece counts if the pice count has changed
                    match node.contents.name:
                        # pawns
                        case "pawn":
                            # too many pawns
                            if pieces[node.contents.player]["pawn"] > 8:
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                            # pawns on the back rank
                            if y in [0, 7]:
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                        # knights
                        case "knight":
                            # too many knights, given the number of pawns
                            if (
                                pieces[node.contents.player]["pawn"] == 8
                                and pieces[node.contents.player]["knight"] > 2
                            ):
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                        # bishops
                        case "bishop":
                            # too many bishops, given the number of pawns
                            if (
                                pieces[node.contents.player]["pawn"] == 8
                                and pieces[node.contents.player]["bishop"] > 2
                            ):
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                            # add the bishop to the list of bishop positions
                            bishops[node.contents.player].append((x, y))

                        # rooks
                        case "rook":
                            # too many rooks, given the number of pawns
                            if (
                                pieces[node.contents.player]["pawn"] == 8
                                and pieces[node.contents.player]["rook"] > 2
                            ):
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                        # queens
                        case "queen":
                            # too many queens, given the number of pawns
                            if (
                                pieces[node.contents.player]["pawn"] == 8
                                and pieces[node.contents.player]["queen"] > 1
                            ):
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                        case "king":
                            # too many kings
                            if pieces[node.contents.player]["king"] > 1:
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

        # validate last rules
        # too few of any piece
        # TODO: what position do we error on if too few pieces? (defaulting to (7,7))
        # for each player
        for player in pieces:
            # TODO: can there be *less* than 16 pieces at start? if so, need flag for whether this is a unplayed board, or a new one
            if sum(pieces[player].values()) > 16:
                # find last node with a piece
                last: tuple[int, int] | None = None
                for y, row in enumerate(self.board):
                    for x, node in enumerate(row):
                        if node.contents is not None:
                            last = (x, y)
                if last is not None:
                    return Failure(Error.ILLEGAL_BOARD % algebraic(*last))
                    # TODO: what position to error on if no pieces

            # for each of their pieces
            for piece in pieces[player]:
                match piece:
                    # There must be at least one king and one queen
                    case "king" | "queen":
                        if pieces[player][piece] < 1:
                            return Failure(Error.ILLEGAL_BOARD % algebraic(7, 7))

                    # There must be at least two of each of the other pieces (except pawns)
                    case "knight" | "bishop" | "rook":
                        if pieces[player][piece] < 2:
                            return Failure(Error.ILLEGAL_BOARD % algebraic(7, 7))

        if pieces[Player.WHITE]["king"] < 1 or pieces[Player.BLACK]["king"] < 1:
            return Failure(Error.ILLEGAL_BOARD % algebraic(7, 7))
        # bishops on the same color
        for player in bishops:
            # calculate which squares the bishops are on (black or white)
            bishop_squares = list(
                map(
                    is_white,
                    [i for i, j in bishops[player]],
                    [j for i, j in bishops[player]],
                )
            )
            # if there is not at least one on each color (given that there are at least two bishops)
            if (0 not in bishop_squares or 1 not in bishop_squares) and len(bishops) < 2:
                # TODO: which square to error on for this rule? (defaulting to last placed bishop)
                return Failure(Error.ILLEGAL_BOARD % algebraic(*bishops[player][-1]))

        # number of walls in reserve too many
        if walls + sum(self.board.state.walls.values()) > 6:
            return Failure(Error.ILLEGAL_STATUSLINE)

        # Validation succeeded, return Success
        return Success(None)

    def set_board(self, new_board):
        self.board = new_board

    def play_move(self, move_str: str) -> Result:
        """Plays the given move.

        Parameters
        ----------
        move : Move
            The move to play.
        """
        # Create the move from the provided string
        play_result = Move.from_str(move_str)\
            .and_then(
            # Push the new move and the old board onto the history
            lambda move: self.history.push(move, self.board)
        ).and_then(
            # Apply the move to the board
            lambda move, board: self.board.apply_move(move)
        ).and_then(
            # Set the current board to the new one
            lambda new_board: self.set_board(new_board)
        )  # If any of these fail, the Failure passes through and is returned
        return play_result
