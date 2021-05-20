import asyncio
import datetime
from functools import wraps
from functools import partial
import threading
from uuid import uuid4
import abc
from time import sleep
from pathlib import Path

from typing import Optional
from typing import Union



import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from logger import logger


def _build_repr(func, *a, **kw):
    name = getattr(func, "__qualname__", getattr(func, "__name__", str(func)))

    if a:
        args = ", ".join(str(arg) for arg in a)
        if kw:
            args += ", "
    else:
        args = ""
    if kw:
        kwargs = ", ".join(f"{k}={v}" for k, v in kw.items())
    else:
        kwargs = ""
    return name, f"{name}({args}{kwargs})"


def traced(logging_function):
    def factory(func):
        @wraps(func)
        def wrapper(*a, **kw):
            uuid = str(uuid4())
            name, repred = _build_repr(func, *a, **kw)
            logging_function(f"{'CALL':<8} [{uuid}]: {repred}")
            try:
                ret = func(*a, **kw)
            except Exception as exc:
                logger.error(
                    f"{'ERROR':<8} [{uuid}]: {name} - {type(exc).__name__} ({exc})"
                )
                raise
            logging_function(f"{'RETURN':<8} [{uuid}]: {name}")
            logging_function(str(ret))
            return ret

        return wrapper

    return factory


def traced_async(logging_function):
    def traced_async_factory(func):
        @wraps(func)
        async def wrapper(*a, **kw):
            uuid = str(uuid4())
            name, repred = _build_repr(func, *a, **kw)
            logging_function(f"{'CALL':<8} [{uuid}]: {_build_repr(func, *a, **kw)}")
            try:
                ret = await func(*a, **kw)
            except Exception as exc:
                logger.error(
                    f"{'ERROR':<8} [{uuid}]: {name} - {type(exc).__name__} ({exc})"
                )
                raise
            logging_function(f"{'RETURN':<8} [{uuid}]: {name}")
            logging_function(str(ret))
            return ret

        return wrapper

    return traced_async_factory


def _to_dot(name, pipeline):
    name = name or str(datetime.datetime.now()).replace(":", "_")
    Gst.debug_bin_to_dot_file_with_ts(pipeline, Gst.DebugGraphDetails.ALL, name)


def dotted(func):

    name = getattr(func, "__qualname__", getattr(func, "__name__", str(func)))

    @wraps(func)
    def wrapper(self, *a, **kw):
        _to_dot(f"pre_{name}", self.pipeline)
        try:
            ret = func(self, *a, **kw)
        finally:
            _to_dot(f"post_{name}", self.pipeline)
        return ret

    return wrapper


def get_by_name_or_raise(gst_bin: Gst.Bin, name: str) -> Gst.Element:
    element = gst_bin.get_by_name(name)
    if element is None:
        raise NameError(f"{gst_bin} does not have a child element named '{name}'")
    return element


def _loop_in_thread(coro, loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro())


def start_asyncio_background(coro, loop):
    t = threading.Thread(
        target=_loop_in_thread,
        args=(
            coro,
            loop,
        ),
    )
    t.start()
    return t


class CancellableRunLater(threading.Thread, abc.ABC):
    """A `Thread` enabled for external stopping by attribute settings."""

    def __repr__(self):
        return f"<{type(self).__name__}({self.name})>"

    def __init__(
        self,
        callback: callable,
        delay: int = 0,
        name: Optional[str] = "CancellableRunLater",
        daemon: Optional[bool] = True,
    ) -> None:
        """Initialize a cancellable delayed thread.

        Args:
            callback: Callable to execute after delay.
            delay: Delay before running.
            name: Thread `name` kwarg.
            daemon: Thread  `daemon` kwarg.
        """
        super().__init__(group=None, target=None, name=name, daemon=daemon)
        self.callback = callback
        self.delay = delay

        self._cancelled = False
        self._output = None

    def cancel(self):
        if self._output:
            raise ValueError("Task already done!")
        self._cancelled = True

    def run(self):
        """Run skeleton - delay data and check external stop."""
        sleep(self.delay)
        if self._cancelled:
            logger.debug("Task Cancelled")
            return

        self._output = self.callback()
        return self._output


def run_later(cb, delay, *a, daemon=True, **kw) -> CancellableRunLater:
    runner = CancellableRunLater(
        partial(cb, *a, **kw),
        delay,
        daemon=daemon,
    )
    runner.start()
    return runner


def pipe_from_file(
    path: Union[str, Path],
    **pipeline_kwargs
) -> str:
    logger.info(f"Loading pipeline from {path}")

    real = Path(path).resolve()
    with open(real) as fp:
        pipeline_string = fp.read()
    lines = []
    for line in pipeline_string.split("\n"):
        raw = line.strip()
        content = raw.split("#", 1)[0]
        if content.strip():
            lines.append(content)
    pipeline_string = "\n".join(lines)
    try:
        formatted_pipeline = pipeline_string.format_map(pipeline_kwargs)
    except KeyError as exc:
        logger.error(f"PythiaGsApp: Cannot run {real}. Reason: {repr(exc)}")
        raise

    return formatted_pipeline
