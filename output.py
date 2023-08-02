import stdio


class Error:
    """Error messages as an enum."""

    ILLEGAL_MOVE = "illegal move at %s"
    """Move %s is illegal"""
    ILLEGAL_BOARD = "illegal board at %s"
    """Board is illegal at %s"""
    ILLEGAL_STATUSLINE = "illegal board at statusline"
    """Illegal statusline"""


class Info:
    """Informational messages as an enum."""

    CHECK = "check"
    """Player in check"""
    CHECKMATE = "checkmate"
    """Player checkmated"""
    STALEMATE = "stalemate"
    """Game at stalemate"""
    DRAW_FIFTY = "draw due to fifty moves"
    """Game drawn due to fifty-move rule"""
    DRAW_THREEFOLD = "draw due to threefold repetition"
    """Game drawn due to threefold-repetition"""


def print_error(error: str, param: str | None = None):
    """Prints an error message to the console

    The param value is only used if the error message has a valid format string

    Parameters
    ----------
    error : str
        The error message to print
    param : str | None, optional
        The parameter to the error message, by default None
    """
    stdio.writeln(f"ERROR: {error%param if param and '%' in error else error}")


def print_info(info: str):
    """Prints an informational message to the console

    Parameters
    ----------
    info : str
        The info message to print
    """
    stdio.writeln(f"INFO: {info}")
