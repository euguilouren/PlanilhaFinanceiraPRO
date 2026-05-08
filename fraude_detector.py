"""
fraude_detector.py — Detecção de fraudes e anomalias em dados financeiros.

Módulo puro — sem DOM, sem I/O de arquivo.
Todos os métodos recebem DataFrames pandas e retornam DataFrames ou dicts.

Uso básico:
    from fraude_detector import FraudeDetector
    resultado = FraudeDetector.analisar(df, col_valor='Valor',
                                        col_data='Data',
                                        col_entidade='Cliente',
                                        col_chave='NF')
    print(resultado['score_risco'], resultado['alertas'])
"""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd

# ── Distribuição esperada pela Lei de Benford (dígitos 1-9) ──────────────────
_BENFORD: dict[int, float] = {
    1: 0.3010, 2: 0.1761, 3: 0.1249, 4: 0.0969,
    5: 0.0792, 6: 0.0669, 7: 0.0580, 8: 0.0512, 9: 0.0458,
}

# Feriados nacionais fixos do Brasil (MM-DD)
_FERIADOS_FIXOS: frozenset[str] = frozenset({
    "01-01",  # Confraternização Universal
    "04-21",  # Tiradentes
    "05-01",  # Dia do Trabalho
    "09-07",  # Independência
    "10-12",  # Nossa Senhora Aparecida
    "11-02",  # Finados
    "11-15",  # Proclamação da República
    "11-20",  # Consciência Negra
    "12-25",  # Natal
})


def _primeiro_digito(v: float) -> Optional[int]:
    """Primeiro dígito significativo de um número positivo; None se inválido."""
    if not v or not math.isfinite(v) or v <= 0:
        return None
    s = f"{abs(v):.10f}".replace(".", "").lstrip("0")
    return int(s[0]) if s else None


def _e_fim_de_semana(d) -> bool:
    return d.weekday() >= 5


def _e_feriado(d) -> bool:
    return d.strftime("%m-%d") in _FERIADOS_FIXOS


# ── Classe principal ──────────────────────────────────────────────────────────

class FraudeDetector:
    """
    Detecta fraudes e anomalias financeiras em DataFrames.
    Todos os métodos são @staticmethod — sem estado interno.
    """

    @staticmethod
    def analisar(
        df: pd.DataFrame,
        col_valor: str,
        col_data: str = "",
        col_entidade: str = "",
        col_chave: str = "",
        limiar_concentracao: float = 0.30,
        limiar_fracionamento_dias: int = 30,
        limiar_outlier_sigma: float = 3.0,
        valor_minimo: float = 100.0,
    ) -> dict:
        """
        Executa todas as análises de fraude disponíveis.

        Parâmetros opcionais habilitam módulos adicionais:
          col_data      → anomalias temporais + fracionamento
          col_entidade  → outliers, concentração, fracionamento, duplicatas fuzzy
          col_chave     → duplicatas exatas

        Retorna dict com chaves:
          benford, duplicatas, numeros_redondos, fracionamento,
          anomalias_temporais, outliers, concentracao,
          score_risco (0-100), alertas (list[str])
        """
        resultado: dict = {
            "benford": None,
            "duplicatas": pd.DataFrame(),
            "numeros_redondos": pd.DataFrame(),
            "fracionamento": pd.DataFrame(),
            "anomalias_temporais": pd.DataFrame(),
            "outliers": pd.DataFrame(),
            "concentracao": pd.DataFrame(),
            "score_risco": 0,
            "alertas": [],
        }

        if df.empty or col_valor not in df.columns:
            return resultado

        resultado["benford"] = FraudeDetector.benford(df, col_valor)

        resultado["duplicatas"] = FraudeDetector.duplicatas_fuzzy(
            df, col_valor, col_entidade, col_chave, col_data
        )

        resultado["numeros_redondos"] = FraudeDetector.numeros_redondos(
            df, col_valor, valor_minimo
        )

        if col_entidade and col_data:
            resultado["fracionamento"] = FraudeDetector.fracionamento(
                df, col_valor, col_entidade, col_data, limiar_fracionamento_dias
            )

        if col_data:
            resultado["anomalias_temporais"] = FraudeDetector.anomalias_temporais(
                df, col_data
            )

        if col_entidade:
            resultado["outliers"] = FraudeDetector.outliers_por_entidade(
                df, col_valor, col_entidade, limiar_outlier_sigma
            )
            resultado["concentracao"] = FraudeDetector.concentracao(
                df, col_valor, col_entidade, limiar_concentracao
            )

        resultado["score_risco"], resultado["alertas"] = (
            FraudeDetector._calcular_score(resultado)
        )
        return resultado

    # ── Algoritmos individuais ────────────────────────────────────────────────

    @staticmethod
    def benford(df: pd.DataFrame, col_valor: str) -> dict:
        """
        Teste da Lei de Benford — detecta adulteração em massa de valores.

        Retorna dict com: valido, chi2, nivel (OK/MÉDIO/ALTO/CRÍTICO),
        observado, esperado, desvio_por_digito.
        Requer mínimo de 30 registros positivos para ser válido.
        """
        if col_valor not in df.columns:
            return {"valido": False, "motivo": "Coluna não encontrada"}

        valores = pd.to_numeric(df[col_valor], errors="coerce").dropna()
        valores = valores[valores > 0]

        if len(valores) < 30:
            return {"valido": False, "motivo": f"Apenas {len(valores)} registros positivos (mínimo: 30)"}

        digitos = valores.map(_primeiro_digito).dropna().astype(int)
        total = len(digitos)
        if total < 30:
            return {"valido": False, "motivo": f"Apenas {total} dígitos válidos após filtragem (mínimo: 30)"}
        contagem = digitos.value_counts().reindex(range(1, 10), fill_value=0)

        esperado_s = pd.Series(_BENFORD)
        observado_s = (contagem / total).round(4)

        # Chi-quadrado (GL=8): p<0.05 → >15.51, p<0.01 → >20.09
        chi2 = float(((contagem - total * esperado_s) ** 2 / (total * esperado_s)).sum())

        if chi2 > 20.09:
            nivel = "CRÍTICO"
        elif chi2 > 15.51:
            nivel = "ALTO"
        elif chi2 > 13.36:
            nivel = "MÉDIO"
        else:
            nivel = "OK"

        return {
            "valido": True,
            "total_registros": total,
            "chi2": round(chi2, 2),
            "nivel": nivel,
            "observado": observado_s.to_dict(),
            "esperado": esperado_s.to_dict(),
            "desvio_por_digito": (observado_s - esperado_s).round(4).to_dict(),
        }

    @staticmethod
    def duplicatas_fuzzy(
        df: pd.DataFrame,
        col_valor: str,
        col_entidade: str = "",
        col_chave: str = "",
        col_data: str = "",
        tolerancia_pct: float = 0.01,
        janela_dias: int = 30,
    ) -> pd.DataFrame:
        """
        Detecta duplicatas exatas (mesma chave) e fuzzy (mesmo valor ±1%,
        mesma entidade, data próxima).
        """
        _empty = pd.DataFrame(
            columns=["tipo", "severidade", "linha", "descricao", "valor", "entidade"]
        )
        if col_valor not in df.columns:
            return _empty

        df_w = df.copy().reset_index(drop=True)
        df_w["_val"] = pd.to_numeric(df_w[col_valor], errors="coerce")
        alertas: list[dict] = []

        # Duplicatas exatas por chave
        if col_chave and col_chave in df_w.columns:
            mask = df_w[col_chave].notna() & (
                df_w[col_chave].astype(str).str.strip() != ""
            )
            def _norm_chave(v):
                try:
                    f = float(v)
                    return str(int(f)) if f == int(f) else str(f)
                except (ValueError, TypeError):
                    return str(v)
            chaves = df_w.loc[mask, col_chave].map(_norm_chave)
            dup_mask = chaves.duplicated(keep=False)
            dup_chaves = chaves[dup_mask]
            for chave_val, grupo_idx in dup_chaves.groupby(dup_chaves):
                linhas = sorted(int(i) + 2 for i in grupo_idx.index)
                primeira_row = df_w.loc[grupo_idx.index[0]]
                alertas.append({
                    "tipo": "DUPLICATA_EXATA",
                    "severidade": "CRÍTICA",
                    "linha": linhas,
                    "descricao": f"Chave '{chave_val}' duplicada",
                    "valor": primeira_row["_val"],
                    "entidade": str(primeira_row[col_entidade]) if col_entidade and col_entidade in df_w.columns else "",
                })

        # Duplicatas fuzzy por valor + entidade + janela de data
        if col_entidade and col_entidade in df_w.columns:
            df_w["_ent"] = df_w[col_entidade].astype(str).str.strip().str.upper()
            df_w = df_w[~df_w["_ent"].isin(["NAN", "NONE", "NAT", ""])]
            if col_data and col_data in df_w.columns:
                df_w["_dt"] = pd.to_datetime(df_w[col_data], errors="coerce", dayfirst=True)
            else:
                df_w["_dt"] = pd.NaT

            for ent, grupo in df_w.groupby("_ent"):
                if len(grupo) < 2:
                    continue
                idxs = grupo.index.tolist()
                for i in range(len(idxs)):
                    for j in range(i + 1, len(idxs)):
                        a, b = df_w.loc[idxs[i]], df_w.loc[idxs[j]]
                        va, vb = a["_val"], b["_val"]
                        if pd.isna(va) or pd.isna(vb) or va <= 0:
                            continue
                        if abs(va - vb) / va > tolerancia_pct:
                            continue
                        da, db = a["_dt"], b["_dt"]
                        if pd.notna(da) and pd.notna(db):
                            if abs((da - db).days) > janela_dias:
                                continue
                        alertas.append({
                            "tipo": "DUPLICATA_FUZZY",
                            "severidade": "ALTA",
                            "linha": [int(idxs[i]) + 2, int(idxs[j]) + 2],
                            "descricao": (
                                f"Valor similar (R$ {va:,.2f} ≈ R$ {vb:,.2f}) "
                                f"para '{ent}' — linha {idxs[j] + 2}"
                            ),
                            "valor": va,
                            "entidade": str(ent),
                        })

        return pd.DataFrame(alertas) if alertas else _empty

    @staticmethod
    def numeros_redondos(
        df: pd.DataFrame,
        col_valor: str,
        valor_minimo: float = 100.0,
        limiar_pct: float = 0.15,
    ) -> pd.DataFrame:
        """
        Detecta concentração anormal de valores exatamente redondos (múltiplos de 100).
        Retorna os registros suspeitos quando a frequência excede limiar_pct.
        """
        _empty = pd.DataFrame(columns=["tipo", "severidade", "descricao", "valor"])
        if col_valor not in df.columns:
            return _empty

        vals = pd.to_numeric(df[col_valor], errors="coerce")
        mask = vals.notna() & (vals >= valor_minimo)
        df_v = df[mask].copy()
        df_v["_val"] = vals[mask]

        if len(df_v) < 5:
            return _empty

        mask_redondo = df_v["_val"].apply(lambda v: v % 100 == 0)
        pct = mask_redondo.sum() / len(df_v)

        if pct < limiar_pct:
            return _empty

        result = df_v[mask_redondo].copy()
        result["tipo"] = "NÚMERO_REDONDO"
        result["severidade"] = "MÉDIA"
        result["descricao"] = result["_val"].apply(
            lambda v: f"Valor redondo R$ {v:,.0f} ({pct * 100:.1f}% dos lançamentos são redondos)"
        )
        return result[["tipo", "severidade", "descricao", "_val"]].rename(
            columns={"_val": "valor"}
        )

    @staticmethod
    def fracionamento(
        df: pd.DataFrame,
        col_valor: str,
        col_entidade: str,
        col_data: str,
        janela_dias: int = 30,
        min_ocorrencias: int = 3,
    ) -> pd.DataFrame:
        """
        Detecta fracionamento: mesmo fornecedor com múltiplas transações de valor
        similar (coeficiente de variação < 30%) em curto período.
        """
        _empty = pd.DataFrame(
            columns=["tipo", "severidade", "entidade", "ocorrencias",
                     "total_rs", "media_rs", "janela_dias", "descricao"]
        )
        if not all(c in df.columns for c in [col_valor, col_entidade, col_data]):
            return _empty

        df_w = df.copy()
        df_w["_val"] = pd.to_numeric(df_w[col_valor], errors="coerce")
        df_w["_dt"] = pd.to_datetime(df_w[col_data], errors="coerce", dayfirst=True)
        df_w["_ent"] = df_w[col_entidade].astype(str).str.strip().str.upper()
        df_w = df_w.dropna(subset=["_val", "_dt"])
        df_w = df_w[df_w["_val"] > 0]

        alertas: list[dict] = []
        for ent, grupo in df_w.groupby("_ent"):
            if len(grupo) < min_ocorrencias:
                continue
            grupo = grupo.sort_values("_dt")
            datas = grupo["_dt"].tolist()
            valores = grupo["_val"].tolist()

            for i in range(len(datas)):
                janela = [
                    (datas[j], valores[j]) for j in range(i, len(datas))
                    if (datas[j] - datas[i]).days <= janela_dias
                ]
                if len(janela) < min_ocorrencias:
                    continue
                vs = [v for _, v in janela]
                media = sum(vs) / len(vs)
                std = (sum((v - media) ** 2 for v in vs) / len(vs)) ** 0.5
                cv = std / media if media > 0 else 1.0
                if cv < 0.30:
                    duracao = (janela[-1][0] - janela[0][0]).days
                    alertas.append({
                        "tipo": "FRACIONAMENTO",
                        "severidade": "ALTA",
                        "entidade": str(ent),
                        "ocorrencias": len(janela),
                        "total_rs": round(sum(vs), 2),
                        "media_rs": round(media, 2),
                        "janela_dias": duracao,
                        "descricao": (
                            f"'{ent}': {len(janela)} transações similares "
                            f"(média R$ {media:,.2f}, CV={cv:.1%}) "
                            f"em {duracao} dias"
                        ),
                    })
                    break  # Uma detecção por entidade é suficiente

        return pd.DataFrame(alertas) if alertas else _empty

    @staticmethod
    def anomalias_temporais(df: pd.DataFrame, col_data: str) -> pd.DataFrame:
        """
        Detecta lançamentos em fins de semana e feriados nacionais brasileiros.
        """
        _empty = pd.DataFrame(
            columns=["tipo", "severidade", "linha", "data", "motivo", "descricao"]
        )
        if col_data not in df.columns:
            return _empty

        df_w = df.copy().reset_index(drop=True)
        df_w["_dt"] = pd.to_datetime(df_w[col_data], errors="coerce", dayfirst=True)
        df_v = df_w.dropna(subset=["_dt"])

        alertas: list[dict] = []
        for idx, row in df_v.iterrows():
            d = row["_dt"].date()
            if _e_fim_de_semana(d):
                motivo = "Sábado" if d.weekday() == 5 else "Domingo"
            elif _e_feriado(d):
                motivo = "Feriado Nacional"
            else:
                continue
            alertas.append({
                "tipo": "ANOMALIA_TEMPORAL",
                "severidade": "MÉDIA",
                "linha": int(idx) + 2,
                "data": str(d),
                "motivo": motivo,
                "descricao": f"Lançamento em {motivo} ({d.strftime('%d/%m/%Y')})",
            })

        return pd.DataFrame(alertas) if alertas else _empty

    @staticmethod
    def outliers_por_entidade(
        df: pd.DataFrame,
        col_valor: str,
        col_entidade: str,
        sigma: float = 3.0,
        min_registros: int = 3,
    ) -> pd.DataFrame:
        """
        Detecta valores estatisticamente anômalos por entidade (|z-score| > sigma).
        """
        _empty = pd.DataFrame(
            columns=["tipo", "severidade", "linha", "entidade",
                     "valor", "z_score", "media_entidade", "descricao"]
        )
        if not all(c in df.columns for c in [col_valor, col_entidade]):
            return _empty

        df_w = df.copy().reset_index(drop=True)
        df_w["_val"] = pd.to_numeric(df_w[col_valor], errors="coerce")
        df_w["_ent"] = df_w[col_entidade].astype(str).str.strip().str.upper()

        alertas: list[dict] = []
        for ent, grupo in df_w.groupby("_ent"):
            serie = grupo["_val"].dropna()
            if len(serie) < min_registros:
                continue
            media = float(serie.mean())
            std = float(serie.std())
            if std == 0:
                continue
            for idx, v in serie.items():
                z = (v - media) / std
                if abs(z) < sigma:
                    continue
                alertas.append({
                    "tipo": "OUTLIER",
                    "severidade": "ALTA" if abs(z) >= sigma * 1.5 else "MÉDIA",
                    "linha": int(idx) + 2,
                    "entidade": str(ent),
                    "valor": round(float(v), 2),
                    "z_score": round(z, 2),
                    "media_entidade": round(media, 2),
                    "descricao": (
                        f"'{ent}': R$ {v:,.2f} é {abs(z):.1f}σ "
                        f"{'acima' if z > 0 else 'abaixo'} da média "
                        f"(R$ {media:,.2f})"
                    ),
                })

        return pd.DataFrame(alertas) if alertas else _empty

    @staticmethod
    def concentracao(
        df: pd.DataFrame,
        col_valor: str,
        col_entidade: str,
        limiar: float = 0.30,
    ) -> pd.DataFrame:
        """
        Detecta entidades com participação anormal no total (> limiar).
        Limiar padrão: 30% do total de despesas/receitas.
        """
        _empty = pd.DataFrame(
            columns=["tipo", "severidade", "entidade",
                     "total_rs", "ocorrencias", "pct_total", "descricao"]
        )
        if not all(c in df.columns for c in [col_valor, col_entidade]):
            return _empty

        df_w = df.copy()
        df_w["_val"] = pd.to_numeric(df_w[col_valor], errors="coerce").abs()
        df_w["_ent"] = df_w[col_entidade].astype(str).str.strip().str.upper()

        total_geral = df_w["_val"].sum()
        if total_geral <= 0:
            return _empty

        resumo = (
            df_w.groupby("_ent")["_val"]
            .agg(total_rs="sum", ocorrencias="count")
        )
        resumo["pct_total"] = (resumo["total_rs"] / total_geral * 100).round(2)
        suspeitos = resumo[resumo["pct_total"] / 100 >= limiar].copy()

        if suspeitos.empty:
            return _empty

        suspeitos = suspeitos.reset_index().rename(columns={"_ent": "entidade"})
        suspeitos["tipo"] = "CONCENTRAÇÃO"
        suspeitos["severidade"] = suspeitos["pct_total"].apply(
            lambda p: "CRÍTICA" if p >= 50 else "ALTA"
        )
        suspeitos["descricao"] = suspeitos.apply(
            lambda r: (
                f"'{r['entidade']}' concentra {r['pct_total']:.1f}% do total "
                f"(R$ {r['total_rs']:,.2f} em {r['ocorrencias']} lançamentos)"
            ),
            axis=1,
        )
        return suspeitos[
            ["tipo", "severidade", "entidade", "total_rs", "ocorrencias", "pct_total", "descricao"]
        ]

    # ── Score consolidado ─────────────────────────────────────────────────────

    @staticmethod
    def _calcular_score(resultado: dict) -> tuple[int, list[str]]:
        """Agrega todos os sinais em score 0-100 e lista de alertas resumidos."""
        score = 0
        alertas: list[str] = []

        b = resultado.get("benford") or {}
        nivel_b = b.get("nivel", "OK") if b.get("valido", False) else "OK"
        if nivel_b == "CRÍTICO":
            score += 30
            alertas.append(f"Lei de Benford CRÍTICA (χ²={b.get('chi2','?')}) — possível adulteração em massa")
        elif nivel_b == "ALTO":
            score += 15
            alertas.append(f"Lei de Benford ALTA (χ²={b.get('chi2','?')}) — distribuição suspeita de valores")
        elif nivel_b == "MÉDIO":
            score += 5
            alertas.append("Lei de Benford: desvio moderado da distribuição esperada")

        def _n(key: str) -> int:
            df = resultado.get(key)
            return len(df) if isinstance(df, pd.DataFrame) and not df.empty else 0

        n_dup = _n("duplicatas")
        if n_dup:
            score += min(25, n_dup * 5)
            alertas.append(f"{n_dup} duplicata(s) detectada(s) (exatas ou por similaridade)")

        n_frac = _n("fracionamento")
        if n_frac:
            score += min(20, n_frac * 10)
            alertas.append(f"{n_frac} caso(s) de fracionamento suspeito detectado(s)")

        n_out = _n("outliers")
        if n_out:
            score += min(15, n_out * 3)
            alertas.append(f"{n_out} outlier(s) estatístico(s) por entidade")

        n_conc = _n("concentracao")
        if n_conc:
            score += min(10, n_conc * 5)
            alertas.append(f"{n_conc} entidade(s) com concentração anormal no total")

        n_temp = _n("anomalias_temporais")
        if n_temp:
            score += min(5, n_temp)
            alertas.append(f"{n_temp} lançamento(s) em fim de semana ou feriado")

        return min(score, 100), alertas
