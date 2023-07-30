import enum
import stdio

class Error(enum.Enum):
    ILLEGAL_MOVE = "illegal move at %s"
    ILLEGAL_BOARD = "illegal board at %s"
    ILLEGAL_STATUSLINE = "illegal board at statusline"

class Info(enum.Enum):
    CHECK = "check"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    DRAW_FIFTY = "draw due to fifty moves"
    DRAW_THREEFOLD = "draw due to threefold repetition"

def print_error(error: Error, param: str|None = None):
    stdio.writeln(f"ERROR: {error.value%param if param else error}")

def print_info(info: Info, param: str|None = None):
    raise NotImplementedError

class BoardError(Exception):
    def __init__(self, error: Error, param: str|None = None) -> None:
        super().__init__(error.value%param if param else error)
        self.error = error
        self.param = param
        