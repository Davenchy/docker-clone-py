import threading
from typing import Callable, Generic, List, TypeVar


SignalListener = TypeVar('SignalListener', bound=Callable[[], None])


class Signal(Generic[SignalListener]):
    """Signal is a simple implementation of an event emitter that can be used
    to listen for events emitted by other objects.

    This class is thread safe."""

    def __init__(self, name: str):
        """Define a new signal with the given name"""
        self.__name = name
        self._listeners: List[SignalListener] = []
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        """The name of the signal"""
        return self.__name

    def connect(self, listener: SignalListener):
        """Connect a listener to the signal"""
        with self._lock:
            self._listeners.append(listener)

    def disconnect(self, listener: SignalListener):
        """Disconnect a listener from the signal"""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def emit(self, *args, **kwargs):
        """Emits the signal with the given arguments"""
        with self._lock:
            for listener in self._listeners:
                listener(*args, **kwargs)

    def clear(self):
        """Clear all listeners from the signal"""
        with self._lock:
            self._listeners = []
