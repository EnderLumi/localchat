from cryptography import x509
import sqlite3
from enum import Enum

from passwordFramwork import PasswordHash, PasswordHashProvider


class OutdatedError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class StorageLimitError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class UserCertificateDBEntry:
    def __init__(self):
        super().__init__()

    def get_id(self) -> int:
        raise NotImplementedError()

    def get_subject_common_name(self) -> str:
        raise NotImplementedError()

    def get_not_before(self) -> float:
        raise NotImplementedError()

    def get_not_after(self) -> float:
        raise NotImplementedError()

    def get_certificate(self) -> x509.Certificate:
        raise NotImplementedError()

    def get_added_on(self) -> float:
        raise NotImplementedError()

    def get_invalidated_on(self) -> float:
        raise NotImplementedError()

    def get_owner(self) -> 'Account':
        raise NotImplementedError()

    def invalidate(self) -> None:
        raise NotImplementedError()

    def remove(self) -> None:
        raise NotImplementedError()

    def __repr__(self):
        try:
            return f"UserCertificateDBEntry[id={self.get_id()}, subject_common_name={self.get_subject_common_name()}]"
        except OutdatedError:
            return f"UserCertificateDBEntry[OUTDATED]"


class ActionLevel(Enum):
    HIGHEST = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class Account:
    def __init__(self):
        super().__init__()

    def get_id(self) -> int:
        raise NotImplementedError()

    def get_name(self) -> str:
        raise NotImplementedError()

    def set_name(self, name: str) -> None:
        raise NotImplementedError()

    def list_certificates(self) -> list[UserCertificateDBEntry]:
        raise NotImplementedError()

    def add_certificate(self, cert: x509.Certificate) -> UserCertificateDBEntry:
        raise NotImplementedError()

    def set_password(self, password: bytes|PasswordHash) -> None:
        raise NotImplementedError()

    def get_password(self) -> PasswordHash:
        raise NotImplementedError()

    def verify_password(self, password: bytes, /, rehash_password_if_needed: bool=True) -> bool:
        raise NotImplementedError()

    def try_add_action_heat(self, action_level: ActionLevel, amount: int) -> bool:
        raise NotImplementedError()

    def get_action_heat(self, action_level: ActionLevel) -> int:
        raise NotImplementedError()

    def remove(self) -> None:
        raise NotImplementedError()

    def __repr__(self):
        try:
            return f"Account[id={self.get_id()}, name={self.get_name()}]"
        except OutdatedError:
            return f"Account[OUTDATED]"


class _AbstractAccountDB:
    def __init__(self):
        super().__init__()

    def start(self):
        raise NotImplementedError()

    def create_connection(self) -> sqlite3.Connection:
        raise NotImplementedError()

    def add_account(self, name: str, password: bytes|PasswordHash) -> 'Account':
        raise NotImplementedError()

    def get_user_by_id(self, user_id: int) -> 'Account':
        raise NotImplementedError()

    def get_user_by_name(self, user_name: str) -> 'Account':
        raise NotImplementedError()

    def get_user_account_max_certificate_count(self) -> int:
        raise NotImplementedError()

    def get_action_heat_session_length(self, action_level: ActionLevel) -> float:
        raise NotImplementedError()

    def get_action_heat_limit(self, action_level: ActionLevel) -> int:
        raise NotImplementedError()

    def get_primary_password_hash_provider(self) -> PasswordHashProvider:
        raise NotImplementedError()

    def get_secondary_password_hash_provider(self) -> dict[str, PasswordHashProvider]:
        raise NotImplementedError()

    def get_deprecated_password_hash_provider(self) -> dict[str, PasswordHashProvider]:
        raise NotImplementedError()


def account_db_unsupported_password_hash_provider_error(provider_name: str):
    return ValueError(f"unsupported password hash provider: {provider_name}")

def account_db_try_find_provider(account_db: _AbstractAccountDB, provider_name: str) -> PasswordHashProvider | None:
    if provider_name == account_db.get_primary_password_hash_provider().get_provider_name():
        return account_db.get_primary_password_hash_provider()
    secondary_provider = account_db.get_secondary_password_hash_provider()
    if provider_name in secondary_provider:
        return secondary_provider[provider_name]
    deprecated_provider = account_db.get_deprecated_password_hash_provider()
    if provider_name in deprecated_provider:
        return deprecated_provider[provider_name]
    return None

def account_db_find_provider(account_db: _AbstractAccountDB, provider_name: str) -> PasswordHashProvider:
    result = account_db_try_find_provider(account_db, provider_name)
    if result is None:
        raise account_db_unsupported_password_hash_provider_error(provider_name)
    return result

def account_db_hash_password(account_db: _AbstractAccountDB, password: bytes) -> PasswordHash:
    return account_db.get_primary_password_hash_provider().hash_password(password)

def account_db_validate_password(account_db: _AbstractAccountDB, tested_password: bytes, original_password: PasswordHash) -> bool:
    provider_name = original_password.get_password_hash_provider_name()
    provider = account_db_find_provider(account_db, provider_name)
    return provider.verify_password(tested_password, original_password)

def account_db_check_password_needs_rehash(account_db: _AbstractAccountDB, password_hash: PasswordHash):
    provider_name = password_hash.get_password_hash_provider_name()
    provider = account_db_try_find_provider(account_db, provider_name)
    if provider is None or provider.get_provider_name() in account_db.get_deprecated_password_hash_provider():
        return True
    return provider.check_password_needs_rehash(password_hash)









