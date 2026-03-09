from cryptography import x509
import time

from ._base import Account, UserCertificateDBEntry, _AbstractAccountDB
from ._implBase import _DBEntryView


class _UserCertificateDBEntryImpl(UserCertificateDBEntry, _DBEntryView):
    def __init__(self,
                 account_db: '_AbstractAccountDB',
                 user_cert_id: int,
                 subject_common_name: str,
                 not_before: float,
                 not_after: float,
                 added_on: float,
                 invalidated_on: float,
                 owner: 'Account'
                 ):
        super().__init__() # max_age=account_db.get_user_certificate_db_entry_view_max_age()
        self._db = account_db
        self._user_cert_id = user_cert_id
        self._subject_common_name = subject_common_name
        self._not_before = not_before
        self._not_after = not_after
        self._added_on = added_on
        self._invalidated_on = invalidated_on
        self._owner = owner

    def get_id(self) -> int:
        return self._user_cert_id

    def get_subject_common_name(self) -> str:
        return self._subject_common_name

    def get_not_before(self) -> float:
        return self._not_before

    def get_not_after(self) -> float:
        return self._not_after

    def get_certificate(self) -> x509.Certificate:
        self._ensure_is_not_outdated()
        con = self._db.create_connection()
        try:
            curser = con.cursor()
            try:
                curser.execute(
                    """
                    SELECT pem_file_bytes
                    FROM user_certificate
                    WHERE user_certificate_id = ?
                    """,
                    (self._user_cert_id,)
                )
                result = curser.fetchone()
                if result is None:
                    self._mark_db_entry_view_as_outdated()
                    raise self._outdated_error()
                return x509.load_der_x509_certificate(result[0])
            finally:
                curser.close()
        finally:
            con.close()

    def get_added_on(self) -> float:
        return self._added_on

    def get_invalidated_on(self) -> float:
        self._ensure_is_not_outdated()
        if self._invalidated_on > 0.0:
            return self._invalidated_on
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute(
                    "SELECT invalidated_on FROM user_certificate WHERE user_certificate_id = ?",
                    (self._user_cert_id,)
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

    def get_owner(self) -> 'Account':
        return self._owner

    def invalidate(self) -> None:
        self._ensure_is_not_outdated()
        if self._invalidated_on > 0.0:
            return
        connection = self._db.create_connection()
        try:
            cur = connection.cursor()
            try:
                cur.execute("BEGIN")
                cur.execute(
                    "SELECT invalidated_on FROM user_certificate WHERE user_certificate_id = ?",
                    (self._user_cert_id,)
                )
                result = cur.fetchone()
                if result is None:
                    self._mark_db_entry_view_as_outdated()
                    raise self._outdated_error()
                if result[0] > 0.0:
                    self._invalidated_on = result[0]
                    return
                time_now = time.time()
                cur.execute(
                    """
                    UPDATE user_certificate
                    SET invalidated_on = ?
                    WHERE user_certificate_id = ?;
                    """,
                    (time_now, self._user_cert_id)
                )
                if cur.rowcount == 0:
                    self._mark_db_entry_view_as_outdated()
                    raise self._outdated_error()
                cur.execute("COMMIT")
                self._invalidated_on = time_now
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
                    """
                    DELETE FROM user_certificate
                    WHERE user_certificate_id = ?;
                    """,
                    (self._user_cert_id, )
                )
                self._mark_db_entry_view_as_outdated()
                if cur.rowcount == 0:
                    raise self._outdated_error()
                cur.execute("COMMIT")
            finally:
                cur.close()
        finally:
            connection.close()