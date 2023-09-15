from typing import List, Tuple, overload
from board import Board, TrapdoorState, Wall
from move import Move
from common import *
from movehandler import MoveSource


class Game:
    """Represents a game of obstacle chess.

    This class is responsible for the game loop, and for handling the game state, including the board, pieces, and players.
    """

    class _StackEntry:
        """Represents an entry in the game history stack."""

        def __init__(self, board: Board, move: Move) -> None:
            if not isinstance(board, Board) and not isinstance(move, Move):
                raise TypeError
            self.board = board
            self.move = move

    class _BoardStack:
        """A stack implementation for game history."""

        def __init__(self) -> None:
            self.__stack: list = []

        def __iter__(self):
            return iter(self.__stack)

        def push(
            self, move: Move, board: Board
        ) -> Result["Game._StackEntry"]:  ## TODO: tuple ordering here is kinda screwey
            self.__stack.append(entry := Game._StackEntry(board, move))
            return Success(entry)

        def pop(self) -> "Game._StackEntry":
            return self.__stack.pop()

        @property
        def boards(self) -> list:
            """The boards in the stack, in order."""
            return [entry.board for entry in self.__stack]

        @property
        def moves(self) -> list:
            """The moves in the stack, in order."""
            return [entry.move for entry in self.__stack]

        def __len__(self) -> int:
            return len(self.__stack)

        @overload
        def __getitem__(self, index: int) -> "Game._StackEntry":
            ...

        @overload
        def __getitem__(self, index: slice) -> List["Game._StackEntry"]:
            ...

        def __getitem__(self, index):
            return self.__stack[index]

        def as_move_string(self) -> str:
            """Returns a string representing the moves in the stack in standard algebraic notation.

            Returns
            -------
            str
                The moves in the stack in standard algebraic notation, with trailing newlines.
            """
            return "".join([f"{move}\n" for move in self.moves])

    ###############
    #   Internal  #
    ###############

    def __init__(self, board: Board) -> None:
        # The game's history, as a stack of (board, boardstate, move) tuples
        self.history: Game._BoardStack = Game._BoardStack()

        # The game's move sinks
        self.sinks: list = []

        # the games move sources
        self.source: MoveSource

        # The current board
        self.board: Board = board

        # Whether or not the game is completed (i.e. no more moves to be played, or game over)
        self.completed = False

    def set_move_source(self, move_gen: MoveSource):
        self.source = move_gen
    
    def __iter__(self):
        return iter(self.history)

    def __repr__(self) -> str:
        return f"Game({self.board})"

    @classmethod
    def from_board(cls, board: Board) -> Result["Game"]:
        game = cls(board)
        validation = game.validate()
        return validation if isinstance(validation, Failure) else Success(game)
    
    def canonical(self) -> str:
        """Returns a string representing the game in canonical form.

        This is the representation used when writing the game to a file.

        Returns
        -------
        str
            The canonical representation of the game.
        """
        return f"{self.board.canonical()}\n{self.board.state.canonical()}"

    ###############
    # Validation  #
    ###############

    def validate(self) -> Result[None]:
        """Validates a games current board and state.

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
                        return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())

                    # too many trapdoors
                    if trapdoors > 2:
                        return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())

                # mines count and position
                if node.mined:
                    mines += 1

                    # mine out of bounds
                    if y not in [3, 4]:
                        return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())

                    # too many mines
                    if mines > 2:
                        return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())

                # walls count (South and West walls only, as the board errors on these walls)
                if node.walls & (Wall.SOUTH | Wall.WEST):
                    # Add one to the wall count if there is a wall to the south
                    if node.walls & Wall.SOUTH:
                        walls += 1
                        # wall on last row
                        if y == 7:
                            return Failure(
                                Error.ILLEGAL_BOARD % Position(x, y).canonical()
                            )
                    # Add one to the wall count if there is a wall to the west
                    if node.walls & Wall.WEST:
                        walls += 1
                        # wall on first column
                        if x == 0:
                            return Failure(
                                Error.ILLEGAL_BOARD % Position(x, y).canonical()
                            )
                    # too many walls on board and in reserve
                    if walls > 6:
                        return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())

                # pieces count
                if node.contents is not None:
                    # update the piece count for the player this node belongs to
                    pieces[node.contents.owner][node.contents.name] += 1

                    # calculate the number of promotions available to the player who owns this piece
                    allowed_promotions = 8 - pieces[node.contents.owner]["pawn"]

                    # we only need to check piece counts if the pice count has changed

                    # pawns
                    if node.contents.name == "pawn":
                        # too many pawns
                        if pieces[node.contents.owner]["pawn"] > 8:
                            return Failure(
                                Error.ILLEGAL_BOARD % Position(x, y).canonical()
                            )

                        # recalculate the number of promotions available to the player who owns this piece, now that we have discovered a pawn
                        allowed_promotions = 8 - pieces[node.contents.owner]["pawn"]

                        # to many of other pieces given number of promotions available
                        if allowed_promotions < promotions[node.contents.owner]:
                            # Too many promoted pieces
                            return Failure(
                                Error.ILLEGAL_BOARD % Position(x, y).canonical()
                            )
                        # pawns on the back rank
                        if y in [0, 7]:
                            return Failure(
                                Error.ILLEGAL_BOARD % Position(x, y).canonical()
                            )

                    # rooks, bishops and knights
                    elif (piece := node.contents.name) in ["rook", "bishop", "knight"]:
                        # update promotions
                        if pieces[node.contents.owner][piece] > 2:
                            # if there are more than 2 rooks, there there must have been a promotion
                            promotions[node.contents.owner] += 1

                    # queens
                    elif node.contents.name == "queen":
                        # update promotions
                        if pieces[node.contents.owner]["queen"] > 1:
                            # if there are more than 2 rooks, there there must have been a promotion
                            promotions[node.contents.owner] += 1

                    # kings
                    elif node.contents.name == "king":
                        # too many kings
                        if pieces[node.contents.owner]["king"] > 1:
                            return Failure(
                                Error.ILLEGAL_BOARD % Position(x, y).canonical()
                            )

                    # too many promotions
                    if promotions[node.contents.owner] > allowed_promotions:
                        return Failure(Error.ILLEGAL_BOARD % Position(x, y).canonical())
        # too many pieces in total
        for player in pieces:
            if sum(pieces[player].values()) > 16:
                # find last node with a piece of the offending color
                last: tuple | None = None
                for y, row in enumerate(self.board):
                    for x, node in enumerate(row):
                        if node.contents is not None and node.contents.owner == player:
                            last = (x, y)
                if last is not None:
                    return Failure(Error.ILLEGAL_BOARD % Position(7, 7).canonical())

        if pieces[Player.WHITE]["king"] < 1 or pieces[Player.BLACK]["king"] < 1:
            return Failure(Error.ILLEGAL_BOARD % Position(7, 7).canonical())

        # number of walls in existence is not six
        if walls + sum(self.board.state.walls.values()) != 6:
            return Failure(Error.ILLEGAL_STATUSLINE)

        # Validation succeeded, return Success
        return Success(None)

    ###############
    #    Moves    #
    ###############
    
    def play(self):
        """Starts the game loop."""
        fifty_moves_announced = False
        init = True
        while not self.completed:
            if not init:
                # check for special conditions
                # keep track of whether a draw by fifty moves has been announced
                # this is so that the draw by fifty moves is only announced once per stalemated position due to fifty moves
                if self.board.state.clock < 100:
                    fifty_moves_announced = False
                # if not checkmate, check for check
                if self.board.in_check():
                    print("INFO: " + Info.CHECK)
                # stalemate
                elif self.board.stalemate():
                    # dont return success, as game can be played past a stalemate
                    print("INFO: " + Info.STALEMATE)
                # draw by fifty moves
                if self.board.state.clock >= 100 and not fifty_moves_announced:
                    print("INFO: " + Info.DRAW_FIFTY)
                    fifty_moves_announced = True
                # draw by threefold repetition
                if self.threefold_repetition():
                    # TODO: should this be announced every time it occurs, or only once per run of moves?
                    # i.e. for move A and B, does AB AB AB AB get announced once, or twice?
                    print("INFO: " + Info.DRAW_THREEFOLD)
            init = False
            
            # get the next move
            move_res = self.get_next_move()
            if isinstance(move_res, Failure):
                return move_res
            
            move = move_res.unwrap()
            # check if we have run out of moves
            if move is None:
                self.completed = True
            else:
                # apply the move
                board_res = self.board.apply_move(move)
                if isinstance(board_res, Failure):
                    return move_res

                # push the move and board to the history
                self.history.push(move, self.board)

                # set the new board
                self.set_board(board_res.unwrap())
                
                # if the player who just moved is in check, their move was illegal
                if self.board.in_check(move.player):
                    return Failure(Error.ILLEGAL_MOVE % move.canonical())
                
                # checkmate
                if self.board.checkmate():
                    print("INFO: " + Info.CHECKMATE)
                    self.completed = True
                
        # check that the next move pulled is None or Success(None)
        # try to pull another move from the source
        trailing_move_res = self.get_next_move()
        inner = trailing_move_res.unwrap()
        # if a move was pulled, it is illegal
        if inner is not None:
                return Failure(Error.ILLEGAL_MOVE % inner.canonical())
        
    def set_board(self, new_board) -> Result[Board]:
        self.board = new_board
        return Success(new_board)

    def get_next_move(self) -> Result[Union[Move, None]]:
        fetch = self.source.get_next()
        if fetch.unwrap() is None or self.source.exhausted:
            return Success(None)
        
        elif isinstance(fetch, Failure):
            return fetch
        
        elif isinstance(fetch, Success):
            return self.board.validate_move(fetch.unwrap())
        
        else:
            return Failure()

    def threefold_repetition(self) -> bool:
        """Checks if the game is in a threefold repetition.

        Returns
        -------
        bool
            Whether or not the game is in a threefold repetition state.
        """
        # only check if there are at least 3 moves in the history
        if len(self.history) > 3:
            positions = 0
            # compare the current board to all the boards in the history
            for board in self.history.boards:
                # if the board is identical to the current board, increment the positions counter
                if self.board == board:
                    positions += 1
                # if there are 3 or more identical positions, the game is in a threefold repetition
                if positions >= 3:
                    return True
        return False

    ###############
    #   Outputs   #
    ###############
    
    def dump(self, file=sys.stdout):
        """Dumps the board and state to a stream"""
        file.write(self.canonical())

    def dump_board(self, file=sys.stdout):
        """Dumps the board to a stream"""
        file.write(self.board.canonical())
