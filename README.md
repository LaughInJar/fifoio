# fifoio
Write &amp; Read to the same buffer (memoryview) with to streams that track their separate positions

Is is performant? Somewhat. It's in pure python (as opposed to C) and uses locks so that read & write operations do not
conflict with each other. But in a test using httpx's streaming requests and a /dev/null target it was somehow faster
then `wget`.

## Usage

use the `create_pair()` method to get two streams, one to write into, one to read from.

```python
from fifoio import create_pair

writeable, readable = create_pair()
writeable.write(b"abc")
result = bytearray(3)
readable.readinto(result)
assert result, b"abc"

writeable.close()
readable.close()

```

Note, that it implements the `write` protocol of `io.RawIOBase`. This means that if not all bytes could be written due
to the underlying buffer being close to being full, it will try to write the maximum number of bytes and will return
the number of bytes being written. YOu must then try again with the remaining bytes. If you do not want to bother with
this, just wrap it in a `io.BufferedWritter`.

Also note that writing and reading are blocking if the underlying buffer is full or empty. 

## Example:
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