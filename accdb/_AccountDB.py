import sqlite3
from typing import Iterable
from types import MappingProxyType

from ._base import Account, _AbstractAccountDB, ActionLevel
from ._AccountImplF import (
    _AccountImpl,
    ensure_user_account_user_name_is_valid,
    calculate_is_user_account_user_name_valid,
    ensure_user_account_new_password_is_valid
)

from passwordFramwork import PasswordHash, PasswordHashProvider


_MINUTE = 60.0
_HOUR = _MINUTE * 60.0
_DAY = _HOUR * 24.0
_WEEK = _DAY * 7.0


class AccountDB(_AbstractAccountDB):
    def __init__(self,
                 db_file_name: str,
                 primary_password_hash_provider: PasswordHashProvider,
                 secondary_password_hash_provider: Iterable[PasswordHashProvider],
                 deprecated_password_hash_provider: Iterable[PasswordHashProvider],
                 /,
                 user_account_max_certificate_count: int = 20,
                 highest_action_heat_session_length: float = _DAY,
                 highest_action_heat_limit: int = 1_000_000,
                 high_action_heat_session_length: float = _HOUR * 12.0,
                 high_action_heat_limit: int = 1_000_000,
                 medium_action_heat_session_length: float = _HOUR * 8.0,
                 medium_action_heat_limit: int = 1_000_000,
                 low_action_heat_session_length: float = _HOUR * 6.0,
                 low_action_heat_limit: int = 1_000_000
                 ):
        super().__init__()
        if not isinstance(db_file_name, str):
            raise TypeError("db_file_name must be of type str")
        if not isinstance(user_account_max_certificate_count, int):
            raise TypeError("user_account_max_certificate_count must be of type int")

        if not isinstance(highest_action_heat_session_length, float):
            raise TypeError("highest_action_heat_session_length must be of type float")
        if not isinstance(highest_action_heat_limit, int):
            raise TypeError("highest_action_heat_limit must be of type int")

        if not isinstance(high_action_heat_session_length, float):
            raise TypeError("high_action_heat_session_length must be of type float")
        if not isinstance(high_action_heat_limit, int):
            raise TypeError("high_action_heat_limit must be of type int")

        if not isinstance(medium_action_heat_session_length, float):
            raise TypeError("medium_action_heat_session_length must be of type float")
        if not isinstance(medium_action_heat_limit, int):
            raise TypeError("medium_action_heat_limit must be of type int")

        if not isinstance(low_action_heat_session_length, float):
            raise TypeError("low_action_heat_session_length must be of type float")
        if not isinstance(low_action_heat_limit, int):
            raise TypeError("low_action_heat_limit must be of type int")

        if not isinstance(primary_password_hash_provider, PasswordHashProvider):
            raise TypeError("primary_password_hash_provider must be of type PasswordHashProvider")
        if not isinstance(secondary_password_hash_provider, Iterable):
            raise TypeError("secondary_password_hash_provider must be of type Iterable")
        if not isinstance(deprecated_password_hash_provider, Iterable):
            raise TypeError("deprecated_password_hash_provider must be of type Iterable")

        self._db_file_name = db_file_name

        self._user_account_max_certificate_count = user_account_max_certificate_count

        self._highest_action_heat_limit = highest_action_heat_limit
        self._highest_action_heat_session_length = highest_action_heat_session_length
        self._high_action_heat_limit = high_action_heat_limit
        self._high_action_heat_session_length = high_action_heat_session_length
        self._medium_action_heat_limit = medium_action_heat_limit
        self._medium_action_heat_session_length = medium_action_heat_session_length
        self._low_action_heat_limit = low_action_heat_limit
        self._low_action_heat_session_length = low_action_heat_session_length

        self._primary_password_hash_provider = primary_password_hash_provider

        sec_pass_prov = dict[str,PasswordHashProvider]()
        for prov in secondary_password_hash_provider:
            if not isinstance(prov, PasswordHashProvider):
                raise TypeError(
                    "secondary_password_hash_provider must only contain elements of type PasswordHashProvider"
                )
            sec_pass_prov[prov.get_provider_name()] = prov
        self._secondary_password_hash_provider = MappingProxyType(sec_pass_prov)

        depr_pass_prov = dict[str,PasswordHashProvider]()
        for prov in deprecated_password_hash_provider:
            if not isinstance(prov, PasswordHashProvider):
                raise TypeError(
                    "deprecated_password_hash_provider must only contain elements of type PasswordHashProvider"
                )
            depr_pass_prov[prov.get_provider_name()] = prov
        self._deprecated_password_hash_provider = MappingProxyType(depr_pass_prov)


    def start(self):
        cursor = None
        con = self.create_connection()
        try:
            cursor = con.cursor()
            cursor.executescript(
"""
BEGIN;
CREATE TABLE IF NOT EXISTS user (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(1024) NOT NULL,
    password_hash_algorithm TEXT NOT NULL,
    password_hash BLOB NOT NULL,
    password_salt BLOB NOT NULL,
    highest_action_session_start REAL NOT NULL,
    highest_action_heat INTEGER NOT NULL,
    high_action_session_start REAL NOT NULL,
    high_action_heat INTEGER NOT NULL,
    medium_action_session_start REAL NOT NULL,
    medium_action_heat INTEGER NOT NULL,
    low_action_session_start REAL NOT NULL,
    low_action_heat INTEGER NOT NULL,
    UNIQUE (name)
);
CREATE TABLE IF NOT EXISTS user_certificate (
    user_certificate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_common_name VARCHAR(64) NOT NULL,
    not_before INTEGER NOT NULL,
    not_after INTEGER NOT NULL,
    pem_file_bytes BLOB NOT NULL,
    added_on REAL NOT NULL,
    invalidated_on REAL NOT NULL,
    owner INTEGER NOT NULL,
    FOREIGN KEY (owner) references user(user_id) ON DELETE CASCADE
);
COMMIT;
"""
            )
        finally:
            if cursor is not None:
                cursor.close()
            con.close()

    def create_connection(self) -> sqlite3.Connection:
        # WARNING: Transactions in sqlite3 are completely broken.
        # Don't question or change the code in this function.
        #
        # Bugs I found:
        # - if `isolation_level` is None and `autocommit` is False,
        #   "COMMIT" fails with "not in a transaction" and "BEGIN"
        #   fails with "already in a transaction", `in_transaction`
        #   constantly returns True, the `commit`-function has no
        #   effect
        # - if the `commit`-function is used, `in_transaction`
        #   gets desynchronized and "COMMIT" and "BEGIN" break
        # - `connect` with `autocommit=False` opens a transaction;
        #   there is something wrong with this transaction,
        #   but it is hard to pin down when mixed with the other bugs

        connection = sqlite3.connect(self._db_file_name)
        connection.autocommit = False # implicitly starts a transaction
        try:
            cur = connection.cursor()
            try:
                cur.execute("COMMIT") # close the implicitly started transaction
                # "PRAGMA" only works outside a transaction
                # silently fails if inside a transaction or if the transaction state is bugged
                cur.execute("PRAGMA foreign_keys = ON;")
                # vvv Code for debugging vvv
                ### cur.execute("PRAGMA foreign_keys;")
                ### result = cur.fetchone()
                ### assert result[0] == 1
            finally:
                cur.close()
        except:
            connection.close()
            raise
        return connection

    def add_account(self, name: str, password: bytes|PasswordHash) -> 'Account':
        ensure_user_account_user_name_is_valid(name)
        password_hash = ensure_user_account_new_password_is_valid(self, password, "password")
        connection = self.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute("BEGIN")
                cur.execute(
"""INSERT INTO user (
    name,
    password_hash_algorithm,
    password_hash,
    password_salt,
    highest_action_session_start,
    highest_action_heat,
    high_action_session_start,
    high_action_heat,
    medium_action_session_start,
    medium_action_heat,
    low_action_session_start,
    low_action_heat
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
                    (
                        name,
                        password_hash.get_password_hash_provider_name(),
                        sqlite3.Binary(password_hash.get_password_hash_body()),
                        sqlite3.Binary(b""),
                        0.0,
                        0,
                        0.0,
                        0,
                        0.0,
                        0,
                        0.0,
                        0
                    )
                )
                new_account_obj = _AccountImpl(
                    self,
                    cur.lastrowid
                )
                cur.execute("COMMIT")
                return new_account_obj
            finally:
                cur.close()
        finally:
            connection.close()

    def get_user_by_id(self, user_id: int) -> 'Account':
        if not isinstance(user_id, int):
            raise TypeError("user_id must be of type int")
        connection = self.create_connection()
        try:
            cur = connection.cursor()
            try:
                # used to test if such a user exists
                cur.execute(
                    "SELECT user_id FROM user WHERE user_id = ?",
                    (user_id,)
                )
                result = cur.fetchone()
                if result is None:
                    raise KeyError("there is no user with such an id")
                return _AccountImpl(
                    self,
                    user_id
                )
            finally:
                cur.close()
        finally:
            connection.close()

    def get_user_by_name(self, user_name: str) -> 'Account':
        if not isinstance(user_name, str):
            raise TypeError("user_name must be of type str")
        if not calculate_is_user_account_user_name_valid(user_name):
            raise KeyError("there is no user with such a name")
        connection = self.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute(
                    "SELECT user_id FROM user WHERE name = ?",
                    (user_name,)
                )
                result = cur.fetchone()
                if result is None:
                    raise KeyError("there is no user with such a name")
                return _AccountImpl(
                    self,
                    result[0]
                )
            finally:
                cur.close()
        finally:
            connection.close()

    def get_user_account_max_certificate_count(self) -> int:
        return self._user_account_max_certificate_count

    def get_action_heat_session_length(self, action_level: ActionLevel) -> float:
        if not isinstance(action_level, ActionLevel):
            raise TypeError("action_level must be of type ActionLevel")
        if action_level == ActionLevel.HIGHEST:
            return self._highest_action_heat_session_length
        if action_level == ActionLevel.HIGH:
            return self._high_action_heat_session_length
        if action_level == ActionLevel.MEDIUM:
            return self._medium_action_heat_session_length
        if action_level == ActionLevel.LOW:
            return self._low_action_heat_session_length
        raise ValueError("value of action_level is invalid")

    def get_action_heat_limit(self, action_level: ActionLevel) -> int:
        if not isinstance(action_level, ActionLevel):
            raise TypeError("action_level must be of type ActionLevel")
        if action_level == ActionLevel.HIGHEST:
            return self._highest_action_heat_limit
        if action_level == ActionLevel.HIGH:
            return self._high_action_heat_limit
        if action_level == ActionLevel.MEDIUM:
            return self._medium_action_heat_limit
        if action_level == ActionLevel.LOW:
            return self._low_action_heat_limit
        raise ValueError("value of action_level is invalid")

    def get_primary_password_hash_provider(self) -> PasswordHashProvider:
        return self._primary_password_hash_provider

    def get_secondary_password_hash_provider(self) -> dict[str, PasswordHashProvider]:
        # noinspection PyTypeChecker
        return self._secondary_password_hash_provider

    def get_deprecated_password_hash_provider(self) -> dict[str, PasswordHashProvider]:
        # noinspection PyTypeChecker
        return self._deprecated_password_hash_provider
