import ipaddress
from icmplib import ping
from icmplib.exceptions import ICMPLibError
from .resultado_sonda import CollectorError, ProbeResult


class SondaIcmpService:
    """External integration: bounded, unprivileged ICMP echo through icmplib."""

    def executar(self, endereco, quantidade=4, timeout=1):
        try:
            parsed = ipaddress.ip_address(endereco)
            if parsed.is_multicast or parsed.is_unspecified:
                raise ValueError('IP não permitido')
            host = ping(str(parsed), count=quantidade, interval=0.2, timeout=timeout, privileged=False)
            return ProbeResult(host.packets_sent, host.packets_received, float(host.avg_rtt) if host.packets_received else None)
        except (ICMPLibError, OSError, ValueError) as error:
            raise CollectorError(f'Não foi possível executar o teste ICMP: {type(error).__name__}. Verifique permissões e rede do coletor.') from error
