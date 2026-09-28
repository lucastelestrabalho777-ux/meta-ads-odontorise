#!/usr/bin/env python3
"""Paginação: coleta resultados de um Cursor do SDK respeitando o limite pedido."""


def collect_cursor(cursor, limit=None):
    """
    Percorre um Cursor do SDK (que pagina sozinho) e devolve uma lista de dicts.
    Para assim que atinge `limit`, sem baixar as páginas seguintes.
    """
    results = []
    for item in cursor:
        results.append(item.export_all_data() if hasattr(item, "export_all_data") else item)
        if limit and len(results) >= limit:
            break
    return results
