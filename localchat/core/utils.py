# Hilfsfunktionen, Farben, Zeitstempel

from typing import Any, TypeVar, Generic, Self
from threading import Lock, RLock
from collections.abc import Callable

T = TypeVar('T')

class _UndefinedValue:
        INSTANCE : Self
        def __init__(self): ...
_UndefinedValue.INSTANCE =  _UndefinedValue()

class Lazy(Generic[T]):
    """
    Non-reassignable, non-threadsave lazy.
    Streamlines the use of lazy evaluation, meaning,
    that values are only fetched or calculated as soon as they
    are needed.
    """
    def __new__(cls, supplier : Callable[[],T]|None = None, /, value : T|_UndefinedValue = _UndefinedValue.INSTANCE) -> Self:
        self = LazyImpl._create_new()
        return self # type: ignore
    def get(self) -> T: ...

class MutableLazy(Lazy[T]):
    """
    Reassignable, non-threadsave lazy.
    Streamlines the use of lazy evaluation, meaning,
    that values are only fetched or calculated as soon as they
    are needed.
    """
    def __new__(cls, supplier : Callable[[],T]|None = None, /, value : T|_UndefinedValue = _UndefinedValue.INSTANCE) -> Self:
        self = MutableLazyImpl._create_new()
        return self # type: ignore
    def set_value(self, value : T): ...
    def set_supplier(self, supplier : Callable[[],T]): ...

class ConcurrentLazy(Lazy[T]):
    """
    Non-reassignable, threadsave lazy.
    Streamlines the use of lazy evaluation, meaning,
    that values are only fetched or calculated as soon as they
    are needed.
    """
    def __new__(cls, supplier : Callable[[],T]|None = None, /, value : T|_UndefinedValue = _UndefinedValue.INSTANCE) -> Self:
        self = ConcurrentLazyImpl._create_new()
        return self # type: ignore

class MutableConcurrentLazy(ConcurrentLazy[T],MutableLazy[T]):
    """
    Reassignable, threadsave lazy.
    Streamlines the use of lazy evaluation, meaning,
    that values are only fetched or calculated as soon as they
    are needed.
    """
    def __new__(cls, supplier : Callable[[],T]|None = None, /, value : T|_UndefinedValue = _UndefinedValue.INSTANCE) -> Self:
        self = MutableConcurrentLazyImpl._create_new()
        return self # type: ignore

def _lazy_args_validate(supplier : Callable[[],T]|None, value : T|_UndefinedValue):
    if value == _UndefinedValue.INSTANCE:
        if supplier == None: raise ValueError("supplier must not be None if value is undefined")
    elif supplier != None: raise ValueError("supplier must be None if value is defined")

class LazyImpl(Lazy[T]):

    @classmethod
    def _create_new(cls):
        return object.__new__(cls)
    def __init__(self, supplier : Callable[[],T]|None = None, /, value : T|_UndefinedValue = _UndefinedValue.INSTANCE):
        _lazy_args_validate(supplier,value)
        self._supplier : Callable[[],T]|None = supplier
        self._value : T|_UndefinedValue = value
    def get(self) -> T:
        if self._value == _UndefinedValue.INSTANCE:
            s = self._supplier
            if s == None: raise RuntimeError("concurrent modification")
            self._value = s()
            self._supplier = None
        return self._value # type: ignore

class MutableLazyImpl(MutableLazy[T]):
    @classmethod
    def _create_new(cls):
        return object.__new__(cls)
    def __init__(self, supplier : Callable[[],T]|None = None, /, value : T|_UndefinedValue = _UndefinedValue.INSTANCE):
        _lazy_args_validate(supplier,value)
        self._supplier : Callable[[],T]|None = supplier
        self._value : T|_UndefinedValue = value
    def get(self) -> T:
        v = self._value
        if v != _UndefinedValue.INSTANCE:
            return v # type: ignore
        s = self._supplier
        if s == None: raise RuntimeError("concurrent modification")
        v = s()
        self._value = v
        self._supplier = None
        return v
    def set_value(self, value : T):
        self._supplier = None
        self._value = value
    def set_supplier(self, supplier : Callable[[],T]):
        self._supplier = supplier
        self._value = _UndefinedValue.INSTANCE

class ConcurrentLazyImpl(ConcurrentLazy[T]):
    @classmethod
    def _create_new(cls):
        return object.__new__(cls)
    def __init__(self, supplier : Callable[[],T]|None = None, /, value : T|_UndefinedValue = _UndefinedValue.INSTANCE):
        _lazy_args_validate(supplier,value)
        self._supplier = supplier
        self._value = value
        self._lock = RLock() # RLock to avoid deadlock on recursive lazy call (will cause stack overflow exception instead)
    def _get_subr1(self):
        with self._lock:
            if self._value != _UndefinedValue.INSTANCE: return
            self._value = self._supplier() #type: ignore
        self._supplier = None
    def get(self) -> T:
        if self._value == _UndefinedValue.INSTANCE:
            self._get_subr1()
        return self._value #type: ignore

class MutableConcurrentLazyImpl(MutableConcurrentLazy[T]):
    @classmethod
    def _create_new(cls):
        return object.__new__(cls)
    def __init__(self, supplier : Callable[[],T]|None = None, /, value : T|_UndefinedValue = _UndefinedValue.INSTANCE):
        _lazy_args_validate(supplier,value)
        self._supplier : Callable[[],T]|None = supplier
        self._value : T|_UndefinedValue = value
        # lock must be reentrant to avoid deadlock on recursive supplier call
        # (will cause stack overflow exception instead)
        self._lock = RLock()
    def get(self) -> T:
        with self._lock:
            if self._value == _UndefinedValue.INSTANCE:
                self._value = self._supplier() # type: ignore
                self._supplier = None
            return self._value # type: ignore
    def set_value(self, value: T):
        with self._lock:
            self._supplier = None
            self._value = value
    def set_supplier(self, supplier: Callable[[], T]):
        with self._lock:
            self._supplier = supplier
            self._value = _UndefinedValue.INSTANCE
