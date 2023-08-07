from typing import Iterator
from common import Result
from move import Move
import socket
from common import *

class RemoteConnection:
    def __init__(self, remote_ip:str,  master: bool, port:int = 5000) -> None:
        # initialize the socket the recieving socket
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.recv_sock.bind((socket.gethostname(), port))

        if not master:
            # wait for the master to connect
            self.recv_sock.accept()
            if self.recv_sock.recv(1024) != b"connect":
                raise RuntimeError("Master did not send connect message")
            
        # initialize the sending socket
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # the master sends to port 1501, the slave sends to port 1500
        self.send_sock.connect((remote_ip, port))
        
        if master:
            # send the connect message to the slave
            self.send_sock.sendall(b"connect")
    
    @classmethod
    def search(cls, quick_connect = False) -> Result[tuple[str, int] | None]:
        """Open up to search requests, and multicast a search request to the group to discover other players.
        
        The multicast will repeat every 5 seconds until a response is recieved, or until there have been 12 attempts (i.e. max one minute of searching), or until user enters Ctrl+C.
        
        Upon reciving a multicast, the player will respond with a unicast to the sender of the multicast.
        
        The multicaster will be the master, and the responder will be the slave.
        
        Returns Failure if no response is recieved, or if the user enters Ctrl+C.
        
        Returns Success with the address of the responder if a response is recieved, or None if this player is the slave.
        """
        # Initialize the multicast sending socket
        multi_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        multi_out.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        multi_out.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            raise NotImplementedError
        except KeyboardInterrupt: # On Ctrl+C, close the socket and exit
            return Failure("User cancelled search")
    
    @property
    def recv_addr(self) -> tuple[str, int]:
        return self.recv_sock.getsockname()
    
    @property
    def send_addr(self) -> tuple[str, int]:
        return self.send_sock.getsockname()
    
    @property
    def remote_addr(self) -> tuple[str, int]:
        return self.send_sock.getpeername()
    
    @property
    def local_hostname(self) -> str:
        return socket.gethostname()
    
    def close(self) -> None:
        self.recv_sock.close()
        self.send_sock.close()
        
    def __del__(self) -> None:
        self.close()
        del self.recv_sock
        del self.send_sock
        
    def send(self, msg:str) -> None:
        raise NotImplementedError
        
    def recv(self) -> str:
        raise NotImplementedError

class MoveSource:
    """A base class for all move sources.
    
    A different one can be used for each player, allowing for different move sources for each player.
    
    i.e.) One player could be a human, while the other is an AI, or one player could be local, while the other is a remote player.
    """
    def __init__(self, player:int, moves: list[Move]) -> None:
        self.player = player
        self.moves = iter(moves)
        self.__closed = False
        
    def close(self) -> None:
        self.__closed = True
    
    def __iter__(self) -> Iterator[Result[Move]]:
        while not self.__closed:
            yield Success(next(self.moves))
        
class HumanMoveSource(MoveSource):
    def __init__(self, player: int) -> None:
        super().__init__(player, [])
        
    def __iter__(self) -> Iterator[Result[Move]]:
        while not self.__closed:
            yield Move.from_str(self.player, input())
            
class AIMoveSource(MoveSource):
    def __init__(self, player: int) -> None:
        super().__init__(player, [])
        
    def __iter__(self) -> Iterator[Result[Move]]:
        raise NotImplementedError
    
class RemoteMoveSource(MoveSource):
    def __init__(self, player: int, connection:RemoteConnection) -> None:
        super().__init__(player, [])
        self.connection = connection
        
    def __iter__(self) -> Iterator[Result[Move]]:
        while not self.__closed:
            move_str = self.connection.recv()
            yield Move.from_str(self.player, move_str)

class MoveGenerator:
    """A base class for all move generators.
    
    Implements the iterator protocol, allowing for iteration over all moves.
    """
    def __init__(self, white:MoveSource, black:MoveSource) -> None:
        self.white_source = white
        self.black_source = black
    #TODO: Implement iterator protocol
    
if __name__ == '__main__':
    search_result: Result[tuple[str, int]|None] = RemoteConnection.search()
    if isinstance(search_result, Failure):
        print("No other players found, starting local game")
    elif isinstance(search_result, Success):
        search_target: tuple[str, int] | None = search_result.unwrap()
        if search_target is None:
            conn = RemoteConnection("", False)
        elif isinstance(search_target, tuple):
            conn = RemoteConnection(remote_ip=search_target[0], port=search_target[1], master=True)