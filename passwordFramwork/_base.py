from typing import final, Iterable
import threading
from warnings import warn


MAX_PASSWORD_HASH_PROVIDER_NAME_LENGTH = 4 * 1024
MAX_PASSWORD_HASH_PROVIDER_NAME_ENCODED_SIZE = MAX_PASSWORD_HASH_PROVIDER_NAME_LENGTH * 4


class _ExposedNotesException(Exception):
    def __init__(self, *args):
        super().__init__(*args)
        self._exposed_notes_lock = threading.Lock()
        self._exposed_notes: list[str] = []
        self._exposed_notes_immutable: tuple[str, ...] | None = None

    def add_all_exposed_notes(self, exposed_notes: Iterable[str]|_ExposedNotesException) -> None:
        if isinstance(exposed_notes, _ExposedNotesException):
            exposed_notes_iterable = exposed_notes.get_exposed_notes()
        elif isinstance(exposed_notes, Iterable):
            exposed_notes_iterable = exposed_notes
        else:
            raise TypeError(
                "exposed_notes must be of type Iterable, UnacceptablePasswordError, InvalidPasswordHashError or "
                "PasswordHashProviderError"
            )
        exposed_notes_list = list(exposed_notes_iterable)
        if len(exposed_notes_list) == 0:
            return
        for note in exposed_notes_list:
            if not isinstance(note, str):
                raise TypeError("elements of exposed_notes must be of type str")
        with self._exposed_notes_lock:
            self._exposed_notes_immutable = None
            self._exposed_notes.extend(exposed_notes_list)

    def add_exposed_note(self, exposed_note: str) -> None:
        if not isinstance(exposed_note, str):
            raise TypeError("exposed_note must be of type str")
        with self._exposed_notes_lock:
            self._exposed_notes_immutable = None
            self._exposed_notes.append(exposed_note)

    def get_exposed_notes(self) -> Iterable[str]:
        with self._exposed_notes_lock:
            if self._exposed_notes_immutable is None:
                self._exposed_notes_immutable = tuple(self._exposed_notes)
            return self._exposed_notes_immutable


class UnacceptablePasswordError(_ExposedNotesException):
    def __init__(self, *args):
        super().__init__(*args)


class InvalidPasswordHashError(_ExposedNotesException):
    def __init__(self, *args):
        super().__init__(*args)


class PasswordHashProviderError(_ExposedNotesException):
    def __init__(self, *args):
        super().__init__(*args)


def with_exposed_notes_of(old_exception: _ExposedNotesException, new_exception: _ExposedNotesException):
    exposed_notes = old_exception.get_exposed_notes()
    new_exception.add_all_exposed_notes(exposed_notes)

def ensure_is_like_bytes(arg: bytes|bytearray|memoryview, arg_name: str):
    """

    :param arg:
    :param arg_name:
    :return:
    :raises TypeError: If `arg` is not of type `bytes`, `bytearray` or `memoryview`.
    """
    if not isinstance(arg, (bytes, bytearray, memoryview)):
        raise TypeError(f"{arg_name} must be of type bytes, bytearray or memoryview")


def arg_like_bytes(arg: bytes|bytearray|memoryview, arg_name: str) -> bytes:
    """

    :param arg:
    :param arg_name:
    :return:
    :raises TypeError: If `arg` is not of type `bytes`, `bytearray` or `memoryview`.
    """
    ensure_is_like_bytes(arg, arg_name)
    return arg if isinstance(arg, bytes) else bytes(arg)


def ensure_is_valid_provider_name(provider_name: str):
    """

    :param provider_name:
    :return:
    :raises ValueError: If `provider_name` is not a valid password hash provider name.
    """
    if len(provider_name) > MAX_PASSWORD_HASH_PROVIDER_NAME_LENGTH:
        raise ValueError("password hash provider name too long")
    try:
        provider_name.encode("utf-8", "strict")
    except UnicodeDecodeError as e:
        raise ValueError("password hash provider name can not be encoded in UTF-8", e)

_SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE = 2
_SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_MAX_VALUE = (
        2 ** (_SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE * 8) - 1
)
assert _SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_MAX_VALUE >= MAX_PASSWORD_HASH_PROVIDER_NAME_ENCODED_SIZE

@final
class PasswordHash:
    """
    Stores a password hash and the name of the password hash provider in memory.
    Immutable object.
    """
    def __init__(self, password_hash_provider_name: str, body: bytes|bytearray|memoryview):
        """
        Creates a new `PasswordHash` Object.
        :param password_hash_provider_name: The name of the password provider.
        :param body: The bytes that stores the password hash and any necessary meta information about it.
        :raises TypeError:  If `password_hash_provider_name` is not of type str or
                            `body` is not of type `bytes`, `bytearray` or `memoryview`.
        :raises ValueError: If `password_hash_provider_name` is not a valid password provider name.
        """
        if not isinstance(password_hash_provider_name, str):
            raise TypeError("password_hash_provider_name must be of type str")
        body_bytes = arg_like_bytes(body, "body")
        ensure_is_valid_provider_name(password_hash_provider_name)
        self._provider_name = password_hash_provider_name
        self._body = body_bytes

    def get_password_hash_provider_name(self) -> str:
        return self._provider_name

    def get_password_hash_body(self) -> bytes:
        return self._body

    def serialize(self) -> bytes:
        """
        Converts this password hash and the password hash provider name into a binary format.
        :return: The binary representation of this object.
        """
        prov_name_bytes = self._provider_name.encode("utf-8", "strict")
        return (
                len(prov_name_bytes).to_bytes(
                    _SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE,
                    "big"
                ) +
                prov_name_bytes +
                self._body
        )

    @staticmethod
    def deserialize(serialized_object: bytes|bytearray|memoryview) -> "PasswordHash":
        """
        Creates a new `PasswordHash` Object that contains the information stored in the given
        binary representation of a `PasswordHash`-Object.
        :param serialized_object:
        :return:
        :raises TypeError: If `serialized_object` is not of type `bytes`, `bytearray` or `memoryview`.
        :raises ValueError: If `serialized_object` is not a valid binary representation of a `PasswordHash`-Object.
        """
        ensure_is_like_bytes(serialized_object, "serialized_object")

        if len(serialized_object) < _SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE:
            raise ValueError("corrupted serialized object")

        prov_name_bytes_length_bytes = serialized_object[:_SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE]
        prov_name_bytes_length = int.from_bytes(prov_name_bytes_length_bytes, "big")

        if prov_name_bytes_length > MAX_PASSWORD_HASH_PROVIDER_NAME_ENCODED_SIZE:
            raise ValueError("corrupted serialized object: password hash provider name too long")

        if prov_name_bytes_length > len(serialized_object) - _SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE:
            raise ValueError("corrupted serialized object")

        prov_name_bytes = serialized_object[
            _SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE:
            prov_name_bytes_length + _SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE
        ]
        try:
            prov_name = prov_name_bytes.decode("utf-8", "strict")
        except UnicodeDecodeError as e:
            raise ValueError("corrupted serialized object: unicode decoding error", e)

        if len(prov_name) > MAX_PASSWORD_HASH_PROVIDER_NAME_LENGTH:
            raise ValueError("corrupted serialized object: password hash provider name too long")

        body = serialized_object[prov_name_bytes_length + _SERIALIZED_PASSWORD_HASH_PROVIDER_NAME_LENGTH_FIELD_SIZE:]

        return PasswordHash(prov_name, body)


class PasswordHashProviderImpl:
    """
    This object must be overwritten by classes that implement
    a password hash provider implementation.
    """
    def __init__(self, provider_name: str):
        """
        Creates a new `PasswordHashProviderImpl`-object.
        :param provider_name: The name of this password provider.
        :raises TypeError: If `provider_name` is not of type str.
        :raises ValueError: If `provider_name` is not a valid password hash provider name.
        """
        super().__init__()
        if not isinstance(provider_name, str):
            raise TypeError("provider_name must be of type str")
        ensure_is_valid_provider_name(provider_name)
        self._password_hash_provider_impl_base_class_provider_name = provider_name

    @final
    def get_provider_name(self) -> str:
        """
        Returns the name of this password hash provider implementation.
        :return:
        """
        return self._password_hash_provider_impl_base_class_provider_name

    def hash_password_impl(self, password: bytes) -> bytes:
        """
        Calculates the hash for the given password.
        The returned bytes must also contain all the metadata about this hash
        this implementation might need when later testing, if this hash needs
        rehashing, or when verifying a password. The returned bytes must be
        usable not only by this instance of this class, but also by other instances
        of this implementation in this process or other processes.
        Whenever possible, the returned binary representation should be
        usable by instances of this class even when running on different operating
        systems or machines with different architectures. Otherwise, the
        password hash provider implementation name should contain a hint
        about its platform dependency (for example: 'my-hash-provider-name-win32').
        The password hash metadata must not contain any sensitive data about the password.
        :param password: The password to be hashed.
        :return: The binary representation of a password hash and meta information about it.
        :raises UnacceptablePasswordError: If `tested_password` is unacceptable.
        :raises PasswordHashProviderError: If an error occurs while hashing the given password.
        :raises NotImplementedError: If this provider did not implement this method.
        """
        raise NotImplementedError()

    def verify_password_impl(self, tested_password: bytes, original_serialized_password_hash: bytes) -> bool:
        """
        Verifies, that the given password is the original source of the given password hash.
        :param tested_password: The password to be verified.
        :param original_serialized_password_hash: The password hash of the original password.
        :return:    `True` if the given password is the original source of the given password hash,
                    `False` otherwise.
        :raises UnacceptablePasswordError: If `tested_password` is unacceptable.
        :raises InvalidPasswordHashError: If `original_serialized_password_hash` is invalid.
        :raises PasswordHashProviderError: If an error occurs while verifying the given password.
        :raises NotImplementedError: If this provider did not implement this method.
        """
        raise NotImplementedError()

    def check_password_needs_rehash_impl(self, serialized_password_hash: bytes) -> bool:
        """
        Checks, if the given password hash needs rehashing.
        :param serialized_password_hash: The password hash to be checked.
        :return: `True` if the given password hash needs rehashing, `False` otherwise.
        :raises InvalidPasswordHashError: If `serialized_password_hash` is invalid.
        :raises PasswordHashProviderError: If an error occurs while checking if the given password hash needs rehashing.
        :raises NotImplementedError: If this provider did not implement this method.
        """
        raise NotImplementedError()


@final
class PasswordHashProvider:
    """
    This object provides an interface for client
    applications to use password hash implementation with.
    """
    def __init__(self, provider_impl: PasswordHashProviderImpl):
        """
        Creates a new `PasswordHashProvider`-object using the give password hash provider implementation.
        :param provider_impl: The password hash provider implementation that should be used.
        :raises TypeError: If `provider_impl` is not of type `PasswordHashProviderImpl`.
        :raises PasswordHashProviderError:  If `provider_impl` is not a valid implementation of
                                            `PasswordHashProviderImpl`.
        """
        super().__init__()

        # test and store impl
        if not isinstance(provider_impl, PasswordHashProviderImpl):
            raise TypeError("provider_impl must be of type PasswordHashProviderImpl")
        self._impl = provider_impl

        # get, test and store provider name
        provider_name = self._impl.get_provider_name()
        try:
            if not isinstance(provider_name, str):
                raise TypeError("get_provider_name() must return object of type str")
            ensure_is_valid_provider_name(provider_name)
        except (TypeError, ValueError) as e:
            raise PasswordHashProviderError("invalid password provider implementation", e)
        self._provider_name = provider_name

        self.__dbm = False

    def _set_debug_mode(self, active: bool) -> None:
        if not isinstance(active, bool):
            raise TypeError("active must be of type bool")
        if active:
            warning_text = f"""
======= WARNING! =======
Enabled Debug Mode For Password Hash Provider.
This Might LEAK PASSWORD INFORMATION In Debug
Messages! Do Not Use In Production
Environments!
Name of password provider in debug mode:
\"{self.get_provider_name()}\"
"""
            warn(warning_text, RuntimeWarning, stacklevel=2)
        self.__dbm = active

    def get_provider_name(self) -> str:
        """
        Returns the name of this password hash provider.
        :return: The name of this password hash provider.
        """
        return self._provider_name

    def hash_password(self, password: bytes) -> PasswordHash:
        """
        Hashes the given password.
        :param password: The password to be hashed.
        :return: The password hash that was created from the given password.
        :raises TypeError: If `password` is not of type bytes.
        :raises UnacceptablePasswordError: If `tested_password` is unacceptable.
        :raises PasswordHashProviderError: If an error occurs while hashing the given password.
        """
        if not isinstance(password, bytes):
            raise TypeError("password must be of type bytes")

        if self.__dbm:
            try:
                result = self._impl.hash_password_impl(password)
            except NotImplementedError as e:
                raise PasswordHashProviderError("not implemented", e)
            except Exception as e:
                raise AssertionError("Unexpected error", e)

        else:
            try:
                result = self._impl.hash_password_impl(password)
            except UnacceptablePasswordError as old_ex:
                new_ex = UnacceptablePasswordError()
                new_ex.add_all_exposed_notes(old_ex)
                raise new_ex
            except PasswordHashProviderError as old_ex:
                new_ex = PasswordHashProviderError()
                new_ex.add_all_exposed_notes(old_ex)
                raise new_ex
            except NotImplementedError:
                raise PasswordHashProviderError("not implemented")
            except Exception:
                raise AssertionError("unexpected error")

        if not isinstance(result, bytes):
            raise PasswordHashProviderError("invalid implementation return value")

        return PasswordHash(
            self.get_provider_name(),
            result
        )

    def verify_password(self, tested_password: bytes, original_password_hash: PasswordHash) -> bool:
        """
        Verifies the given password using the given password hash of the original password.
        :param tested_password: The password to be verified.
        :param original_password_hash: The password hash of the original password.
        :return: `True` if the tested password was correct, `False` if the tested password was wrong.
        :raises TypeError:  If `tested_password` is not of type bytes or `original_password_hash` is not
                            of type `PasswordHash`.
        :raises ValueError: If the password hash provider of `original_password_hash` is not this password
                            hash provider.
        :raises UnacceptablePasswordError: If `tested_password` is unacceptable.
        :raises InvalidPasswordHashError: If `original_password_hash` is invalid.
        :raises PasswordHashProviderError: If an error occurs while verifying the given password.
        """
        if not isinstance(tested_password, bytes):
            raise TypeError("tested_password must be of type bytes")
        if not isinstance(original_password_hash, PasswordHash):
            raise TypeError("original_password_hash must be of type PasswordHash")

        if original_password_hash.get_password_hash_provider_name() != self.get_provider_name():
            raise ValueError("password hash provider mismatch")

        if self.__dbm:
            try:
                result = self._impl.verify_password_impl(
                    tested_password,
                    original_password_hash.get_password_hash_body()
                )
            except NotImplementedError as e:
                raise PasswordHashProviderError("not implemented", e)
            except Exception as e:
                raise AssertionError("unexpected error", e)

        else:
            try:
                result = self._impl.verify_password_impl(
                    tested_password,
                    original_password_hash.get_password_hash_body()
                )
            except UnacceptablePasswordError as old_ex:
                new_ex = UnacceptablePasswordError()
                new_ex.add_all_exposed_notes(old_ex)
                raise new_ex
            except InvalidPasswordHashError as old_ex:
                new_ex = InvalidPasswordHashError()
                new_ex.add_all_exposed_notes(old_ex)
                raise new_ex
            except PasswordHashProviderError as old_ex:
                new_ex = PasswordHashProviderError()
                new_ex.add_all_exposed_notes(old_ex)
                raise new_ex
            except NotImplementedError:
                raise PasswordHashProviderError("not implemented")
            except Exception:
                raise AssertionError("Unexpected error")

        if not isinstance(result, bool):
            raise PasswordHashProviderError("invalid implementation return value")

        return result

    def check_password_needs_rehash(self, password_hash: PasswordHash):
        """
        Checks if the given password hash needs rehashing.
        :param password_hash: The password hash to be checked.
        :return: `True` if the password hash needs rehashing, `False` if rehashing is not necessary.
        :raises TypeError: If `password_hash` is not of type `PasswordHash`.
        :raises ValueError: If the password hash provider of `password_hash` is not this password
                            hash provider.
        :raises InvalidPasswordHashError: If `password_hash` is invalid.
        :raises PasswordHashProviderError: If an error occurs while checking if the given password hash needs rehashing.
        """
        if not isinstance(password_hash, PasswordHash):
            raise TypeError("password_hash must be of type PasswordHash")

        if password_hash.get_password_hash_provider_name() != self.get_provider_name():
            raise ValueError("password hash provider mismatch")

        if self.__dbm:
            try:
                result = self._impl.check_password_needs_rehash_impl(
                    password_hash.get_password_hash_body()
                )
            except NotImplementedError as e:
                raise PasswordHashProviderError("not implemented", e)
            except Exception as e:
                raise AssertionError("unexpected error", e)

        else:
            try:
                result = self._impl.check_password_needs_rehash_impl(
                    password_hash.get_password_hash_body()
                )
            except InvalidPasswordHashError as old_ex:
                new_ex = InvalidPasswordHashError()
                new_ex.add_all_exposed_notes(old_ex)
                raise new_ex
            except PasswordHashProviderError as old_ex:
                new_ex = PasswordHashProviderError()
                new_ex.add_all_exposed_notes(old_ex)
                raise new_ex
            except NotImplementedError:
                raise PasswordHashProviderError("not implemented")
            except Exception:
                raise AssertionError("unexpected error")

        if not isinstance(result, bool):
            raise PasswordHashProviderError("invalid implementation return value")

        return result