import sys
from typing import Any, TextIO
from src.piece import Piece
from src.common import *
from src.output import *
import enum

class TrapdoorState(enum.Enum):
    """The possible states of a trapdoor.
    """
    NONE = enum.auto()
    HIDDEN = enum.auto()
    OPEN = enum.auto()
    @classmethod
    def hide(cls):
        return cls.HIDDEN
    @classmethod
    def open(cls):
        return cls.OPEN
    @classmethod
    def none(cls):
        return cls.NONE

class Wall(enum.Flag):
    NONE = enum.auto()
    NORTH = enum.auto()
    SOUTH = enum.auto()
    EAST = enum.auto()
    WEST = enum.auto()
class BoardNode:
    """Logical representation of a node on the board.

    Maintains info on mines, trapdoors and pieces on the node.
    """
    def __init__(self, contents:Piece|None, mined:bool, trapdoor:TrapdoorState) -> None:
        self.contents = contents
        self.mined = mined
        self.trapdoor = trapdoor
        self.walls = Wall.NONE

class BoardState:
    """Represents the state of the board during a game of obstacle chess.
    
    Holds info about:
     - The current player
     - Castling rights
     - En passant
     - Halfmove clock
    """
    def __init__(self, player:Player, walls:tuple[int,int], castling:tuple[bool,bool,bool,bool], enpassant:BoardNode|None, clock:int) -> None:
        self.player = player
        self.walls = {
            Player.WHITE: walls[0],
            Player.BLACK: walls[1]
        }
        self.castling = {
            Player.WHITE: {
                "king": castling[0],
                "queen": castling[1]
            },
            Player.BLACK: {
                "king": castling[2],
                "queen": castling[3]
            }
        }
        self.enpassant = enpassant
        self.clock = clock
        
    @classmethod
    def from_str(cls, board:"Board", string:str) -> "BoardState":
        """Creates a BoardState from a string.

        The string should be sripped of whitespace.

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
        blocks = list(string)
        player = Player.from_str(blocks[0])
        walls = tuple(map(int, blocks[1:3]))
        castling = tuple(map(lambda x: x == "+", blocks[3:7]))
        enpassant_str = blocks[7]
        if enpassant_str == "-":
            enpassant = None 
        else:
            coordinates = coords(enpassant_str)
            enpassant = board[*coordinates]
        clock = int(blocks[8])
        return cls(player, walls, castling, enpassant, clock)
    
    @classmethod
    def standard_state(cls):
        # TODO: how many walls to start with?
        return cls(Player.WHITE, (3,3), (True,True,True,True), None, 0)
class Board:
    """A representation of the board state.

    Maintains the boards current state, and provides methods for manipulating it.
    """
    def __init__(self, board:list[list[BoardNode]]) -> None:
        # The boards nodes, as a 2D array
        self.__nodes : list[list[BoardNode]] = board
        
    def __getitem__(self, index:tuple[int,int]) -> BoardNode:
        """Returns the node at the given index.
        """
        return self.__nodes[index[0]][index[1]]
    
    def __iter__(self):
        """Iterates over the boards nodes.
        """
        for row in self.__nodes:
            yield row
    
    @classmethod
    def from_str(cls, string : str|list[str]) -> "Board":
        """Returns a board that is in the state described by the given string ,or list of strings.
        
        This string should not contain any comments, or a status line.
        It also should not contain any empty lines, newlines, or whitespace at the start or end of the string.
        """
        # Split the string by lines, and remove empty lines and comments
        if isinstance(string, str):
            raw_lines = string.split("\n")
        elif isinstance(string, list):
            raw_lines = string
        # transform the board lines into a list of lists of characters, such that the wall modifiers are at the end
        lines = []
        for line in raw_lines:
            mod_list = []
            new_line = []
            for char in line:
                # while the character is a modifier, add it to the list
                if char.lower() in ['|','_']:
                    mod_list.append(char)
                    continue
                # add the character and the modifiers to the line, with the wall modifiers at the end
                new_line.append([char] + mod_list)
                # clear the list of modifiers
                mod_list = []
            # add the line to the list of lines
            lines.append(new_line)
        # create the board from the lines
        board = []
        for y,row in enumerate(lines):
            board.append([])
            # Create a node for each character in the line
            for x,char in enumerate(row):
                # Empty node
                if char[0] == ".":
                    board[-1].append(BoardNode(None, False, TrapdoorState.none()))
                
                # a mine or trapdoor
                elif char[0] in ["D", "O", "M", "X"]:
                    match char:
                        # hidden trapdoor
                        case "D":
                            board[-1].append(BoardNode(None, False, TrapdoorState.hide()))
                        # open trapdoor
                        case "O":
                            board[-1].append(BoardNode(None, False, TrapdoorState.open()))
                        # mine
                        case "M":
                            board[-1].append(BoardNode(None, True, TrapdoorState.none()))
                        # hidden trapdoor and a mine
                        case "X":
                            board[-1].append(BoardNode(None, True, TrapdoorState.hide()))
                
                # a piece
                # This is evaluated last, so that isupper and islower can be used to check for pieces and dont get caught on mines/trapdoors
                elif char[0].islower():
                    board[-1].append(BoardNode(Piece.from_str(char[0]), False, TrapdoorState.none()))
                elif char[0].isupper():
                    board[-1].append(BoardNode(Piece.from_str(char[0]), False, TrapdoorState.hide()))
                else:
                    print_error(Error.ILLEGAL_BOARD, algebraic(x, y))
                    sys.exit(1)
                    
                # apply the wall modifiers to the node
                for modifier in char[1:]:
                    match modifier:
                        # west wall
                        case "|":
                            board[-1][-1].walls |= Wall.WEST
                        # east wall
                        case "_":
                            board[-1][-1].walls |= Wall.SOUTH
                            
        # normalise the board walls
        for y,row in enumerate(board):
            for x,node in enumerate(row):
                match node.walls:
                    case Wall.WEST:
                        # if this node has a west wall, the node to the west must have an east wall
                        board[y][x-1].walls |= Wall.EAST
                        # remove the NONE flag from this node and its neighbour
                        board[y][x-1].walls |= ~Wall.NONE
                        board[y][x].walls |= ~Wall.NONE
                    case Wall.SOUTH:
                        # if this node has a south wall, the node to the south must have a north wall
                        board[y-1][x].walls |= Wall.NORTH
                        # remove the NONE flag from this node and its neighbour
                        board[y-1][x].walls |= ~Wall.NONE
                        board[y][x].walls |= ~Wall.NONE
        
                
        return cls(board)
    
    @classmethod
    def standard_board(cls) -> "Board":
        """Returns a board that is in standard starting positions.
        """
        standard_board_str = "\n".join([
            "rnbqkbnr", # black pieces
            "pppppppp",
            "........",
            "........",
            "........",
            "........",
            "PPPPPPPP",
            "RNBQKBNR", # white pieces
        ])
        return cls.from_str(standard_board_str)
    
    
    def apply_move(self, move: Move) -> "Board":
        """Applies the given move to the board, returning a new board and leaving the original unchanged.
        """
        raise NotImplementedError
