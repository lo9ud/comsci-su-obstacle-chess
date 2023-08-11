"""A module for handling moves.

Defines MoveGenerator, which yields moves from a file, socket, console or AI; and MoveSink, which recieves moves and processes them for output to a file, console, or GUI.
"""


from typing import Iterator, Generator, TextIO
from common import *
from move import Move
import socket
import time
import struct
from common import *


class RemoteConnection:
    host_recv_port = 50007
    slave_recv_port = 50008
    multicast_port = 5007
    multicast_group = "224.56.3.54"  # Effectively random, but in the multicast range

    def __init__(self, send_sock: socket.socket, recv_sock: socket.socket) -> None:
        self.send_sock = send_sock
        self.recv_sock = recv_sock
        # set the timeout (defaults to 2 minutes)
        self.set_recv_timeout(120)

    @classmethod
    def as_host(
        cls, friendly_name=socket.gethostname(), listen_timeout=120
    ) -> Result["RemoteConnection"]:
        """Open up to search requests, and multicast a search request to the group to discover other players.

        Upon recieving a search request, the host will send a unicast response to the sender, and at the end of the timeout, will return a RemoteConnection object to the first client to connect.

        listen_timeout: The number of seconds to listen for responses. If 0, will listen forever. This can be overridden by the user with Ctrl+C. Thsi has limited resolution, so may not be exact.
        """
        # Initialize mulitcast listener
        mcast_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )

        # reuse the address
        mcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # bind to the multicast port
        mcast_sock.bind(
            (RemoteConnection.multicast_group, RemoteConnection.multicast_port)
        )

        # add the socket to the multicast group
        mreq = struct.pack(
            "4sl", socket.inet_aton(
                RemoteConnection.multicast_group), socket.INADDR_ANY
        )
        mcast_sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # set the timeout
        mcast_sock.settimeout(5)

        # Initialize unicast response sender
        response_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # start the clock
        start_time = time.time()

        # the list of responses recieved
        client_responses = set()

        # while the timeout has not been reached, or the user has not ended the search
        while (time.time() - start_time > listen_timeout) or listen_timeout == 0:
            try:
                # recieve a multicast
                # msg should be the friendly name of the responder, and addr will be the address of the responder
                bytes_msg, (addr, port) = mcast_sock.recvfrom(1024)
                client_friendly_name = bytes_msg.decode()
            except (
                TimeoutError
            ):  # if the timeout expires, keep running (allows manual timeout via Ctrl+C)
                continue
            except (
                KeyboardInterrupt
            ):  # if the user enters Ctrl+C, break out of the loop
                break
            else:  # if a message is recieved, append it to the list of responses and send a unicast to the sender
                # check if the response is already in the list of responses
                if (client_friendly_name, addr, port) not in client_responses:
                    client_responses.add((client_friendly_name, addr, port))
                    # send a unicast response containing the remaining time, so the client can determine how long to wait before attempting to connect
                    response_sock.sendto(
                        bytes(
                            f"{friendly_name}:{listen_timeout - (time.time() - start_time)}",
                            "utf-8",
                        ),
                        (addr, port),
                    )
                    err_print(
                        f"Client discovered: {client_friendly_name}@{addr}:{port}"
                    )
        # User has ended the search, or timeout reached, so close the multicast socket
        mcast_sock.close()

        # wait for a client to connect
        recv_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recv_server.bind(("127.0.0.1", RemoteConnection.host_recv_port))
        recv_server.settimeout(60)
        err_print("Waiting for client connection...")
        client_addr = recv = None
        while not client_addr:
            try:
                recv, (client_addr, _) = recv_server.accept()
            except TimeoutError:
                err_print("Client connection timed out, exiting...")
                return Failure("Client selection timed out")
            # find the client in the list of responses
            for name, addr, port in client_responses:
                if addr == client_addr:
                    err_print(f"Client {name} connected")
                    break
            # if the client was not found, close the connection and wait for another client
            err_print("Unknown client connected, closing connection...")
            recv.close()
            client_addr = None

        # connect to the client
        send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send.connect((client_addr, RemoteConnection.slave_recv_port))

        # a client has connected, so close the server socket
        recv_server.close()

        # return the connection
        if recv and send:
            return Success(RemoteConnection(send, recv))
        else:
            return Failure("Client connection failed")

    @classmethod
    def as_slave(
        cls, friendly_name=socket.gethostname(), broadcast_timeout=120
    ) -> Result["RemoteConnection"]:
        """Attempt to connect to a host."""

        # initialize the multicast sender
        mcast_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )

        # set the socket TTL TODO: check how far it needs to be to reach the host experimentally
        mcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        # initialize the unicast listener
        response_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        response_sock.bind(("127.0.0.1", RemoteConnection.slave_recv_port))
        response_sock.settimeout(5)

        # start the clock
        start_time = time.time()

        hosts = set()
        # start the multicast
        while time.time() - start_time < broadcast_timeout:
            # send a multicast request
            mcast_sock.sendto(
                bytes(friendly_name, "utf-8"),
                (RemoteConnection.multicast_group,
                 RemoteConnection.multicast_port),
            )
            try:
                # recieve a unicast response
                msg, (addr, port) = response_sock.recvfrom(1024)
            except (
                TimeoutError
            ):  # if the timeout expires, keep running (allows manual timeout via Ctrl+C)
                continue
            except (
                KeyboardInterrupt
            ):  # if the user enters Ctrl+C, break out of the loop
                break
            else:  # if a message is recieved, append it to the list of responses
                match msg.decode().split(":"):
                    case [host_friendly_name, timeout]:
                        hosts.add((host_friendly_name, addr, port, timeout))
        # User has ended the search, or timeout reached, so close the multicast socket
        mcast_sock.close()

        # if no hosts were found, return a failure
        if not hosts:
            return Failure("No hosts found")

        # ask the user to select a host, or exit
        host_list = list(hosts)
        err_print("Select a host:")
        for i, (host_friendly_name, addr, port, timeout) in enumerate(host_list):
            err_print(f"   {i}-: {host_friendly_name}@{addr}:{port}")

        # get the user's selection
        selection = input(
            f"[{'/'.join([str(i+1) for i in range(len(host_list))] + ['q'])}]\n>>> "
        )

        # if user entered 'q', exit
        if selection.lower().strip() == "q":
            return Failure("User exited")

        # else, try to parse the selection as an integer
        try:
            selection = int(selection)
            if selection < 1 or selection > len(host_list):
                raise ValueError
        except ValueError:
            return Failure("Invalid selection")

        # extract the selected host
        name, addr, port, timeout = host_list[selection - 1]
        err_print(f"Selected host: {name}@{addr}:{port}\n Connecting...")

        # wait for the specified timeout
        time.sleep(float(timeout))

        # connect to the host
        err_print("Establishing TX connection...")
        send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send.connect((addr, RemoteConnection.host_recv_port))

        # wait for the host to connect
        err_print("Establishing RX connection...")
        recv_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recv_server.bind(("127.0.0.1", RemoteConnection.slave_recv_port))
        recv, addr = recv_server.accept()

        # close the server socket
        recv_server.close()

        # return the connection
        return Success(RemoteConnection(send, recv))

    def set_recv_timeout(self, timeout: float) -> None:
        self.recv_sock.settimeout(timeout)

    def close(self) -> None:
        self.recv_sock.close()
        self.send_sock.close()

    def __del__(self) -> None:
        self.close()
        del self.recv_sock
        del self.send_sock

    def send(self, msg: str) -> None:
        self.send_sock.sendall(bytes(msg, "utf-8"))

    def recv(self) -> str:
        return self.recv_sock.recv(1024).decode()


class MoveSource(Iterator[Result[Move]]):
    """A base class for all move sources.

    A different one can be used for each player, allowing for different move sources for each player.

    i.e.) One player could be a human, while the other is an AI, or one player could be local, while the other is a remote player.
    """

    def __init__(self, player: int) -> None:
        self.__source: Iterator[Move]
        self.player = player
        self.__closed = False

    def close(self) -> None:
        self.__closed = True

    def __iter__(self) -> Iterator[Result[Move]]:
        return self

    def __next__(self) -> Result[Move]:
        return Success(next(self.__source))

    def __enter__(self) -> Generator[Result[Move], None, None]:
        return iter(self)  # TODO: fix this

    def __exit__(self, type, value, traceback) -> bool:
        match type:  # match the type of exception
            case None:  # if no exception was raised, close the source
                self.close()
                return True
            case _:  # if an exception was raised, close the source and reraise the exception
                self.close()
                raise value


class ConsoleMoveSource(MoveSource):
    def __init__(self, player: int) -> None:
        super().__init__(player)

    def __iter__(self) -> Iterator[Result[Move]]:
        while not self.__closed:
            yield Move.from_str(self.player, input())


class AIMoveSource(MoveSource):
    def __init__(self, player: int) -> None:
        super().__init__(player)

    def __iter__(self) -> Iterator[Result[Move]]:
        raise NotImplementedError


class RemoteMoveSource(MoveSource):
    def __init__(self, player: int, connection: RemoteConnection) -> None:
        super().__init__(player)
        self.connection = connection

    def __iter__(self) -> Iterator[Result[Move]]:
        while not self.__closed:
            move_str = self.connection.recv()
            yield Move.from_str(self.player, move_str)


class MoveGenerator:
    """A base class for all move generators.

    Contains two MoveSources, one for each player.

    Implements the iterator protocol, allowing for iteration over all moves.
    """

    def __init__(self, white: MoveSource, black: MoveSource) -> None:
        self.white_source = white
        self.black_source = black
        self.__closed = False

    # TODO: Implement iterator protocol

    def close(self) -> None:
        self.__closed = True

    def __iter__(self) -> Iterator[Result[Move]]:
        with self.white_source as white_iter, self.black_source as black_iter:
            while not self.__closed:
                yield next(white_iter)
                yield next(black_iter)


class MoveSink:
    """A base class for all move sinks.

    Moves are sent to the sink using the send method, and handled internally.

    For example, a ConsoleMoveSink would err_print the move to the console, or a RemoteMoveSink would send the move to the remote player.
    """

    def __init__(self) -> None:
        pass

    def send(self, move: Move) -> None:
        """Takes a move and sends it to the sink.

        Parameters
        ----------
        move : Move
            The move to send
        """
        raise NotImplementedError

    def dump(self) -> None:
        """Performs any cleanup operations necessary to close the sink."""
        pass


class ConsoleMoveSink(MoveSink):
    def __init__(self) -> None:
        super().__init__()

    def send(self, move: Move) -> None:
        err_print(move.canonical())


class RemoteMoveSink(MoveSink):
    def __init__(self, conn: RemoteConnection) -> None:
        super().__init__()
        self.conn = conn

    def send(self, move: Move) -> None:
        self.conn.send(move.canonical())

    def dump(self) -> None:
        self.conn.close()

    def __del__(self):
        self.conn.close()


class GraphicMoveSink(MoveSink):  # TODO implement this
    def __init__(self, player: int) -> None:
        raise NotImplementedError

    def send(self, move: Move) -> None:
        raise NotImplementedError


class FileMoveSink(MoveSink):
    def __init__(self, file: str | TextIO) -> None:
        super().__init__()
        if isinstance(file, str):
            file = open(file, "w")
        self.file = file
        self.__tmp = ""

    def send(self, move: Move) -> None:
        self.__tmp += f"{move.canonical()}\n"

    def dump(self) -> None:
        self.file.write(self.__tmp)

    def __del__(self):
        self.file.close()
