"""Utilitários compartilhados entre toolkit_financeiro, relatorio_html,
dashboard_visual e fraude_detector.

Antes esses helpers viviam duplicados em cada arquivo (~3x). Aqui está
a única implementação canônica — mudanças de formato (locale BRL,
escape de HTML, normalização de string) acontecem em um lugar só.
"""
from __future__ import annotations

import html
import math
from typing import Any


def fmt_brl(val: Any, dec: int = 2) -> str:
    """Formata número como moeda brasileira (R$ 1.234,56).

    Retorna '—' para None, NaN, ou valores não numéricos.
    """
    try:
        v = float(val)
    except (ValueError, TypeError):
        return '—'
    if math.isnan(v):
        return '—'
    us = f"{abs(v):,.{dec}f}"
    br = us.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"{'-' if v < 0 else ''}R$ {br}"


def esc_html(val: Any) -> str:
    """Escapa valor para inserção segura em HTML. None vira string vazia."""
    if val is None:
        return ''
    return html.escape(str(val))


def norm_text(val: Any) -> str:
    """Normalização canônica para comparação de chaves textuais:
    string strip + upper. None ou NaN viram string vazia.
    """
    if val is None:
        return ''
    try:
        if isinstance(val, float) and math.isnan(val):
            return ''
    except (ValueError, TypeError):
        pass
    return str(val).strip().upper()
