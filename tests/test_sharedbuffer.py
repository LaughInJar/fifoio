"""
Tests for :py:class:`fifoio.SharedBuffer`
"""
import asyncio
from typing import Callable
from unittest import TestCase

import pytest

from fifoio import SharedBuffer


class IndicateEofTestCase(TestCase):
    """Tests for :py:class:`fifoio.SharedBuffer.indicate_eof`"""

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

        async def run_in_thread(func: Callable, *args) -> None:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, func, *args)

        async def main() -> None:
            task1 = asyncio.create_task(run_in_thread(wait_for_notify, waiting))
            task2 = asyncio.create_task(run_in_thread(buffer.inidicate_eof))
            await asyncio.gather(task1, task2)

        asyncio.run(main())
        self.assertEqual(waiting[0], "done")


class BytesFreeTestCase(TestCase):
    """Tests for :py:class:`fifoio.SharedBuffer.bytes_free`"""

    def test_buffer_fresh(self):
        """tests that we have the full buffer available for a fresh object"""

        buffer = SharedBuffer(buffer_size=100)
        self.assertEqual(buffer.bytes_free(), 100)

    def test_buffer_writtento(self):
        """tests that we have the full buffer - no bytes written to it"""

        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b'1' * 10)
        self.assertEqual(buffer.bytes_free(), 90)

    def test_buffer_full(self):
        """tests that we have the buffer if full after filling it"""

        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b'1' * 100)
        self.assertEqual(buffer.bytes_free(), 0)

    def test_buffer_read(self):
        """tests that the number of free bytes increased after reading"""
        buffer = SharedBuffer(buffer_size=100)
        buffer.write(b'1' * 100)
        buffer.readinto(bytearray(10))
        self.assertEqual(buffer.bytes_free(), 10)

