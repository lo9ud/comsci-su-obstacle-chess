from src.board import Board, BoardNode, Move, BoardState, TrapdoorState, Wall
from src.piece import Piece
from src.output import *
from src.common import *
import enum

    



class Game:
    """Represents a game of obstacle chess.

    This class is responsible for the game loop, and for handling the game state, including the board, pieces, and players.
    """
    
    class __BoardStack:
        """A stack implementation for game history.
        """
        
        def __init__(self) -> None:
            self.__stack : list[tuple[Board, BoardState, Move]] = []
            
        def __iter__(self):
            return iter(self.__stack)
        
        def push(self, move: Move, board: Board, state: BoardState) -> None:
            self.__stack.append((board, state, move))
            
        def pop(self) -> tuple[Board, BoardState, Move]:
            return self.__stack.pop()
        
        @property
        def boards(self) -> list[Board]:
            """The boards in the stack, in order.
            """
            return [board for board, _, _ in self.__stack]
        
        @property
        def states(self) -> list[BoardState]:
            """The states in the stack, in order
            """
            return [state for _, state, _ in self.__stack]
        
        @property
        def moves(self) -> list[Move]:
            """The moves in the stack, in order.
            """
            return [move for _, _, move in self.__stack]
        
        def __len__(self) -> int:
            return len(self.__stack)
        
        def __getitem__(self, index: int) -> tuple[Board, BoardState, Move]:
            return self.__stack[index]
        
        def as_move_string(self) -> str:
            """Returns a string representing the moves in the stack in standard algebraic notation.

            Returns
            -------
            str
                The moves in the stack in standard algebraic notation, separated by newlines.
            """
            return ''.join([f"{move}\n" for move in self.moves])
        
    def __init__(self, board: Board = Board.standard_board(), state:BoardState = BoardState.standard_state()) -> None:
        # The game's history, as a stack of (board, boardstate, move) tuples
        self.history : Game.__BoardStack = Game.__BoardStack()
        
        # The current board
        self.board : Board = board
        self.state : BoardState = state
        
        self.validate()
    
    def __iter__(self):
        return iter(self.history)
    
    def validate(self) -> None:
        # TODO: must pieces be in original order?
        # TODO: must we verify that the state is valid? (i.e. castling not possible if king has moved, etc.)
        # TODO: where to error on wall count in correct? (defaulting to statusline for now)
        # all counts in the order [white, black]
        mines = 0
        trapdoors = 0
        # The number of walls in reserve is pre-determined, so we don't need to count them
        walls = sum(self.state.walls.values())
        bishops = {
            Player.WHITE: [],
            Player.BLACK: []
        }
        pieces = {
            Player.WHITE: {
                "pawn": 0,
                "knight": 0,
                "bishop": 0,
                "rook": 0,
                "queen": 0,
                "king": 0
            },
            Player.BLACK: {
                "pawn": 0,
                "knight": 0,
                "bishop": 0,
                "rook": 0,
                "queen": 0,
                "king": 0
            }
        }
            
        # populate data
        for y,row in enumerate(self.board):
            for x,node in enumerate(row):
                # trapdoor count and position
                if node.trapdoor in [TrapdoorState.OPEN , TrapdoorState.HIDDEN]:
                    trapdoors += 1
                    # trapdoor out of bounds
                    if y not in [2,3,4,5]:
                        raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                    # too many trapdoors
                    if trapdoors > 2:
                        raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                # mines count and position
                if node.mined:
                    mines += 1
                    # mine out of bounds
                    if y not in [3,4]:
                        raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                    # too many mines
                    if mines > 2:
                        raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                # walls count (South and West walls only, as the board errors on these walls)
                if node.walls == Wall.SOUTH | Wall.WEST:
                    walls += 1
                    # too many walls on board and in reserve
                    if walls > 6:
                        raise BoardError(Error.ILLEGAL_STATUSLINE, None)
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
                                raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                            
                            # pawns on the back rank
                            if y in [0,7]:
                                raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                            
                        # knights
                        case "knight":
                            # too many knights, given the number of pawns
                            if pieces[node.contents.player]["pawn"] == 8 and pieces[node.contents.player]["knight"] > 2:
                                raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                            
                        # bishops
                        case "bishop":
                            # too many bishops, given the number of pawns
                            if pieces[node.contents.player]["pawn"] == 8 and pieces[node.contents.player]["bishop"] > 2:
                                raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                            
                            # add the bishop to the list of bishop positions
                            bishops[node.contents.player].append((x,y))
                            
                        # rooks
                        case "rook":
                            # too many rooks, given the number of pawns
                            if pieces[node.contents.player]["pawn"] == 8 and pieces[node.contents.player]["rook"] > 2:
                                raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                            
                        # queens
                        case "queen":
                            # too many queens, given the number of pawns
                            if pieces[node.contents.player]["pawn"] == 8 and pieces[node.contents.player]["queen"] > 1:
                                raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                            
                        case "king":
                            # too many kings
                            if pieces[node.contents.player]["king"] > 1:
                                raise BoardError(Error.ILLEGAL_BOARD, algebraic(x,y))
                
        # validate last rules
        # too few of any piece
        # TODO: what position do we error on if too few pieces? (defaulting to (7,7))
        # for each player
        for player in pieces:
            # TODO: can there be *less* than 16 pieces at start? if so, need flag for whether this is a unplayed board, or a new one
            if sum(pieces[player].values()) > 16:
                # find last node with a piece
                last: tuple[int,int]|None = None
                for y,row in enumerate(self.board):
                    for x,node in enumerate(row):
                        if node.contents is not None:
                            last = (x,y)
                if last is not None:
                    raise BoardError(Error.ILLEGAL_BOARD, algebraic(*last))
                else:
                    pass #There are no pieces on the board.
                #TODO: what position to error on if no pieces
            # for each of their pieces
            for piece in pieces[player]:
                # if there are too few of that piece, and it's not a king or pawn
                if pieces[player][piece] < 2 and piece not in ["king", "pawn"]:
                    raise BoardError(Error.ILLEGAL_BOARD, algebraic(7,7))
                
        if pieces[Player.WHITE]["king"] < 1 or pieces[Player.BLACK]["king"] < 1:
            raise BoardError(Error.ILLEGAL_BOARD, algebraic(7,7))
        # bishops on the same color
        for player in bishops:
            # calculate which squares the bishops are on (black or white)
            bishop_squares = list(map(lambda pos: (pos[0] + pos[1]) % 2, bishops[player]))
            # if there is not at least one on each color
            if not(0 in bishop_squares and 1 in bishop_squares):
                # TODO: which square to error on for this rule? (defaulting to last placed bishop)
                raise BoardError(Error.ILLEGAL_BOARD, bishops[player][-1])
    
    def play_move(self, move: Move) -> None:
        """Plays the given move.

        Parameters
        ----------
        move : Move
            The move to play.
        """
        self.history.push(move, self.board, self.state)
        self.board = self.board.apply_move(move)
        