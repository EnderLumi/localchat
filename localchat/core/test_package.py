
from typing import TypeVar, Generic, Any, Iterator
import io

from package import (
    Package, PackageFactory, PackageFieldType, BytesPackageFieldType,
    StringPackageFieldType, IntegerPackageFieldType, FloatPackageFieldType
)

class _RisingNumbersBytesPackageFieldType(BytesPackageFieldType):
    def __init__(self):
        super().__init__("risingNumbers",3,False)
    def deserialized_validator(self, value : Any) -> bool:
        if not super().deserialized_validator(value): return False
        if len(value) == 0: return True
        last = value[0]
        for val in value[1:]:
            if val != last + 1: return False
            last = val
        return True

class _LegalUserNameStringPackageFieldType(StringPackageFieldType):
    def __init__(self):
        super().__init__("legalUserName",5,False)
    def deserialized_validator(self, value : Any) -> bool:
        if not super().deserialized_validator(value): return False
        assert isinstance(value,str)
        return value.strip() == value and len(value) != 0

class _Between1And20IntegerPackageFieldType(IntegerPackageFieldType):
    def __init__(self):
        super().__init__("between1And20",True)
    def deserialized_validator(self, value : Any) -> bool:
        if not super().deserialized_validator(value): return False
        return value >= 1 and value <= 20

class _Between0And1FloatPackageFieldType(FloatPackageFieldType):
    def __init__(self):
        super().__init__("between0And1",True)
    def deserialized_validator(self, value : Any) -> bool:
        if not super().deserialized_validator(value): return False
        return value >= 0 and value <= 1

_package_factory_emptry = PackageFactory(set())
_package_factory_optional_single_entry = PackageFactory(set([
    _Between1And20IntegerPackageFieldType(),
    ]))
_package_factory_big = PackageFactory(set([
    _RisingNumbersBytesPackageFieldType(),
    _LegalUserNameStringPackageFieldType(),
    _Between1And20IntegerPackageFieldType(),
    _Between0And1FloatPackageFieldType()
    ]))

def test_main():
    p1a = _package_factory_emptry.create_new()
    b1 = io.BytesIO()
    p1a.serialize(b1)
    b1.seek(0)
    p1b = _package_factory_emptry.deserialize(b1)
    assert p1a == p1b

    p2a = _package_factory_optional_single_entry.create_new()
    b2 = io.BytesIO()
    p2a.serialize(b2)
    b2.seek(0)
    p2b = _package_factory_optional_single_entry.deserialize(b2)
    assert p2a == p2b

    p3a = _package_factory_big.create_new()

    # enter non existant
    try:
        p3a["nonExistant"] = "hey"
        assert False, "incorrect success"
    except KeyError as e:
        ...
    except:
        assert False, "incorrect exception type"


    ### bytes ###
    #enter wrong value bytes: incorrect value
    incorrect = [
        bytes([4,9,100]),
        bytes([1,2,3,4,5,6,7,8,9])
        ]
    for inco in incorrect:
        try:
            p3a["risingNumbers"] = inco
            assert False, "incorrect success"
        except ValueError as e:
            ...
        except:
            assert False, "incorrect exception type"

    #enter wrong value bytes: incorrect type
    try:
        p3a["risingNumbers"] = True
        assert False, "incorrect success"
    except ValueError as e:
        ...
    except:
        assert False, "incorrect exception type"

    #delete bytes absent
    try:
        del p3a["risingNumbers"]
        assert False, "incorrect success"
    except:
        ...

    #enter correc value bytes
    correct = [
        bytes([]),
        bytes([1,2]),
        bytes([20,21,22])
        ]
    for corr in correct:
        try:
            p3a["risingNumbers"] = corr
        except:
            assert False, "incorrect failure"

    #delete bytes present
    try:
        del p3a["risingNumbers"]
    except:
        assert False, "incorrect failure"

    ### string ###
    #enter wrong value string: incorrect value
    incorrect = [
        "",
        "  hey",
        "test 123 "
        ]
    for inco in incorrect:
        try:
            p3a["legalUserName"] = inco
            assert False, "incorrect success"
        except ValueError as e:
            ...
        except:
            assert False, "incorrect exception type"

    #enter wrong value string: incorrect type
    try:
        p3a["legalUserName"] = True
        assert False, "incorrect success"
    except ValueError as e:
        ...
    except:
        assert False, "incorrect exception type"

    #delete string absent
    try:
        del p3a["legalUserName"]
        assert False, "incorrect success"
    except:
        ...

    #enter correc value string
    correct = [
        "a",
        "bob",
        "five_"
        ]
    for corr in correct:
        try:
            p3a["legalUserName"] = corr
        except:
            assert False, "incorrect failure"

    #delete string present
    try:
        del p3a["legalUserName"]
    except:
        assert False, "incorrect failure"


    # TODO continue test (Im done for now)


if __name__ == "__main__":
    test_main()




