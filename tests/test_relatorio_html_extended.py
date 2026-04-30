"""
Testes estendidos para relatorio_html.py — cobertura de seções não testadas.
"""
import pytest
import pandas as pd
from relatorio_html import GeradorHTML


@pytest.fixture
def cfg():
    return {
        'relatorio': {
            'titulo': 'Teste',
            'empresa': 'Empresa',
            'tema': {
                'cor_primaria': '#1F4E79',
                'cor_secundaria': '#2E75B6',
                'cor_ok': '#C6EFCE',
                'cor_alerta': '#FFEB9C',
                'cor_critico': '#FFC7CE',
            },
        },
        'colunas': {'valor': 'Valor'},
    }


@pytest.fixture
def g(cfg):
    return GeradorHTML(cfg)


@pytest.fixture
def df_dados():
    return pd.DataFrame({'NF': ['001', '002'], 'Valor': [100.0, 200.0]})


@pytest.fixture
def df_audit_vazia():
    return pd.DataFrame(columns=['Severidade', 'Tipo', 'Linha', 'Coluna', 'Descrição', 'Impacto R$'])


# ── gerar_pdf ─────────────────────────────────────────────────────

class TestGerarPDF:
    def test_gerar_pdf_sem_weasyprint_retorna_false(self, g, tmp_path):
        import sys
        original = sys.modules.get('weasyprint')
        sys.modules['weasyprint'] = None
        try:
            result = g.gerar_pdf('<html></html>', str(tmp_path / 'out.pdf'))
        finally:
            if original is None:
                sys.modules.pop('weasyprint', None)
            else:
                sys.modules['weasyprint'] = original
        assert result is False


# ── _esc e _fmt_brl ───────────────────────────────────────────────

class TestHelpers:
    def test_esc_none_retorna_vazio(self, g):
        assert g._esc(None) == ''

    def test_esc_html_especial(self, g):
        assert '&lt;' in g._esc('<script>')

    def test_fmt_brl_negativo(self, g):
        resultado = g._fmt_brl(-1500.50)
        assert 'R$' in resultado
        assert '-' in resultado

    def test_fmt_brl_invalido_retorna_traco(self, g):
        assert g._fmt_brl('não é número') == '—'
        assert g._fmt_brl(None) == '—'

    def test_badge_none(self, g):
        badge = g._badge(None)
        assert 'badge' in badge

    def test_badge_critica(self, g):
        badge = g._badge('CRÍTICA')
        assert 'critica' in badge

    def test_badge_ok(self, g):
        badge = g._badge('OK')
        assert 'ok' in badge


# ── _secao_diagnostico ────────────────────────────────────────────

class TestSecaoDiagnostico:
    def test_gerar_com_diagnostico(self, g, df_dados, df_audit_vazia):
        diagnostico = {
            'arquivo': 'teste.csv',
            'total_registros': 2,
            'problemas_formato': [
                {'aba': 'Dados', 'coluna': 'Valor', 'severidade': 'ALTA',
                 'descricao': 'Números como texto'},
            ],
        }
        html = g.gerar('teste.csv', df_dados, df_audit_vazia, diagnostico=diagnostico)
        assert 'Problemas de Formato' in html
        assert 'Números como texto' in html

    def test_gerar_sem_diagnostico(self, g, df_dados, df_audit_vazia):
        html = g.gerar('teste.csv', df_dados, df_audit_vazia, diagnostico=None)
        assert isinstance(html, str)


# ── _secao_auditoria com impacto ──────────────────────────────────

class TestSecaoAuditoria:
    def test_auditoria_com_impacto_rs(self, g, df_dados):
        df_audit = pd.DataFrame([{
            'Severidade': 'CRÍTICA',
            'Tipo': 'DUPLICATA',
            'Linha': 5,
            'Coluna': 'NF',
            'Descrição': 'Duplicata em NF',
            'Impacto R$': 1000.0,
        }])
        html = g.gerar('teste.csv', df_dados, df_audit)
        assert 'DUPLICATA' in html
        assert 'R$' in html

    def test_auditoria_linha_como_lista(self, g, df_dados):
        df_audit = pd.DataFrame([{
            'Severidade': 'MÉDIA',
            'Tipo': 'CAMPO_VAZIO',
            'Linha': [3, 4, 5],
            'Coluna': 'Valor',
            'Descrição': 'Campo vazio',
            'Impacto R$': 0,
        }])
        html = g.gerar('teste.csv', df_dados, df_audit)
        assert '3, 4, 5' in html

    def test_auditoria_impacto_invalido_mostra_traco(self, g, df_dados):
        df_audit = pd.DataFrame([{
            'Severidade': 'BAIXA',
            'Tipo': 'OUTLIER',
            'Linha': 2,
            'Coluna': 'Valor',
            'Descrição': 'Outlier',
            'Impacto R$': 'N/A',
        }])
        html = g.gerar('teste.csv', df_dados, df_audit)
        assert '—' in html


# ── _secao_aging ──────────────────────────────────────────────────

class TestSecaoAging:
    def test_aging_correto(self, g, df_dados, df_audit_vazia):
        df_aging = pd.DataFrame([
            {'Faixa_Aging': 'A vencer', 'Quantidade': 3, 'Total_RS': 3000.0, 'Percentual': 60.0},
            {'Faixa_Aging': '1-30 dias', 'Quantidade': 1, 'Total_RS': 1000.0, 'Percentual': 20.0},
            {'Faixa_Aging': '31-60 dias', 'Quantidade': 1, 'Total_RS': 1000.0, 'Percentual': 20.0},
        ])
        html = g.gerar('teste.csv', df_dados, df_audit_vazia, df_aging=df_aging)
        assert 'Aging' in html
        assert 'A vencer' in html

    def test_aging_sem_colunas_obrigatorias(self, g, df_dados, df_audit_vazia):
        df_aging_ruim = pd.DataFrame([{'Faixa': 'x', 'Total': 1}])
        html = g.gerar('teste.csv', df_dados, df_audit_vazia, df_aging=df_aging_ruim)
        assert 'Aging' in html

    def test_aging_faixas_cor(self, g, df_dados, df_audit_vazia):
        df_aging = pd.DataFrame([
            {'Faixa_Aging': 'Acima de 90 dias', 'Quantidade': 2, 'Total_RS': 5000.0, 'Percentual': 100.0},
        ])
        html = g.gerar('teste.csv', df_dados, df_audit_vazia, df_aging=df_aging)
        assert 'bar-critico' in html


# ── _secao_fluxo ──────────────────────────────────────────────────

class TestSecaoFluxo:
    def _make_fluxo(self):
        return pd.DataFrame([
            {'Periodo': '01/2024', 'Receita_RS': 5000.0, 'NFs_Receita': 3,
             'Despesa_RS': 2000.0, 'NFs_Despesa': 2,
             'Resultado_RS': 3000.0, 'Resultado_Pct': 60.0},
            {'Periodo': '02/2024', 'Receita_RS': 4000.0, 'NFs_Receita': 2,
             'Despesa_RS': 4500.0, 'NFs_Despesa': 3,
             'Resultado_RS': -500.0, 'Resultado_Pct': -12.5},
        ])

    def test_fluxo_mensal(self, g, df_dados, df_audit_vazia):
        df_m = self._make_fluxo()
        html = g.gerar('t.csv', df_dados, df_audit_vazia,
                       df_fluxo_mensal=df_m)
        assert 'Fluxo' in html
        assert '01/2024' in html

    def test_fluxo_diario(self, g, df_dados, df_audit_vazia):
        df_d = self._make_fluxo()
        html = g.gerar('t.csv', df_dados, df_audit_vazia,
                       df_fluxo_diario=df_d)
        assert 'Fluxo' in html

    def test_fluxo_anual(self, g, df_dados, df_audit_vazia):
        df_a = self._make_fluxo()
        html = g.gerar('t.csv', df_dados, df_audit_vazia,
                       df_fluxo_anual=df_a)
        assert 'Fluxo' in html

    def test_fluxo_resultado_negativo_cor_vermelha(self, g, df_dados, df_audit_vazia):
        df_m = self._make_fluxo()
        html = g.gerar('t.csv', df_dados, df_audit_vazia, df_fluxo_mensal=df_m)
        assert '#FEE2E2' in html

    def test_fluxo_nenhum_dado_nao_renderiza(self, g, df_dados, df_audit_vazia):
        html = g.gerar('t.csv', df_dados, df_audit_vazia,
                       df_fluxo_diario=None, df_fluxo_mensal=None, df_fluxo_anual=None)
        assert 'Fluxo por Período' not in html
