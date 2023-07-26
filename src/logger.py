import sys
from typing import Callable, TextIO
import stdio
import enum

class StdOut(TextIO):
    def __init__(self) -> None:
        pass
        
    def write(self, message: str) -> None:
        stdio.print(message)
        
class Errors(enum.Enum):
    illegal_move = enum.auto()
    illegal_board = enum.auto()
    illegal_status = enum.auto()
    
class Infos(enum.Enum):
    check = enum.auto()
    checkmate = enum.auto()
    stalemate = enum.auto()
    draw_fifty = enum.auto()
    draw_threefold = enum.auto()
    
class Logger:
        
    def __init__(self, outstream: TextIO) -> None:
        self.outstream = outstream
        
    def error(self, type: Errors, param: str|None = None) -> None:
        match type:
            case Errors.illegal_board:
                if param == None: raise ValueError
                message = "illegal board at {pos}"%param
            case Errors.illegal_move:
                if param == None: raise ValueError
                message = "illegal move {move}"%param
            case Errors.illegal_status:
                message = "illegal baord at status line"
        self.outstream.write(f"ERROR: {message}\n")
        # TODO: Confirm error behaviour
        sys.exit(1)
        
    def info(self, type: Infos) -> None:
        match type:
            case Infos.check:
                message = "check"
            case Infos.checkmate:
                message = "checkmate"
            case Infos.stalemate:
                message = "stalemate"
            case Infos.draw_fifty:
                message = "draw due to fifty moves"
            case Infos.draw_threefold:
                message = "draw due to threefold repetition"
        self.outstream.write(f"INFO: {message}\n")