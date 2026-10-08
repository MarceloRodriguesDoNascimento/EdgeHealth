from dataclasses import dataclass
from math import isfinite


class CollectorError(Exception):
    """The collector could not execute a trustworthy measurement."""


@dataclass(frozen=True)
class ProbeResult:
    """One measurement: packets sent/received and the average latency (unknown without replies)."""
    sent: int
    received: int
    latency_ms: float | None

    def __post_init__(self):
        if isinstance(self.sent, bool) or not isinstance(self.sent, int) or self.sent <= 0:
            raise CollectorError('Quantidade de pacotes enviados inválida.')
        if not isinstance(self.received, int) or isinstance(self.received, bool) or not 0 <= self.received <= self.sent:
            raise CollectorError('Quantidade de pacotes recebidos inválida.')
        if self.received and (self.latency_ms is None or not isfinite(self.latency_ms) or self.latency_ms < 0):
            raise CollectorError('Latência inválida para uma resposta recebida.')
        if not self.received and self.latency_ms is not None:
            raise CollectorError('Sem resposta, a latência deve permanecer desconhecida.')

    @property
    def loss(self):
        return (self.sent - self.received) * 100.0 / self.sent
