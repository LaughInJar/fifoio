"""

"""
from array import array
from io import RawIOBase
from mmap import mmap
from threading import Condition
from threading import Lock
from typing import Union

__author__ = "Simon Lachinger"
__copyright__ = "Copyright 2021, Simon Lachinger"
__credits__ = ["Simon Lachinger"]
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Simon Lachinger"
__email__ = "simon"
__status__ = "Alpha"


ONE_KILOBYTE = 1024
ONE_MEGABYTE = 1024 * ONE_KILOBYTE


class SharedBuffer:
    """A shared buffer used by the read & write stream pair created by :py:meth:`create_pair`"""

    def __init__(self, buffer_size=ONE_MEGABYTE):
        """
        :param buffer_size: the size of the circular buffer in bytes
        """
        self._buffer = memoryview(bytearray(buffer_size))
        self.buffer_size = buffer_size
        self.write_pos = 0
        self.read_pos = 0
        self._lock = Lock()
        self._full = Condition()
        self._empty = Condition()
        self.eof = False

    def inidicate_eof(self):
        """The if the writeable stream is closed it will use this method to indicate that no more bytes are
        incoming.
        """
        self.eof = True
        with self._empty:
            self._empty.notify()

    def bytes_free(self) -> int:
        """free bytes in the buffer"""
        used = self.write_pos - self.read_pos
        return self.buffer_size - used

    def available(self):
        """bytes available for reading"""
        return self.write_pos - self.read_pos

    def write(self, b: Union[bytes, bytearray, memoryview, array, mmap]) -> int:
        """override the method from :py:class:`io.RawIOBase`

        :param b: a bytes like object to write to the stream

        It will acquire a lock and then check the number of free bytes in the (circular) buffer.

        #. if there are free bytes, write min(free bytes, length of `b`) to the stream, return the number of written
           bytes

        #. if there are no free bytes in the buffer, wait until bytes were read from the paired reader stream

        #. notify the a potentially waiting reader that bytes are available
        """
        length = 0

        # for all buffer manipulations, lock
        with self._lock:
            free = self.bytes_free()
            if free > 0:
                # how many bytes are we going to write
                length = min(free, len(b))

                # where are we in the circular buffer
                buffer_pos = self.write_pos % self.buffer_size

                # how many bytes are left until circular buffer overrun
                bytes_until_overrun = min(length, self.buffer_size - buffer_pos)

                # write bytes until the overrun
                self._buffer[buffer_pos : buffer_pos + bytes_until_overrun] = b[
                    :bytes_until_overrun
                ]

                # if we have more bytes to write, start from the beginning
                bytes_from_start = length - bytes_until_overrun
                if bytes_from_start:
                    self._buffer[0:bytes_from_start] = b[bytes_until_overrun:length]

                self.write_pos += length

        if free == 0:
            # the buffer is full, wait until a read operation has happened
            with self._full:
                self._full.wait()
                return self.write(b)
        elif length > 0:
            # we wrote something to the buffer, notify waiting readers
            with self._empty:
                self._empty.notify()

        return length

    def readinto(self, b: Union[bytearray, memoryview, array, mmap]) -> int:
        """override the method from :py:class:`io.RawIOBase`

        :param b: the bytearray (or memoryview, ...) object to read into


        At first, it will acquire a lock an then check the number of available bytes to read

        #. if there are bytes available read min(len(b), available bytes) into the buffer

        #. if there are no bytes available, wait for a write event an try again

        #. notify potentially waiting writer that some bytes were read
        """
        length = 0

        # for all buffer manipulation, lock
        with self._lock:
            available = self.available()
            if available > 0:
                # how many bytes are we going to read
                length = min(len(b), available)

                # where are we in the circular buffer
                buffer_pos = self.read_pos % self.buffer_size

                # how many bytes are left until circular buffer overrun
                bytes_until_overrun = min(length, self.buffer_size - buffer_pos)

                # read bytes until the overrun
                b[0:bytes_until_overrun] = self._buffer[
                    buffer_pos : buffer_pos + bytes_until_overrun
                ]

                # if we have more bytes to read, start from the beginning
                bytes_from_start = length - bytes_until_overrun
                if bytes_from_start:
                    b[bytes_until_overrun:length] = self._buffer[0:bytes_from_start]

                self.read_pos += length

        if available == 0:
            # input stream closed?
            if self.eof:
                return 0
            # the buffer is empty, wait until a write op happens
            with self._empty:
                self._empty.wait()
                return self.readinto(b)
        elif length > 0:
            # notify pending write ops that we'Ve got space again
            with self._full:
                self._full.notify()
        return length


class Writeable(RawIOBase):
    def __init__(self, buffer: SharedBuffer):
        """

        :param buffer:
        """
        self.buffer = buffer

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def write(self, b: Union[bytes, bytearray, memoryview, array, mmap]) -> int:
        return self.buffer.write(b)

    def close(self):
        self.buffer.inidicate_eof()
        super().close()


class Readable(RawIOBase):
    def __init__(self, buffer: SharedBuffer):
        """

        :param buffer:
        """
        self.buffer = buffer

    def writable(self):
        return True

    def readable(self):
        return False

    def seekable(self):
        return False

    def readinto(self, b: Union[bytearray, memoryview, array, mmap]) -> int:
        return self.buffer.readinto(b)


def create_pair(size=ONE_MEGABYTE):
    """

    :param size:
    :return:
    """
    buffer = SharedBuffer(buffer_size=size)
    return Writeable(buffer), Readable(buffer)
