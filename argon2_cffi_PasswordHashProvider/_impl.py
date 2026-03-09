import argon2
from importlib.metadata import version

from passwordFramwork import (
    PasswordHashProvider,
    PasswordHashProviderImpl,
    InvalidPasswordHashError,
    PasswordHashProviderError
)


_ARGON2_CFFI_VERSION_STR = version("argon2-cffi")
_ARGON2_CFFI_VERSION_TUPLE_STR = _ARGON2_CFFI_VERSION_STR.split(".")
_ARGON2_CFFI_VERSION_TUPLE_INT = tuple([int(x) for x in _ARGON2_CFFI_VERSION_TUPLE_STR])

if not (
        (_ARGON2_CFFI_VERSION_TUPLE_INT[0] >= 25) or
        (_ARGON2_CFFI_VERSION_TUPLE_INT[0] == 24 and _ARGON2_CFFI_VERSION_TUPLE_INT[1] >= 1)
):
    raise RuntimeError(f"""This library requires \"argon2-cffi\" version 24.1.0 or later to function.
The currently installed version is {_ARGON2_CFFI_VERSION_STR}.
Please update your version of \"argon2-cffi\"."""
    )


class Argon2CFFI25PasswordHashProviderImpl(PasswordHashProviderImpl):
    def __init__(self, argon2_hasher_parameters: argon2.profiles.Parameters):
        super().__init__("argon2-cffi")
        self._hasher = argon2.PasswordHasher.from_parameters(argon2_hasher_parameters)

    def hash_password_impl(self, password: bytes) -> bytes:
        try:
            result = self._hasher.hash(password)
        except argon2.exceptions.HashingError as e:
            ex = PasswordHashProviderError(e)
            ex.add_exposed_note("error while hashing password")
            raise ex

        try:
            encoded_result = result.encode("utf-8", "strict")
        except UnicodeDecodeError as e:
            ex = PasswordHashProviderError(e)
            ex.add_exposed_note("unexpected error while encoding password hash")
            raise ex

        return encoded_result

    def verify_password_impl(self, tested_password: bytes, original_serialized_password_hash: bytes) -> bool:
        try:
            password_hash = original_serialized_password_hash.decode("utf-8", "strict")
        except UnicodeDecodeError as e:
            ex = InvalidPasswordHashError(e)
            ex.add_exposed_note("error while decoding password hash")
            raise ex

        try:
            result = self._hasher.verify(password_hash, tested_password)
        except argon2.exceptions.VerifyMismatchError:
            return False
        except argon2.exceptions.VerificationError as e:
            ex = PasswordHashProviderError(e)
            ex.add_exposed_note("error while verifying password hash")
            raise ex
        except argon2.exceptions.InvalidHashError as e:
            raise InvalidPasswordHashError(e)

        return result

    def check_password_needs_rehash_impl(self, serialized_password_hash: bytes) -> bool:
        try:
            password_hash = serialized_password_hash.decode("utf-8", "strict")
        except UnicodeDecodeError as e:
            ex = InvalidPasswordHashError(e)
            ex.add_exposed_note("error while decoding password hash")
            raise ex

        return self._hasher.check_needs_rehash(password_hash)

_MY_PROVIDER_IMPL_DEFAULT = Argon2CFFI25PasswordHashProviderImpl(
    argon2.profiles.get_default_parameters()
)

def get_instance() -> PasswordHashProvider:
    return PasswordHashProvider(_MY_PROVIDER_IMPL_DEFAULT)
