import asyncio
import datetime
from functools import wraps
import threading
from uuid import uuid4

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

def _build_repr(func, *a, **kw):
    name = getattr(func, "__qualname__", getattr(func, "__name__", str(func)))
    
    if a:
        args = ", ".join(str(arg) for arg in a)
        if kw:
            args += ", "
    else:
        args=""
    if kw:
        kwargs = ", ".join(f"{k}={v}" for k,v in kw.items())
    else:
        kwargs=""
    return name, f"{name}({args}{kwargs})"


def traced(func):

    @wraps(func)
    def wrapper(*a, **kw):
        uuid = str(uuid4())
        name, repred = _build_repr(func, *a, **kw)        
        print(f"{'CALL':<8} [{uuid}]: {repred}")
        try:
            ret = func(*a, **kw)
        except Exception as exc:
            print(f"{'ERROR':<8} [{uuid}]: {name} - {type(exc).__name__} ({exc})")
            raise
        print(f"{'RETURN':<8} [{uuid}]: {name}", end="")
        print("\n         " + str(ret).replace("\n", "\n         "))
        return ret
    return wrapper


def traced_async(func):
    @wraps(func)
    async def wrapper(*a, **kw):
        uuid = str(uuid4())
        name, repred = _build_repr(func, *a, **kw)
        print(f"{'CALL':<8} [{uuid}]: {_build_repr(func, *a, **kw)}")
        try:
            ret = await func(*a, **kw)
        except Exception as exc:
            print(f"{'ERROR':<8} [{uuid}]: {name} - {type(exc).__name__} ({exc})")
            raise
        print(f"{'RETURN':<8} [{uuid}]: {name}", end="")
        print("\n         " + str(ret).replace("\n", "\n         "))
        return ret

    return wrapper


def _to_dot(name, pipeline):
    name = name or str(datetime.datetime.now()).replace(":","_")
    Gst.debug_bin_to_dot_file_with_ts(
        pipeline,
        Gst.DebugGraphDetails.ALL,
        name
    )

def dotted(func):

    name = getattr(func, "__qualname__", getattr(func, "__name__", str(func)))

    @wraps(func)
    def wrapper(self, *a, **kw):
        _to_dot(f"pre_{name}", self.pipeline)
        ret = func(self, *a, **kw)
        _to_dot(f"post_{name}", self.pipeline)
        return ret
    return wrapper

def get_by_name_or_raise(gst_bin:Gst.Bin, name:str) -> Gst.Element:
    element = gst_bin.get_by_name(name)
    if element is None:
        raise NameError(f"{gst_bin} does not have a child element named '{name}'")
    return element


def _loop_in_thread(coro, loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro())

def start_asyncio_background(coro, loop):
    t = threading.Thread(target=_loop_in_thread, args=(coro, loop,))
    t.start()
    return t