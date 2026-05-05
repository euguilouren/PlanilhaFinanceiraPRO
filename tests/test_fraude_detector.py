"""
Testes para fraude_detector.py

    pytest tests/test_fraude_detector.py -v
"""
import math
import pytest
import pandas as pd
from datetime import date

from fraude_detector import FraudeDetector, _primeiro_digito, _e_fim_de_semana, _e_feriado


# ── Helpers ───────────────────────────────────────────────────────────────────

def _df(**kwargs) -> pd.DataFrame:
    return pd.DataFrame(kwargs)


# ── _primeiro_digito ──────────────────────────────────────────────────────────

class TestPrimeiroDigito:
    def test_inteiro_simples(self):
        assert _primeiro_digito(123) == 1

    def test_decimal(self):
        assert _primeiro_digito(0.0045) == 4

    def test_negativo_retorna_none(self):
        assert _primeiro_digito(-10) is None

    def test_zero_retorna_none(self):
        assert _primeiro_digito(0) is None

    def test_nan_retorna_none(self):
        assert _primeiro_digito(float("nan")) is None

    def test_inf_retorna_none(self):
        assert _primeiro_digito(float("inf")) is None

    def test_digito_9(self):
        assert _primeiro_digito(9999) == 9

    def test_valor_muito_pequeno(self):
        assert _primeiro_digito(0.000003) == 3


# ── _e_fim_de_semana / _e_feriado ─────────────────────────────────────────────

class TestCalendario:
    def test_sabado(self):
        assert _e_fim_de_semana(date(2024, 1, 6))   # sábado

    def test_domingo(self):
        assert _e_fim_de_semana(date(2024, 1, 7))   # domingo

    def test_segunda(self):
        assert not _e_fim_de_semana(date(2024, 1, 8))

    def test_natal_e_feriado(self):
        assert _e_feriado(date(2024, 12, 25))

    def test_independencia_e_feriado(self):
        assert _e_feriado(date(2024, 9, 7))

    def test_dia_util_nao_feriado(self):
        assert not _e_feriado(date(2024, 3, 15))


# ── FraudeDetector.benford ────────────────────────────────────────────────────

class TestBenford:
    def _df_benford(self, n=200):
        """Gera dados que seguem Benford razoavelmente."""
        import random, math
        random.seed(42)
        vals = [10 ** (random.random() * 4) for _ in range(n)]
        return _df(Valor=vals)

    def test_poucos_registros_invalido(self):
        df = _df(Valor=[100, 200, 300])
        r = FraudeDetector.benford(df, "Valor")
        assert r["valido"] is False

    def test_coluna_ausente(self):
        df = _df(Valor=[100])
        r = FraudeDetector.benford(df, "Inexistente")
        assert r["valido"] is False

    def test_distribuicao_conforme_ok(self):
        df = self._df_benford(300)
        r = FraudeDetector.benford(df, "Valor")
        assert r["valido"] is True
        assert r["nivel"] in ("OK", "MÉDIO")

    def test_distribuicao_manipulada_critica(self):
        # Todos os valores começam com 5 — viola brutalmente Benford
        vals = [500 + i * 0.1 for i in range(100)]
        df = _df(Valor=vals)
        r = FraudeDetector.benford(df, "Valor")
        assert r["valido"] is True
        assert r["nivel"] in ("ALTO", "CRÍTICO")
        assert r["chi2"] > 15.51

    def test_retorna_estrutura_esperada(self):
        df = self._df_benford(50)
        r = FraudeDetector.benford(df, "Valor")
        assert r["valido"] is True
        assert "chi2" in r
        assert "observado" in r
        assert "esperado" in r
        assert set(r["observado"].keys()) == set(range(1, 10))

    def test_ignora_negativos_e_zeros(self):
        vals = [-100, 0, 150, 250, 350] * 20
        df = _df(Valor=vals)
        r = FraudeDetector.benford(df, "Valor")
        assert r["valido"] is True
        assert r["total_registros"] == 60  # apenas positivos


# ── FraudeDetector.duplicatas_fuzzy ──────────────────────────────────────────

class TestDuplicatasFuzzy:
    def test_duplicata_exata_por_chave(self):
        df = _df(NF=["001", "002", "001"], Valor=[100, 200, 100], Cliente=["A", "B", "A"])
        r = FraudeDetector.duplicatas_fuzzy(df, "Valor", "Cliente", "NF")
        assert not r.empty
        exatas = r[r["tipo"] == "DUPLICATA_EXATA"]
        assert len(exatas) == 2  # ambas as ocorrências da chave duplicada

    def test_sem_duplicata(self):
        df = _df(NF=["001", "002", "003"], Valor=[100, 200, 300], Cliente=["A", "B", "C"])
        r = FraudeDetector.duplicatas_fuzzy(df, "Valor", "Cliente", "NF")
        assert r.empty

    def test_duplicata_fuzzy_mesmo_valor_mesma_entidade(self):
        df = _df(
            Valor=[1000.0, 1005.0, 2000.0],
            Cliente=["ALFA", "ALFA", "BETA"],
            Data=["01/01/2024", "10/01/2024", "01/01/2024"],
        )
        r = FraudeDetector.duplicatas_fuzzy(df, "Valor", "Cliente", col_data="Data")
        fuzzy = r[r["tipo"] == "DUPLICATA_FUZZY"]
        assert not fuzzy.empty

    def test_fuzzy_fora_da_janela_nao_detecta(self):
        df = _df(
            Valor=[1000.0, 1005.0],
            Cliente=["ALFA", "ALFA"],
            Data=["01/01/2024", "01/05/2024"],  # 120 dias de diferença
        )
        r = FraudeDetector.duplicatas_fuzzy(
            df, "Valor", "Cliente", col_data="Data", janela_dias=30
        )
        assert r[r["tipo"] == "DUPLICATA_FUZZY"].empty

    def test_coluna_ausente_retorna_vazio(self):
        df = _df(X=[1, 2])
        r = FraudeDetector.duplicatas_fuzzy(df, "Valor")
        assert r.empty

    def test_chave_vazia_ignorada(self):
        df = _df(NF=["", "", "001"], Valor=[100, 200, 300])
        r = FraudeDetector.duplicatas_fuzzy(df, "Valor", col_chave="NF")
        exatas = r[r["tipo"] == "DUPLICATA_EXATA"]
        assert exatas.empty


# ── FraudeDetector.numeros_redondos ──────────────────────────────────────────

class TestNumerosRedondos:
    def test_muitos_redondos_detecta(self):
        vals = [1000.0, 2000.0, 3000.0, 4000.0, 500.0, 200.0, 150.75, 180.20]
        df = _df(Valor=vals)
        r = FraudeDetector.numeros_redondos(df, "Valor", valor_minimo=100, limiar_pct=0.50)
        assert not r.empty

    def test_poucos_redondos_nao_detecta(self):
        vals = [105.30, 210.75, 333.40, 1000.0, 489.20]
        df = _df(Valor=vals)
        r = FraudeDetector.numeros_redondos(df, "Valor", limiar_pct=0.50)
        assert r.empty

    def test_abaixo_valor_minimo_ignorado(self):
        # Todos redondos mas abaixo do mínimo
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        df = _df(Valor=vals)
        r = FraudeDetector.numeros_redondos(df, "Valor", valor_minimo=100)
        assert r.empty

    def test_coluna_ausente(self):
        df = _df(X=[1000])
        assert FraudeDetector.numeros_redondos(df, "Valor").empty


# ── FraudeDetector.fracionamento ─────────────────────────────────────────────

class TestFracionamento:
    def test_detecta_fracionamento_classico(self):
        df = _df(
            Valor=[4900.0, 4950.0, 4980.0, 4920.0],
            Cliente=["FORNEC_A"] * 4,
            Data=["01/01/2024", "05/01/2024", "10/01/2024", "15/01/2024"],
        )
        r = FraudeDetector.fracionamento(df, "Valor", "Cliente", "Data")
        assert not r.empty
        assert r.iloc[0]["entidade"] == "FORNEC_A"
        assert r.iloc[0]["ocorrencias"] == 4

    def test_sem_fracionamento_valores_diferentes(self):
        df = _df(
            Valor=[100.0, 5000.0, 250.0, 8000.0],
            Cliente=["FORNEC_A"] * 4,
            Data=["01/01/2024", "05/01/2024", "10/01/2024", "15/01/2024"],
        )
        r = FraudeDetector.fracionamento(df, "Valor", "Cliente", "Data")
        assert r.empty

    def test_fora_da_janela_nao_detecta(self):
        df = _df(
            Valor=[4900.0, 4950.0, 4980.0],
            Cliente=["FORNEC_A"] * 3,
            Data=["01/01/2024", "01/03/2024", "01/05/2024"],  # 60 dias de intervalo
        )
        r = FraudeDetector.fracionamento(df, "Valor", "Cliente", "Data", janela_dias=30)
        assert r.empty

    def test_coluna_ausente_retorna_vazio(self):
        df = _df(Valor=[100], Cliente=["A"])
        r = FraudeDetector.fracionamento(df, "Valor", "Cliente", "DataInexistente")
        assert r.empty


# ── FraudeDetector.anomalias_temporais ───────────────────────────────────────

class TestAnomaliasTEmporais:
    def test_detecta_sabado(self):
        df = _df(Data=["06/01/2024"])  # sábado
        r = FraudeDetector.anomalias_temporais(df, "Data")
        assert not r.empty
        assert "Sábado" in r.iloc[0]["motivo"]

    def test_detecta_domingo(self):
        df = _df(Data=["07/01/2024"])  # domingo
        r = FraudeDetector.anomalias_temporais(df, "Data")
        assert not r.empty
        assert "Domingo" in r.iloc[0]["motivo"]

    def test_detecta_feriado_natal(self):
        df = _df(Data=["25/12/2024"])
        r = FraudeDetector.anomalias_temporais(df, "Data")
        assert not r.empty
        assert "Feriado" in r.iloc[0]["motivo"]

    def test_dia_util_nao_detecta(self):
        df = _df(Data=["15/01/2024"])  # terça-feira
        r = FraudeDetector.anomalias_temporais(df, "Data")
        assert r.empty

    def test_data_invalida_ignorada(self):
        df = _df(Data=["não-é-data", "15/01/2024"])
        r = FraudeDetector.anomalias_temporais(df, "Data")
        assert r.empty

    def test_coluna_ausente(self):
        df = _df(X=["01/01/2024"])
        assert FraudeDetector.anomalias_temporais(df, "Data").empty


# ── FraudeDetector.outliers_por_entidade ─────────────────────────────────────

class TestOutliers:
    def test_detecta_outlier_claro(self):
        vals = [100.0, 110.0, 105.0, 95.0, 102.0, 98.0, 5000.0]
        df = _df(Valor=vals, Cliente=["ALFA"] * 7)
        r = FraudeDetector.outliers_por_entidade(df, "Valor", "Cliente", sigma=2.0)
        assert not r.empty
        assert r.iloc[0]["valor"] == 5000.0

    def test_sem_outlier(self):
        vals = [100.0, 110.0, 105.0, 95.0, 102.0]
        df = _df(Valor=vals, Cliente=["ALFA"] * 5)
        r = FraudeDetector.outliers_por_entidade(df, "Valor", "Cliente", sigma=3.0)
        assert r.empty

    def test_poucos_registros_ignorado(self):
        df = _df(Valor=[100.0, 9999.0], Cliente=["A", "A"])
        r = FraudeDetector.outliers_por_entidade(df, "Valor", "Cliente", min_registros=3)
        assert r.empty

    def test_std_zero_ignorado(self):
        df = _df(Valor=[100.0, 100.0, 100.0, 100.0], Cliente=["A"] * 4)
        r = FraudeDetector.outliers_por_entidade(df, "Valor", "Cliente")
        assert r.empty

    def test_severidade_alta_para_z_muito_alto(self):
        vals = [100.0] * 10 + [10000.0]
        df = _df(Valor=vals, Cliente=["ALFA"] * 11)
        r = FraudeDetector.outliers_por_entidade(df, "Valor", "Cliente", sigma=2.0)
        assert not r.empty
        assert r.iloc[0]["severidade"] == "ALTA"


# ── FraudeDetector.concentracao ───────────────────────────────────────────────

class TestConcentracao:
    def test_detecta_concentracao_alta(self):
        df = _df(
            Valor=[8000.0, 500.0, 300.0, 200.0],
            Cliente=["DOMINA", "ALFA", "BETA", "GAMMA"],
        )
        r = FraudeDetector.concentracao(df, "Valor", "Cliente", limiar=0.30)
        assert not r.empty
        assert r.iloc[0]["entidade"] == "DOMINA"
        assert r.iloc[0]["pct_total"] > 80

    def test_sem_concentracao(self):
        df = _df(
            Valor=[300.0, 300.0, 300.0, 300.0],
            Cliente=["A", "B", "C", "D"],
        )
        r = FraudeDetector.concentracao(df, "Valor", "Cliente", limiar=0.30)
        assert r.empty

    def test_severidade_critica_acima_50pct(self):
        df = _df(Valor=[6000.0, 1000.0, 1000.0, 1000.0, 1000.0],
                 Cliente=["BIG", "A", "B", "C", "D"])
        r = FraudeDetector.concentracao(df, "Valor", "Cliente", limiar=0.30)
        assert r[r["entidade"] == "BIG"].iloc[0]["severidade"] == "CRÍTICA"

    def test_total_zero_retorna_vazio(self):
        df = _df(Valor=[0.0, 0.0], Cliente=["A", "B"])
        assert FraudeDetector.concentracao(df, "Valor", "Cliente").empty


# ── FraudeDetector.analisar (integração) ─────────────────────────────────────

class TestAnalisarIntegracao:
    def test_df_vazio_retorna_score_zero(self):
        r = FraudeDetector.analisar(pd.DataFrame(), "Valor")
        assert r["score_risco"] == 0
        assert r["alertas"] == []

    def test_coluna_valor_ausente(self):
        df = _df(X=[1, 2])
        r = FraudeDetector.analisar(df, "Valor")
        assert r["score_risco"] == 0

    def test_score_aumenta_com_fraudes(self):
        # Duplicatas + concentração alta → score > 0
        df = _df(
            Valor=[5000.0, 5000.0, 100.0],
            Cliente=["ALFA", "ALFA", "BETA"],
            NF=["001", "001", "002"],
        )
        r = FraudeDetector.analisar(df, "Valor", col_entidade="Cliente", col_chave="NF")
        assert r["score_risco"] > 0
        assert len(r["alertas"]) > 0

    def test_retorna_todas_as_chaves(self):
        df = _df(Valor=[100.0, 200.0, 300.0] * 15,
                 Cliente=["A", "B", "C"] * 15)
        r = FraudeDetector.analisar(df, "Valor", col_entidade="Cliente")
        chaves = {"benford", "duplicatas", "numeros_redondos", "fracionamento",
                  "anomalias_temporais", "outliers", "concentracao",
                  "score_risco", "alertas"}
        assert chaves.issubset(r.keys())

    def test_score_maximo_100(self):
        # Cenário extremo — garante que não ultrapassa 100
        vals = [5000.0] * 50
        df = _df(
            Valor=vals,
            Cliente=["ÚNICO"] * 50,
            NF=["001"] * 50,
            Data=["06/01/2024"] * 50,  # todos sábado
        )
        r = FraudeDetector.analisar(
            df, "Valor", col_data="Data",
            col_entidade="Cliente", col_chave="NF"
        )
        assert 0 <= r["score_risco"] <= 100
