from cryptography import x509
from cryptography import hazmat
import time
import sqlite3

from ._base import (
    Account, UserCertificateDBEntry, StorageLimitError, _AbstractAccountDB,
    ActionLevel,
    account_db_find_provider
)
from ._implBase import _DBEntryView
from ._UserCertificateDBEntryImplF import _UserCertificateDBEntryImpl

from passwordFramwork import PasswordHash, PasswordHashProvider


def calculate_is_user_account_user_name_valid(user_name: str) -> bool:
    if not isinstance(user_name, str):
        raise TypeError("user_name must be of type str")
    try:
        return len(user_name.encode("utf-8", "strict")) <= 1024
    except UnicodeEncodeError:
        return False

def ensure_user_account_user_name_is_valid(user_name: str) -> None:
    if not isinstance(user_name, str):
        raise TypeError("user_name must be of type str")
    if len(user_name.encode("utf-8", "strict")) > 1024:
        raise StorageLimitError("name is too long")

def ensure_user_account_new_password_is_valid(
        account_db: _AbstractAccountDB,
        new_password: bytes|PasswordHash,
        arg_name: str
) -> PasswordHash:
    if isinstance(new_password, bytes):
        return account_db.get_primary_password_hash_provider().hash_password(new_password)
    elif isinstance(new_password, PasswordHash):
        password_hash = new_password
        if (password_hash.get_password_hash_provider_name() !=
                account_db.get_primary_password_hash_provider().get_provider_name()):
            raise TypeError(
                f"password hash provider of {arg_name} must equal to the primary password hash provider"
                " of the account database"
            )
        return password_hash
    else:
        raise TypeError(f"{arg_name} must be of type bytes or PasswordHash")

class _AccountImpl(Account, _DBEntryView):
    def __init__(self, account_db: _AbstractAccountDB, account_id: int):
        if not isinstance(account_db, _AbstractAccountDB):
            raise TypeError("account_db must be of type _AbstractAccountDB")
        if not isinstance(account_id, int):
            raise TypeError("account_id must be of type int")
        super().__init__()
        self._id = account_id
        self._db = account_db

    def get_id(self) -> int:
        return self._id

    def get_name(self) -> str:
        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute(
                    "SELECT name FROM user WHERE user_id = ?;",
                    (self._id,)
                )
                result = cur.fetchone()
                if result is None:
                    self._mark_db_entry_view_as_outdated()
                    raise self._outdated_error()
                return result[0]
            finally:
                cur.close()
        finally:
            connection.close()

    def set_name(self, name: str) -> None:
        ensure_user_account_user_name_is_valid(name)
        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute("BEGIN")
                cur.execute(
                    "UPDATE user SET name = ? WHERE user_id = ?",
                    (name, self._id,)
                )
                cur.execute("COMMIT")
            finally:
                cur.close()
        finally:
            connection.close()

    def list_certificates(self) -> list[UserCertificateDBEntry]:
        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute(
        """
        SELECT
            user_certificate_id,
            subject_common_name,
            not_before,
            not_after,
            added_on,
            invalidated_on
        FROM user_certificate WHERE user_certificate.owner = ?
        """,
                        (self._id,)
                )
                result = cur.fetchmany(self._db.get_user_account_max_certificate_count())
                cert_objects = []
                for certEntry in result:
                    cert_obj = _UserCertificateDBEntryImpl(
                        self._db,
                        certEntry[0],
                        certEntry[1],
                        certEntry[2],
                        certEntry[3],
                        certEntry[4],
                        certEntry[5],
                       self
                    )
                    cert_objects.append(cert_obj)
                return cert_objects
            finally:
                cur.close()
        finally:
            connection.close()

    def add_certificate(self, cert: x509.Certificate) -> int:
        if not isinstance(cert, x509.Certificate):
            raise TypeError("cert must be of type x509.Certificate")
        self._ensure_is_not_outdated()
        max_certs = self._db.get_user_account_max_certificate_count()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute("BEGIN")
                cur.execute(
"""INSERT INTO user_certificate (
    subject_common_name,
    not_before,
    not_after,
    pem_file_bytes,
    added_on,
    invalidated_on,
    owner
) VALUES (?, ?, ?, ?, ?, ?, ?)
""",
                    (
                        cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value,
                        cert.not_valid_before_utc.timestamp(),
                        cert.not_valid_after_utc.timestamp(),
                        sqlite3.Binary(cert.public_bytes(encoding=hazmat.primitives.serialization.Encoding.DER)),
                        time.time(),
                        -1.0,
                        self._id
                    )
                )
                new_user_cert_id = cur.lastrowid
                cur.execute(
                    "SELECT user_certificate_id FROM user_certificate WHERE user_certificate.owner = ?",
                    (self._id,)
                )
                result = cur.fetchmany(max_certs + 1)
                if len(result) > max_certs:
                    raise StorageLimitError("user already has the maximal amount of allowed certificates")
                cur.execute("COMMIT")
                return new_user_cert_id
            finally:
                cur.close()
        finally:
            connection.close()

    def set_password(self, password: bytes|PasswordHash) -> None:
        password_hash = ensure_user_account_new_password_is_valid(self._db, password, "password")
        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute("BEGIN")
                cur.execute(
                    """
UPDATE
    user
SET
    password_hash_algorithm = ?,
    password_hash = ?,
    password_salt = ?
WHERE
    user_id = ?
                    """,
                    (
                        password_hash.get_password_hash_provider_name(),
                        sqlite3.Binary(password_hash.get_password_hash_body()),
                        sqlite3.Binary(b""),
                        self._id
                    )
                )
                if cur.rowcount == 0:
                    self._mark_db_entry_view_as_outdated()
                    raise self._outdated_error()
                cur.execute("COMMIT")
            finally:
                cur.close()
        finally:
            connection.close()

    def _get_password_impl_0(self, cur: sqlite3.Cursor) -> tuple[str, bytes, bytes]:
        cur.execute(
            "SELECT password_hash_algorithm, password_hash, password_salt FROM user WHERE user_id = ?",
            (self._id,)
        )
        result = cur.fetchone()
        if result is None:
            self._mark_db_entry_view_as_outdated()
            raise self._outdated_error()
        return result

    def _get_password_impl_1(self) -> tuple[str, bytes, bytes]:
        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                return self._get_password_impl_0(cur)
            finally:
                cur.close()
        finally:
            connection.close()

    def get_password(self) -> PasswordHash:
        result = self._get_password_impl_1()
        return PasswordHash(result[0], result[1])

    def verify_password(self, password: bytes, /, rehash_password_if_needed: bool=True) -> bool:
        current_password_db_entry = self._get_password_impl_1()
        current_hash = PasswordHash(current_password_db_entry[0], current_password_db_entry[1])
        current_provider_name = current_hash.get_password_hash_provider_name()
        current_provider = account_db_find_provider(self._db, current_provider_name)
        if not current_provider.verify_password(password, current_hash):
            return False

        if not (
                rehash_password_if_needed and
                (
                        current_provider_name in self._db.get_deprecated_password_hash_provider() or
                        current_provider.check_password_needs_rehash(current_hash)
                )
        ):
            return True

        new_hash = self._db.get_primary_password_hash_provider().hash_password(password)

        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute("BEGIN")
                cur.execute(
                    """
                    UPDATE
                        user
                    SET
                        password_hash_algorithm = ?,
                        password_hash = ?,
                        password_salt = ?
                    WHERE
                        user_id = ? AND
                        password_hash_algorithm = ? AND
                        password_hash = ? AND
                        password_salt = ?
                    """,
                    (
                        new_hash.get_password_hash_provider_name(),
                        sqlite3.Binary(new_hash.get_password_hash_body()),
                        sqlite3.Binary(b""),
                        self._id,
                        current_password_db_entry[0],
                        sqlite3.Binary(current_password_db_entry[1]),
                        sqlite3.Binary(current_password_db_entry[2])
                    )
                )
                # might affect no rows if:
                # - account got deleted
                # - new password was set in the same moment
                # - password was rehashed by another connection in the same moment
                # in all cases, we just commit and ignore it, because we reached our goal (or don't need it anymore)
                cur.execute("COMMIT")
            finally:
                cur.close()
        finally:
            connection.close()

        self._ensure_is_not_outdated()
        return True

    @staticmethod
    def _action_level_to_colum_name(action_level: ActionLevel) -> str:
        if action_level == ActionLevel.HIGHEST:
            return "highest_action"
        if action_level == ActionLevel.HIGH:
            return "high_action"
        if action_level == ActionLevel.MEDIUM:
            return "medium_action"
        if action_level == ActionLevel.LOW:
            return "low_action"
        raise ValueError("Invalid action level")

    def _get_action_heat(self, cur: sqlite3.Cursor, time_now, action_level: ActionLevel) -> int|None:
        action_level_colum_name_prefix = self._action_level_to_colum_name(action_level)
        cur.execute(
            f"""
SELECT
    {action_level_colum_name_prefix}_session_start,
    {action_level_colum_name_prefix}_heat
FROM
    user
WHERE
    user_id = ?
"""
        )
        result = cur.fetchone()
        if result is None:
            self._mark_db_entry_view_as_outdated()
            raise self._outdated_error()
        session_start: float = result[0]
        session_heat: int = result[1]
        session_end = session_start + self._db.get_action_heat_session_length(action_level)
        if time_now >= session_end:
            return None
        else:
            return session_heat

    def try_add_action_heat(self, action_level: ActionLevel, amount: int) -> bool:
        if not isinstance(action_level, ActionLevel):
            raise TypeError("action_level must be of type ActionLevel")
        if not isinstance(amount, int):
            raise TypeError("amount must be of type int")
        if amount < 0:
            raise ValueError("amount must be a positive number or zero")
        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute("BEGIN")
                time_now = time.time()
                session_heat_state = self._get_action_heat(cur, time_now, action_level)
                heat_session_is_running = session_heat_state is not None
                session_heat = session_heat_state if session_heat_state is not None else 0
                heat_limit = self._db.get_action_heat_limit(action_level)
                if session_heat >= heat_limit:
                    return False
                new_session_heat = session_heat + amount
                heat_is_too_high = new_session_heat > heat_limit
                action_level_colum_name_prefix = self._action_level_to_colum_name(action_level)
                if heat_session_is_running:
                    cur.execute(
                        f"""
UPDATE
    user
SET
    {action_level_colum_name_prefix}_heat = ?
WHERE
    user_id = ?
""",
                        (new_session_heat, self._id)
                    )
                else:
                    cur.execute(
                        f"""
UPDATE
    user
SET
    {action_level_colum_name_prefix}_session_start = ?,
    {action_level_colum_name_prefix}_heat = ?
WHERE
    user_id = ?
                        """,
                        (time_now, new_session_heat, self._id)
                    )
                if cur.rowcount == 0:
                    self._mark_db_entry_view_as_outdated()
                    raise self._outdated_error()
                cur.execute("COMMIT")
                return not heat_is_too_high
            finally:
                cur.close()
        finally:
            connection.close()

    def get_action_heat(self, action_level: ActionLevel) -> int:
        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                heat_session_state = self._get_action_heat(cur, time.time(), action_level)
                return heat_session_state if heat_session_state is not None else 0
            finally:
                cur.close()
        finally:
            connection.close()

    def remove(self) -> None:
        self._ensure_is_not_outdated()
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute("BEGIN")
                cur.execute(
                    """DELETE FROM user
                        WHERE user_id = ?;
                    """,
                    (self._id, )
                )
                self._mark_db_entry_view_as_outdated()
                if cur.rowcount == 0:
                    raise self._outdated_error()
                cur.execute("COMMIT")
            finally:
                cur.close()
        finally:
            connection.close()