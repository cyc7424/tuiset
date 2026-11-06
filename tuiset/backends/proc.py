import asyncio
from asyncio.subprocess import DEVNULL, PIPE


async def run(*cmd: str, timeout: float = 10.0, input: str | None = None) -> tuple[int, str, str]:
    """Run a command without blocking the UI; returns (returncode, stdout, stderr).

    `input` goes to stdin, which keeps secrets out of the process list.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdin=DEVNULL if input is None else PIPE, stdout=PIPE, stderr=PIPE
        )
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: command not found"
    try:
        out, err = await asyncio.wait_for(proc.communicate(None if input is None else input.encode()), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "", f"{cmd[0]}: timed out"
    return proc.returncode or 0, out.decode(errors="replace"), err.decode(errors="replace")
