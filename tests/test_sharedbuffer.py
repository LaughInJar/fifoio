"""
Tests for :py:class:`fifoio.SharedBuffer`
"""
import asyncio
from unittest import TestCase

import pytest

from fifio import SharedBuffer


class IndicateEofTestCase(TestCase):
    """Tests for :py:class:`fifoio.SharedBuffer`"""

    def test_indicate_eof_flips_flag(self):
        """test if :py:meth:`fifoio.SharedBuffer.indicate_eof` flips the eof flag"""
        buffer = SharedBuffer(buffer_size=100)
        self.assertFalse(buffer.eof)
        buffer.inidicate_eof()
        self.assertTrue(buffer.eof)

    @pytest.mark.asyncio
    def test_indicate_eof_notifes_empty(self):
        """test if :py:meth:`fifoio.SharedBuffer.indicate_eof` actually notifies potentially waiting readers"""
        buffer = SharedBuffer(buffer_size=100)
        waiting = []

        def wait_for_notify(waiting):
            """"""
            with buffer._empty:
                if buffer._empty.wait(timeout=1):
                    waiting.append("done")
                else:
                    waiting.append("timeout")

        async def run_in_thread(func, *args):
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, func, *args)

        async def main():
            task1 = asyncio.create_task(run_in_thread(wait_for_notify, waiting))
            task2 = asyncio.create_task(run_in_thread(buffer.inidicate_eof))
            await asyncio.gather(task1, task2)

        asyncio.run(main())
        self.assertEqual(waiting[0], "done")
