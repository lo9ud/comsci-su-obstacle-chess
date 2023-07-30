import re
from logger import Logger, StdOut, Errors, Infos
from typing import TextIO
from piece import Piece, Position


logger = Logger(StdOut())


class BoardNode:
    def __init__(self, contents, modifiers) -> None:
        self.contents = contents
        self.walls = {
            'n': False,
            's': False,
            'e': False,
            'w': False
        }
        for mod in modifiers:
            match mod:
                case "d":
                    self.trapdoor = "hidden"
                case "o":
                    self.trapdoor = "open"
                case "m":
                    self.mined = True
                # TODO: set other BoardNodes wall states
                case "|":
                    self.walls['w'] = True
                case "_":
                    self.walls['s'] = True

                case ".":
                    continue
                case _:
                    raise ValueError(f"Invalid modifier {mod}!")

    def swap(self, other: "BoardNode") -> None:
        self.contents, other.contents = other.contents, self.contents


class Board:
    def __init__(self, board_array: list[list[BoardNode]]) -> None:
        self.board_array = board_array

    def __getitem__(self, position: Position | tuple[int, int]) -> BoardNode:
        if isinstance(position, Position):
            position = position.position
        return self.board_array[position[0]][position[1]]

    def __setitem__(self, position: Position | tuple[int, int], value: BoardNode) -> None:
        if isinstance(position, Position):
            position = position.position
        self.board_array[position[0]][position[1]] = value

    def apply_file(self, file: TextIO):
        raise NotImplementedError

    @classmethod
    def from_file(cls, file: TextIO) -> "Board":
        board_array = []
        lines_read = 0
        for line in file.readlines():
            if re.match(r"\s*%", line):
                # Comment line
                continue

            # Valid line
            lines_read += 1

            # Too many lines
            if lines_read > 9:
                break

            # Status line
            if lines_read > 8:
                status_regex = re.compile(
                    # white vs black
                    r"(w|b)\s"
                    # white remainig walls
                    + r"\d\s"
                    # black remaining walls
                    + r"\d\s"
                    # castling rights
                    + r"((\+|-)\s){4}"
                    # en-pasant target
                    + r"(-|(\w\d))\s"
                    # halfmoves
                    + r"\d+"
                )  # matches structurally-correct status lines

                match = status_regex.match(line)
                if match:
                    raise NotImplementedError
                else:
                    logger.error(Errors.illegal_status)

            # Board line
            board_line = []

            # the current modifiers for the board node
            mod_stack = []
            for col, char in enumerate(line):
                if char == "\n":
                    continue

                match char.lower():
                    # Empty blocks
                    case "." | "o" | "d" | "m":
                        board_line.append(BoardNode(None, mod_stack + [char]))
                        mod_stack = []

                    # special case to expand x into d,m
                    case "x":
                        board_line.append(
                            BoardNode(None, mod_stack + ['m', 'd']))
                        mod_stack = []

                    # A piece
                    case "p" | "r" | "b" | "q" | "k" | "n":
                        board_line.append(BoardNode(Piece(char), mod_stack))
                        mod_stack = []

                    # A piece modifier
                    case "x" | "-" | "|":
                        mod_stack.append(char)

                    # Invalid descriptor
                    case _:
                        logger.error(Errors.illegal_board, str(
                            Position((col, lines_read))))
            board_array.append(board_line)
        return cls(board_array)
