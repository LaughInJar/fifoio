"""
Tests for :py:class:`fifoio.SharedBuffer`
"""
import asyncio
from typing import Callable
from unittest import TestCase

import pytest

from fifoio import SharedBuffer


async def run_in_thread(func: Callable, *args) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, func, *args)


class IndicateEofTestCase(TestCase):
    """Tests for :py:meth:`fifoio.SharedBuffer.indicate_eof`"""

    def test_indicate_eof_flips_flag(self):
        """test if :py:meth:`fifoio.SharedBuffer.indicate_eof` flips the eof flag"""
        buffer = SharedBuffer(buffer_size=100)
        self.assertFalse(buffer.eof)
        buffer.inidicate_eof()
        self.assertTrue(buffer.eof)

    @pytest.mark.asyncio
    def test_indicate_eof_notifies_empty(self):
        """test if :py:meth:`fifoio.SharedBuffer.indicate_eof` actually notifies potentially waiting readers"""
        buffer = SharedBuffer(buffer_size=100)
        waiting = []

        def wait_for_notify(waiting: list) -> None:
            """"""
            with buffer._empty:
                if buffer._empty.wait(timeout=1):
                    waiting.append("done")
                else:
                    waiting.append("timeout")

        async def main() -> None:
            task1 = asyncio.create_task(run_in_thread(wait_for_notify, waiting))
            task2 = asyncio.create_task(run_in_thread(buffer.inidicate_eof))
            await asyncio.gather(task1, task2)

        asyncio.run(main())
        self.assertEqual(waiting[0], "done")


class BytesFreeTestCase(TestCase):
    """Tests for :py:meth:`fifoio.SharedBuffer.bytes_free`"""

    def test_buffer_fresh(self):
        """tests that we have the full buffer available for a fresh object"""

        buffer = SharedBuffer(buffer_size=100)
        self.assertEqual(buffer.bytes_free(), 100)

    def test_buffer_writtento(self):
        """tests that we have the full buffer - no bytes written to it"""

        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b"1" * 10)
        self.assertEqual(buffer.bytes_free(), 90)

    def test_buffer_full(self):
        """tests that we have the buffer if full after filling it"""

        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b"1" * 100)
        self.assertEqual(buffer.bytes_free(), 0)

    def test_buffer_read(self):
        """tests that the number of free bytes increased after reading"""
        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b"1" * 100)
        buffer.readinto(bytearray(10))
        self.assertEqual(buffer.bytes_free(), 10)


class AvailabilityTestCase(TestCase):
    """Tests for :py:meth:`fifoio.SharedBuffer.available`"""

    def test_initial_availability(self):
        """test that initially we have no bytes ready for reading"""
        buffer = SharedBuffer(buffer_size=100)
        self.assertEqual(buffer.available(), 0)

    def test_after_write(self):
        """after writeing we should have more bytes to read"""
        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b"0" * 60)
        self.assertEqual(buffer.available(), 60)
        buffer.write(b"0" * 10)
        self.assertEqual(buffer.available(), 70)

    def test_after_read(self):
        """after a read there should be fewer bytes to"""
        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b"0" * 60)
        self.assertEqual(buffer.available(), 60)
        buffer.readinto(bytearray(20))
        self.assertEqual(buffer.available(), 40)


class WriteTestCase(TestCase):
    """Tests for :py:meth:`fifoio.SharedBuffer.write`"""

    def test_read_write(self):
        """test that we can read what was written"""
        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b"abc")
        result = bytearray(3)
        buffer.readinto(result)
        self.assertEqual(b"abc", result)

    def test_read_write_circular(self):
        """test subsequent read an writes greater than the buffer size"""
        buffer = SharedBuffer(buffer_size=15)
        buffer.write(b"0123456789")
        buffer.readinto(bytearray(10))
        buffer.write(b"0123456789")
        buffer.readinto(bytearray(10))
        buffer.write(b"0123456789")
        result = bytearray(10)
        buffer.readinto(result)
        self.assertEqual(b"0123456789", result)

    @pytest.mark.asyncio
    def test_block_on_full(self):
        """test that it blocks when the buffer is full"""
        buffer = SharedBuffer(buffer_size=10)
        buffer.write(b"0123456789")
        self.assertEqual(buffer.bytes_free(), 0)
        history = []

        def write_blocked() -> None:
            """write to full buffer"""
            history.append("before write")
            buffer.write(b"abc")
            history.append("after write")

        def read() -> None:
            """read from buffer"""
            history.append("before read")
            buffer.readinto(bytearray(10))
            history.append("read done")

        async def main() -> None:
            write_task = asyncio.create_task(run_in_thread(write_blocked))
            await asyncio.sleep(0.1)
            read_task = asyncio.create_task(run_in_thread(read))
            await asyncio.gather(write_task, read_task)

        asyncio.run(main())
        self.assertListEqual(
            history,
            [
                "before write",
                "before read",
                "read done",
                "after write",
            ],
        )

    @pytest.mark.asyncio
    def test_notify_empty(self):
        """test that the empty condition is notified after a write"""
        buffer = SharedBuffer(buffer_size=100)
        waiting = []

        def wait_for_notify(waiting: list) -> None:
            """"""
            with buffer._empty:
                if buffer._empty.wait(timeout=1):
                    waiting.append("done")
                else:
                    waiting.append("timeout")

        async def main() -> None:
            task1 = asyncio.create_task(run_in_thread(wait_for_notify, waiting))
            task2 = asyncio.create_task(run_in_thread(buffer.write, b"abc"))
            await asyncio.gather(task1, task2)

        asyncio.run(main())
        self.assertEqual(waiting[0], "done")


class ReadIntoTestCase(TestCase):
    """Tests for :py:meth:`fifoio.SharedBuffer.read`"""

    #: copy the tests from the write test case.. not nice
    test_read_write = WriteTestCase.test_read_write

    #: copy the tests from the write test case.. not nice
    test_read_write_circular = WriteTestCase.test_read_write_circular

    @pytest.mark.asyncio
    def test_block_on_empty(self):
        """test that it blocks when the buffer is full"""
        buffer = SharedBuffer(buffer_size=10)
        self.assertEqual(buffer.available(), 0)
        history = []

        def read_blocked() -> None:
            """write to full buffer"""
            history.append("before read")
            buffer.readinto(bytearray(3))
            history.append("after read")

        def write() -> None:
            """read from buffer"""
            history.append("before write")
            buffer.write(b"abc")
            history.append("write done")

        async def main() -> None:
            read_task = asyncio.create_task(run_in_thread(read_blocked))
            await asyncio.sleep(0.1)
            write_task = asyncio.create_task(run_in_thread(write))
            await asyncio.gather(read_task, write_task)

        asyncio.run(main())
        self.assertListEqual(
            history,
            [
                "before read",
                "before write",
                "write done",
                "after read",
            ],
        )

    @pytest.mark.asyncio
    def test_notify_full(self):
        """test that the empty condition is notified after a write"""
        buffer = SharedBuffer(buffer_size=3)
        buffer.write(b"abc")
        waiting = []

        def wait_for_notify(waiting: list) -> None:
            """"""
            with buffer._full:
                if buffer._full.wait(timeout=1):
                    waiting.append("done")
                else:
                    waiting.append("timeout")

        async def main() -> None:
            task1 = asyncio.create_task(run_in_thread(wait_for_notify, waiting))
            task2 = asyncio.create_task(run_in_thread(buffer.readinto, bytearray(3)))
            await asyncio.gather(task1, task2)

        asyncio.run(main())
        self.assertEqual(waiting[0], "done")
