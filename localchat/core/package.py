from collections.abc import Callable
from typing import TypeVar, Generic, Any, Iterator
from io import BytesIO
import math
import io

T = TypeVar('T')

class PackageValidationError(IOError):
    """
    Raised if a package failes
    to be validated while
    deserialisation.
    """
    def __init__(self, message : str):
        super().__init__(message)

class PackageFieldType(Generic[T]):
    """
    Defines a field type in a package.
    Contains methodes for validation,
    serialisation and deserialisation
    for the storead value.
    """
    def __init__(self, identifier : str, serialied_byte_limit : int, optional : bool):
        self._identifier = identifier
        self._serialied_byte_limit = serialied_byte_limit
        self._optional = optional
    def get_identifier(self):
        """
        Returns the package fields identifier.
        ("username", "payload", ...)
        """
        return self._identifier
    def get_serialied_byte_limit(self):
        """
        Returns the packages fields maximal allowed
        size when stored as bytes.
        This is neccessary to prevent huge payloads that
        crash receiving clients.
        """
        return self._serialied_byte_limit
    def get_is_optional(self):
        """
        Returns whetever the package field is optional.
        Packages with non-optional fields missing will
        throw a exception on serialisation and
        deserialisation. This is ment to avoid
        sending invalid packages and to make
        validation of incoming packages more
        manageable.
        """
        return self._optional
    def serialized_validator(self, b : bytes) -> bool:
        """
        This methode is called every time a package
        field value is deserialized.
        It decides whetever the value is legal or illegal.
        It must only return 'True', if the 'deserializer'
        methode will be capable of processing this bytes.
        """
        ...
    def deserialized_validator(self, value : Any) -> bool:
        """
        This methode is called every time a value
        of this field type is set in a package.
        It decides whetever the value is legal or illegal.
        Notice, that 'value' can be of any type. Therefore,
        'isinstance' should always be a part of the methode
        implementation.
        """
        ...
    def serializer(self, value : T) -> bytes:
        """
        Serialises a value to bytes.
        'value' is assumed to have passed the
        'deserialized_validator' test.
        This methode should work with all
        values that can pass the
        'deserialized_validator' test.
        """
        ...
    def deserializer(self, b : bytes) -> T:
        """
        Deserialises bytes to a value.
        b' is assumed to have passed the
        'serialized_validator' test.
        This methode should work with all
        byte blocks that can pass the
        'serialized_validator' test.
        """
        ...

class BytesPackageFieldType(PackageFieldType[bytes]):
    """
    Defines a field type in a package that stores bytes.
    Should be overloaded with a class that overwrites
    the 'deserialized_validator' methodes to providebe better
    value validation.
    'if not super().deserialized_validator(value): return False'
    should be called at the beginning of the overwriting
    methode.
    """
    def __init__(self, identifier : str, serialied_byte_limit : int, optional : bool):
        super().__init__(identifier,serialied_byte_limit,optional)
    def serializer(self, value : bytes) -> bytes: return value
    def deserializer(self, b : bytes) -> bytes: return b
    def serialized_validator(self, b : bytes) -> bool:
        assert len(b) <= self.get_serialied_byte_limit(), "package 'serialied byte limit' has not been tested"
        return True
    def deserialized_validator(self, value : Any) -> bool:
        return isinstance(value,bytes) and len(value) <= self.get_serialied_byte_limit()

class StringPackageFieldType(PackageFieldType[str]):
    """
    Defines a field type in a package that stores a string.
    Should be overloaded with a class that overwrites
    the 'deserialized_validator' methodes to providebe better
    value validation.
    'if not super().deserialized_validator(value): return False'
    should be called at the beginning of the overwriting
    methode.
    """
    def __init__(self, identifier : str, character_limit : int, optional : bool):
        super().__init__(identifier,int(character_limit * 4.2) + 8,optional)
        self._character_limit = character_limit
    def serialized_validator(self, b : bytes) -> bool:
        try:
            b.decode("utf-8","strict")
        except UnicodeDecodeError:
            return False
        return True
    def deserialized_validator(self, value : Any) -> bool:
        if not isinstance(value,str): return False
        if len(value) > self._character_limit: return False
        return True
    def serializer(self, value : str) -> bytes:
        return value.encode("utf-8","strict")
    def deserializer(self, b : bytes) -> str:
        return b.decode("utf-8","strict")

class IntegerPackageFieldType(PackageFieldType[int]):
    """
    Defines a field type in a package that stores an integer.
    Should be overloaded with a class that overwrites
    the 'deserialized_validator' methodes to providebe better
    value validation.
    'if not super().deserialized_validator(value): return False'
    should be called at the beginning of the overwriting
    methode.
    """
    def __init__(self, identifier : str, optional : bool):
        super().__init__(identifier, 20, optional)
    def serialized_validator(self, b : bytes) -> bool:
        if len(b) != 16: return False
    def deserialized_validator(self, value : Any) -> bool:
        return isinstance(value,int)
    def serializer(self, value : int) -> bytes:
        return value.to_bytes(16,"big",signed=True)
    def deserializer(self, b : bytes) -> int:
        return int.from_bytes(b,"big",signed=True)

class FloatPackageFieldType(PackageFieldType[float]):
    """
    Defines a field type in a package that stores an float.
    Should be overloaded with a class that overwrites
    the 'deserialized_validator' methodes to providebe better
    value validation.
    'if not super().deserialized_validator(value): return False'
    should be called at the beginning of the overwriting
    methode.
    """
    def __init__(self, identifier : str, optional : bool):
        super().__init__(identifier, 36, optional)
    def _float_pack_to_ints(self, b : bytes) -> tuple[int,int]:
        first_bytes = b[:16]
        last_bytes = b[16:32]
        return (
            int.from_bytes(first_bytes,"big",signed=True),
            int.from_bytes(last_bytes,"big",signed=False)
            )
    def serialized_validator(self, b : bytes) -> bool:
        if len(b) != 32: return False
        ints = self._float_pack_to_ints(b)
        return not (ints[1] == 0 and not ints[0] in [0,1,2,3])
    def deserialized_validator(self, value : Any) -> bool:
        return isinstance(value,float) or isinstance(value,int)
    def serializer(self, value : float|int) -> bytes:
        value = float(value)
        if value == math.nan: ints = (1,0)
        elif value == math.inf: ints = (2,0)
        elif value == -math.inf: ints = (3,0)
        else: ints = value.as_integer_ratio()
        return ints[0].to_bytes(16,"big",signed=True) + ints[1].to_bytes(16,"big",signed=False)
    def deserializer(self, b : bytes) -> int:
        ints = self._float_pack_to_ints(b)
        if ints[0] != 0 and ints[1] == 0:
            if ints[0] == 1: return math.nan
            if ints[1] == 2: return math.inf
            if ints[2] == 3: return -math.inf
            raise ValueError("bytes are not a valid float package field value")
        return float(float(ints[0]) / float(ints[1]))

class Package: ...

class PackageFactory:
    """
    Every package needs a factory.
    The factory defines the fields a
    package type can contain.
    """
    def __init__(self, fields : set[PackageFieldType]):
        self._fields = dict([(field.get_identifier(),field) for field in fields])
        self._largest_identifier = max([0] + [len(field.get_identifier()) for field in fields])

    def get_fields(self) -> dict[str,PackageFieldType]:
        return dict(self._fields)
    def create_new(self) -> Package:
        return Package(self)

    def get_largest_identifier(self):
        return self._largest_identifier

    # Might be counterintuitive, 'get_fields' is less efficient, but easier to understand
    """
    def __len__(self) -> int:
        return len(self._fields)
    def __contains__(self, key : str) -> bool:
        return key in self._fields
    def __getitem__(self, key : str) -> PackageFieldType:
        return self._fields[key]
    def __setitem__(self, key : str, value: Any) -> None:
        raise UnsupportedOperation("package factories are immutable")
    def __delitem__(self, key : str) -> None:
        raise UnsupportedOperation("package factories are immutable")
    def __iter__(self) -> Iterator[str]:
        return self._fields.__iter__()
    def __reversed__(self) -> Iterator[str]:
        return self._fields.__reversed__()
    """

    def deserialize(self, src : BytesIO) -> Package:
        """
        Reads a package from a byte stream.
        @throws PackageValidationError - if src does not contain a valid package
        @throws IOError - if an IOError occurs while reading from src
        @thorws EOFError - if src unexpectedly reaches EOF
        """
        pack = self.create_new()
        pack.deserialize(src)
        return pack

class Package:
    """
    A package is a lot
    like a directory.
    Keys or values inserted into
    the package are validated.
    Packages can be serialized
    and deserialited, but
    serialized failes if any
    non-optional keys are missing
    in the package.
    The properties of a package
    are defined by its package
    factory.
    """
    _MAX_STR_TO_BYTE_FACTOR = 4.2
    def __init__(self, factory : PackageFactory):
        self._factory = factory
        self._data : dict[str,Any] = {}
    def get_factory(self) -> PackageFactory:
        return self._factory
    def __len__(self) -> int:
        return len(self._data)
    def __contains__(self, key : str) -> bool:
        return key in self._data
    def __getitem__(self, key : str):
        return self._data[key]
    def __setitem__(self, key : str, value: Any) -> None:
        fields = self._factory.get_fields() 
        if not key in fields: raise KeyError(f"unknown package field name: '{key}'")
        field = fields[key]
        if not field.deserialized_validator(value):
            raise ValueError(f"attempted to assign invalid value '{value}' to package field {key}")
        self._data[key] = value
    def __delitem__(self, key : str) -> None:
        del self._data[key]
    def __iter__(self) -> Iterator[str]:
        return self._data.__iter__()
    def __eq__(self, value : object, /) -> bool:
        if not isinstance(value,Package): return False
        if value.get_factory() != self._factory: return False
        return self._data == value._data
    def __reversed__(self) -> Iterator[str]:
        return self._data.__reversed__()

    def _validate(self) -> bool:
        fields = self._factory.get_fields()
        for key in fields:
            if not key in self._data and not fields[key].get_is_optional():
                return False
        return True

    """
    Writes the package to a byte stream.
    @throws IOError - if an IOError occurs while writing to dest
    """
    def serialize(self, dest : BytesIO):
        assert self._validate(), "Package is missing non-optional fields"
        fields = self._factory.get_fields()
        for key in self._data:
            key_bytes = key.encode("utf-8")
            key_block_size = len(key_bytes)
            dest.write(key_block_size.to_bytes(8,"big",signed=False))
            dest.write(key_bytes)
            value_bytes = fields[key].serializer(self._data[key])
            value_block_size = len(value_bytes)
            dest.write(value_block_size.to_bytes(8,"big",signed=False))
            dest.write(value_bytes)
        dest.write((0).to_bytes(8,"big",signed=False))

    @staticmethod
    def _read_exact(src : BytesIO, n : int) -> bytes:
        b = src.read(n)
        if b == None: raise EOFError("unexpected EOF while package deserialisation")
        assert len(b) <= n
        while len(b) < n:
            bytes_left = n - len(b)
            new_b = src.read(bytes_left)
            if b == None: raise EOFError("unexpected EOF while package deserialisation")
            assert len(new_b) <= bytes_left
            b += new_b
        return b

    @staticmethod
    def _read_block_size(src : BytesIO) -> int:
        b = Package._read_exact(src,8);
        return int.from_bytes(b,'big', signed=False)

    def deserialize(self, src : BytesIO):
        """
        Reads a package from a byte stream.
        @throws PackageValidationError - if src does not contain a valid package
        @throws IOError - if an IOError occurs while reading from src
        @thorws EOFError - if src unexpectedly reaches EOF
        """
        before = self._data
        try:
            self._data = {}
            max_iden_byte_len = int(self._factory.get_largest_identifier() * Package._MAX_STR_TO_BYTE_FACTOR)
            pack = self
            factory : PackageFactory = self._factory
            fields = factory.get_fields()
            while True:
                key_block_size = Package._read_block_size(src)
                if key_block_size == 0: break
                if key_block_size > max_iden_byte_len:
                    raise PackageValidationError("unexpected field identifier: field identifier is too large")
                key_bytes = Package._read_exact(src,key_block_size)
                try:
                    key = key_bytes.decode("utf-8","strict")
                except UnicodeDecodeError:
                    raise PackageValidationError("invalid field identifier: field identifier contains invalid unicode")
                if not key in fields:
                    raise PackageValidationError(f"unexpected field identifier: '{key}'")
                if key in pack:
                    raise PackageValidationError(f"duplicate field identifier: '{key}'")
                field = fields[key]
                value_block_size = Package._read_block_size(src)
                if value_block_size > field.get_serialied_byte_limit():
                    raise PackageValidationError(f"invalid field value: value for field '{key}' is too large")
                value_bytes = Package._read_exact(src,value_block_size)
                if not field.serialized_validator(value_bytes):
                    raise PackageValidationError(f"invalid field value: value for field '{key}' is illegal")
                value = field.deserializer(value_bytes)
                assert field.deserialized_validator(value), f"deserializer of field '{key}' returned an illegal value as its result"
                pack[key] = value
            for key in fields:
                if not key in pack and not fields[key].get_is_optional():
                    raise PackageValidationError(f"invalid package: non-optional field '{key}' is missing")
            return pack
        except:
            self._data = before
            raise

class UserNamePackageFieldType(StringPackageFieldType):
    """
    A package field type for storing a user name.
    """
    def __init__(self, identifier : str):
        super().__init__(identifier, 256, True)
    def deserializer(self, b):
        username = super().deserializer(b)
        if not super().deserialized_validator(username): return username
        normalized_username = self._normalize_user_name(username)
        return normalized_username if normalized_username != None else username
    def deserialized_validator(self, value) -> bool:
        if not super().deserialized_validator(value): return False
        assert isinstance(value,str)
        return self._normalize_user_name(value) != None
        # if len(value) <= 1: return False
        # if value.strip() != value: return False
        # if any([e in value for e in ["  ","\t","\n","\r"]]): return False
        # if not value.isprintable(): return False
        # return True
    def _normalize_user_name(self, value : str) -> str|None:
        value = (
            value.strip()
            .replace("\r\n","\n")
            .replace("\r"," ")
            .replace("\n"," ")
            .replace("\t"," ")
                 )
        value = "".join([c if c.isprintable() else "#" for c in value])
        value = value.strip()
        result = io.StringIO()
        last_was_space = False
        for c in value:
            if c == " ":
                if not last_was_space:
                    result.write(c)
                last_was_space = True
            else:
                last_was_space = False
                result.write(c)
        value = result.getvalue()
        return value if len(value) >= 2 else None
    def normalize_user_name(self, username : str) -> str:
        result = self._normalize_user_name(username)
        if result == None: raise ValueError("'username' must be a legal username")
        return result


class ColorPackageFieldType(BytesPackageFieldType):
    """
    A package field type for storing RGB color values.
    """
    def __init__(self, identifier : str, optional : bool):
        super().__init__(identifier,3,optional)
    def deserialized_validator(self, value) -> bool:
        if not super().deserialized_validator(value): return False
        return len(value) == 3
