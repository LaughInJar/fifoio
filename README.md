# fifoio
Write &amp; Read to the same buffer (memoryview) with to streams that track their separate positions

Is is performant? No. It's in pure python (as opposed to C) and uses locks so that read & write operations do not
conflict with each other.

Example:
```python
import asyncio
from io import BufferedReader
from io import BufferedWriter
from typing import IO
from typing import Callable

from fifoio import ONE_MEGABYTE
from fifoio import create_pair


async def run_in_thread(func: Callable, *args) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, func, *args)

def producer(stream: IO) -> None:
    for number in range(1_000_000):
        line = "{}\n".format(number)
        stream.write(line.encode("utf-8"))
    stream.close()

def consumer(stream: IO) -> None:
    expected = 0
    for line in stream:
        result = int(line.decode().strip())
        assert expected == result
        expected += 1
    assert expected == 1_000_000
    print("All ok!")


async def main() -> None:
    writer, reader = create_pair(size=ONE_MEGABYTE)
    reader = BufferedReader(reader)
    writer = BufferedWriter(writer)

    task1 = asyncio.create_task(run_in_thread(producer, writer))
    task2 = asyncio.create_task(run_in_thread(consumer, reader))
    await asyncio.gather(task1, task2)

asyncio.run(main())
```