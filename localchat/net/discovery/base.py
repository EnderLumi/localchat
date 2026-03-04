from abc import ABC, abstractmethod

from localchat.net.discovery.models import DiscoveredServer


class DiscoveryScanner(ABC):
    @abstractmethod
    def scan(self) -> list[DiscoveredServer]:
        """
        Scans the local network for active localchat servers.
        :raises IOError: on socket or protocol errors
        """


class DiscoveryResponder(ABC):
    @abstractmethod
    def start(self):
        """
        Starts answering discovery requests.
        :raises IOError: on socket errors
        """

    @abstractmethod
    def stop(self):
        """
        Stops answering discovery requests.
        """

    @abstractmethod
    def is_running(self) -> bool: ...
