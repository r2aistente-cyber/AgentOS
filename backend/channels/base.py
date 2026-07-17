"""Interfaz abstracta para canales de mensajería."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class IncomingMessage:
    channel: str
    sender: str
    text: str
    chat_id: str


class Channel(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def send(self, to: str, text: str) -> None: ...

    @abstractmethod
    async def status(self) -> dict: ...
