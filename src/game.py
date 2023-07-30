from src.board import Board, Move
import enum

class Player(enum.Enum):
    WHITE = enum.auto()
    BLACK = enum.auto()
    

class __BoardStack:
    def __init__(self) -> None:
        self.__stack = []
        
    def __iter__(self):
        return iter(self.__stack)
    
    def push(self, move: Move, board: Board) -> None:
        self.__stack.append((board, move))
        
    def pop(self) -> tuple[Board, Move]:
        return self.__stack.pop()
    
    @property
    def moves(self) -> list[Move]:
        """The moves in the stack, in order.
        """
        return [move for _, move in self.__stack]
    
    @property
    def boards(self) -> list[Board]:
        """The boards in the stack, in order.
        """
        return [board for board, _ in self.__stack]
    
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
        return ''.join([f"{move}\n" for move in self.moves])

class Game:
    """Represents a game of obstacle chess.

    This class is responsible for the game loop, and for handling the game state, including the board, pieces, and players.
    """
    def __init__(self, board: Board = Board.starting_Board()) -> None:
        # The game's history, as a stack of (board, move) tuples
        self.history : __BoardStack = __BoardStack()
        
        # The current board
        self.board : Board = board
        
    def __iter__(self):
        return iter(self.history)
        