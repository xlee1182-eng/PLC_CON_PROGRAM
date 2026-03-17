from abc import ABC, abstractmethod

class BaseAsyncPLC(ABC):

    def __init__(self, name, ip, port, tags=None):
        """Base class for asynchronous PLC objects.

        :param name: human readable PLC identifier
        :param ip: address of PLC
        :param port: connection port
        :param tags: optional list or single tag/address for polling
        """
        self.name = name
        self.ip = ip
        self.port = port
        # ``tags`` is the generic identifier used by higher level code. It
        # can be a string/number or an iterable of strings/numbers depending on
        # the driver.  A manager may iterate over this attribute to perform
        # per-tag reads.
        self.tags = tags
        self.connected = False
        self.retry_count = 0

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def read(self):
        pass

    @abstractmethod
    async def write(self, address, value):
        pass

    @abstractmethod
    async def close(self):
        pass