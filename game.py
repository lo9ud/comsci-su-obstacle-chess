from board import Board, TrapdoorState, Wall
from move import Move
from common import *
from movehandler import MoveSink, MoveSource


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

        def push(self, move: Move, board: Board) -> Result[tuple[Board, Move]]:
            self.__stack.append((board, move))
            return Success((board, move))

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

        # The game's move sinks
        self.sinks: list[MoveSink] = []

        # the games move sources
        self.sources: list[MoveSource] = []

        # The current board
        # If no board is provided, instantiate a standard one
        if board is None:
            board = Board.standard_board().unwrap()
        self.board: Board = board

    @classmethod
    def from_board(cls, board: Board) -> Result[Self]:
        game = cls(board)
        validation = game.validate()
        return validation if isinstance(validation, Failure) else Success(game)

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

    def validate(self) -> Result[None | str]:
        """Validates a game.

        Uses data from the board and the curretn board state to validate the game.

        Returns
        -------
        Result
            Whether or not the game is valid.
        """
        # the count of mines on the board
        mines = 0

        # the count of trapdoors on the board
        trapdoors = 0

        # The number of walls on the board
        walls = 0

        # the number of promoted pieces on the board
        promotions: dict[Player, int] = {
            Player.WHITE: 0,
            Player.BLACK: 0,
        }

        # each players piece count
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

        # populate data and verify in-place rules (too many of something etc)
        for y, row in enumerate(self.board):
            for x, node in enumerate(row):
                # trapdoor count and position
                if node.trapdoor in [
                    TrapdoorState.OPEN,
                    TrapdoorState.HIDDEN,
                ]:
                    trapdoors += 1

                    # trapdoor out of bounds
                    if y not in [2, 3, 4, 5]:
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                    # too many trapdoors
                    if trapdoors > 2:
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                # mines count and position
                if node.mined:
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
                    if node.walls & Wall.SOUTH:
                        walls += 1
                        # wall on last row
                        if y == 7:
                            return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                    # Add one to the wall count if there is a wall to the west
                    if node.walls & Wall.WEST:
                        walls += 1
                        # wall on first column
                        if x == 0:
                            return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                    # too many walls on board and in reserve
                    if walls > 6:
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                # pieces count
                if node.contents is not None:
                    # update the piece count for the player this node belongs to
                    pieces[node.contents.owner][node.contents.name] += 1

                    # calculate the number of promotions available to the player who owns this piece
                    allowed_promotions = 8 - pieces[node.contents.owner]["pawn"]

                    # we only need to check piece counts if the pice count has changed
                    match node.contents.name:
                        # pawns
                        case "pawn":
                            # too many pawns
                            if pieces[node.contents.owner]["pawn"] > 8:
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                            # recalculate the number of promotions available to the player who owns this piece, now that we have discovered a pawn
                            allowed_promotions = 8 - pieces[node.contents.owner]["pawn"]

                            # to many of other pieces given number of promotions available
                            if allowed_promotions < promotions[node.contents.owner]:
                                # Too many promoted pieces
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
                            # pawns on the back rank
                            if y in [0, 7]:
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                        # rooks, bishops and knights
                        case "rook" | "bishop" | "knight" as piece:
                            # update promotions
                            if pieces[node.contents.owner][piece] > 2:
                                # if there are more than 2 rooks, there there must have been a promotion
                                promotions[node.contents.owner] += 1

                        # queens
                        case "queen":
                            # update promotions
                            if pieces[node.contents.owner]["queen"] > 1:
                                # if there are more than 2 rooks, there there must have been a promotion
                                promotions[node.contents.owner] += 1

                        # kings
                        case "king":
                            # too many kings
                            if pieces[node.contents.owner]["king"] > 1:
                                return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))

                    # too many promotions
                    if promotions[node.contents.owner] > allowed_promotions:
                        return Failure(Error.ILLEGAL_BOARD % algebraic(x, y))
        # too many pieces in total
        for player in pieces:
            if sum(pieces[player].values()) > 16:
                # find last node with a piece of the offending color
                last: tuple[int, int] | None = None
                for y, row in enumerate(self.board):
                    for x, node in enumerate(row):
                        if node.contents is not None and node.contents.owner == player:
                            last = (x, y)
                if last is not None:
                    return Failure(Error.ILLEGAL_BOARD % algebraic(7, 7))

        if pieces[Player.WHITE]["king"] < 1 or pieces[Player.BLACK]["king"] < 1:
            return Failure(Error.ILLEGAL_BOARD % algebraic(7, 7))

        # number of walls in existence is not six
        if walls + sum(self.board.state.walls.values()) != 6:
            return Failure(Error.ILLEGAL_STATUSLINE)

        # Validation succeeded, return Success
        return Success(None)

    def set_board(self, new_board) -> Result[Board]:
        self.board = new_board
        return Success(new_board)

    def play_move(self, move_str: str) -> Result[Board]:
        """Plays the given move.

        Parameters
        ----------
        move : Move
            The move to play.
        """
        # Create the move from the provided string
        move_result = Move.from_str(self.board.state.player, move_str)
        if isinstance(move_result, Failure):
            return Failure(Error.ILLEGAL_MOVE % move_str)
        move = move_result.unwrap()
        play_result = (
            self.history.push(move, self.board)
            .and_then(
                # Apply the move to the board
                lambda board_move: self.board.apply_move(board_move[1])
            )
            .and_then(
                # Set the current board to the new one
                lambda new_board: self.set_board(new_board)
            )
        )  # If any of these fail, the Failure passes through

        # If the move was successful, send the move to the outputs
        if isinstance(play_result, Success):
            for sink in self.sinks:
                sink.send(move)
        # Return the result of the move
        return play_result

    def register_output(self, output: MoveSink) -> None:
        """Registers an output to send board updates to.

        Parameters
        ----------
        output : Output
            The output to register.
        """
        self.sinks.append(output)

    def dump_output(self):
        """Dumps all output to the registered outputs."""
        for sink in self.sinks:
            sink.dump()

    def dump_board(self, stream=sys.stdout):
        """Dumps the board to a stream"""
        stream.write(self.board.canonical())
