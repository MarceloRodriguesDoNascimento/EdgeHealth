from sqlalchemy import text
from app.extensions import db


class RankingCustoRepository:
    """Top devices by estimated loss.

    The loss of each device is computed by the cost rules (working hours, time zone), so the
    values arrive here in cents and the database orders, filters and names the top devices.
    """

    @staticmethod
    def top_dispositivos(centavos_por_dispositivo, limite=5):
        """[(dispositivo_id, nome)] with loss > 0, highest loss first (ties: highest id first)."""
        if not centavos_por_dispositivo:
            return []
        params, linhas = {'limite': limite}, []
        for i, (dispositivo_id, centavos) in enumerate(centavos_por_dispositivo.items()):
            linhas.append(f'(:d{i}, :c{i})')  # placeholders only: values are always bound parameters
            params[f'd{i}'], params[f'c{i}'] = dispositivo_id, centavos
        sql = text(f"""
            WITH valores(dispositivo_id, centavos) AS (VALUES {', '.join(linhas)})
            SELECT v.dispositivo_id AS dispositivo_id, d.nome AS nome
            FROM valores v
            LEFT JOIN dispositivos d ON d.id = v.dispositivo_id
            WHERE v.centavos > 0
            ORDER BY v.centavos DESC, v.dispositivo_id DESC
            LIMIT :limite
        """)
        return [(linha.dispositivo_id, linha.nome) for linha in db.session.execute(sql, params)]
