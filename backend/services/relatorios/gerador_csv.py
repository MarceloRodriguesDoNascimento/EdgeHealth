import csv
import io
import json


class GeradorCsv:
    """CSV for spreadsheets: ';' separator, UTF-8 with BOM and no formula injection."""

    @staticmethod
    def gerar(linhas, campos):
        out = io.StringIO(newline='')
        writer = csv.writer(out, delimiter=';')
        writer.writerow(campos)
        for row in linhas:
            values = []
            for field in campos:
                value = row.get(field)
                if isinstance(value, (dict, list)): value = json.dumps(value, ensure_ascii=False)
                if value is None: value = ''
                if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                    value = "'" + value  # Prevent spreadsheet formula injection on export.
                values.append(value)
            writer.writerow(values)
        return ('﻿' + out.getvalue()).encode('utf-8')
