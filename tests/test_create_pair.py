"""
Tests for :py:class:`fifoio.create_pair`
"""


import asyncio
from io import BufferedReader
from io import BufferedWriter
from typing import IO
from typing import Callable
from unittest import TestCase

import pytest

from fifoio import ONE_MEGABYTE
from fifoio import create_pair


async def run_in_thread(func: Callable, *args) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, func, *args)


class TestSendLargeFile(TestCase):
    """have a producer that sends a large file and a consumer that reads it"""

    @pytest.mark.asyncio
    def test_send_large_file(self):
        writer, reader = create_pair(size=ONE_MEGABYTE)
        reader = BufferedReader(reader)
        writer = BufferedWriter(writer)

        def producer(stream: IO) -> None:
            for number in range(1_000_000):
                line = "{}\n".format(number)
                stream.write(line.encode("utf-8"))
            stream.close()

        def consumer(case: TestCase, stream: IO) -> None:
            expected = 0
            for line in stream:
                result = int(line.decode().strip())
                case.assertEqual(result, expected)
                expected += 1

            self.assertEqual(expected, 1_000_000)

        async def main() -> None:
            task1 = asyncio.create_task(run_in_thread(producer, writer))
            task2 = asyncio.create_task(run_in_thread(consumer, self, reader))
            await asyncio.gather(task1, task2)

        asyncio.run(main())
