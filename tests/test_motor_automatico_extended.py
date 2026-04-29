"""
Testes estendidos para motor_automatico.py — cobertura de processar(),
AnalisadorClaudeAPI, carregar_config e helpers internos.
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch

from motor_automatico import (
    ProcessadorArquivo,
    AnalisadorClaudeAPI,
    carregar_config,
)


# ── fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def cfg(tmp_path):
    return {
        'pastas': {
            'saida': str(tmp_path / 'saida'),
            'log':   str(tmp_path / 'log.txt'),
        },
        'colunas': {
            'valor': 'Valor', 'categoria': 'Categoria',
            'data': 'Data', 'vencimento': 'Vencimento',
            'chave': 'NF', 'entidade': 'Cliente',
        },
        'auditoria': {'outlier_desvios': 3.0},
        'email': {'ativo': False},
        'claude_api': {'ativo': False},
        'relatorio': {'titulo': 'Teste', 'empresa': 'Empresa', 'tema': {}},
    }


@pytest.fixture
def proc(cfg):
    return ProcessadorArquivo(cfg)


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / 'dados.csv'
    p.write_text(
        'NF,Valor,Data,Vencimento,Categoria,Cliente\n'
        '001,1000.00,01/01/2024,10/01/2024,RECEITA,Alfa\n'
        '002,-200.00,05/01/2024,15/01/2024,DESPESA OPERACIONAL,Beta\n'
        '003,500.00,10/01/2024,20/01/2024,RECEITA,Gamma\n',
        encoding='utf-8',
    )
    return str(p)


@pytest.fixture
def csv_duplicata(tmp_path):
    p = tmp_path / 'dup.csv'
    p.write_text(
        'NF,Valor,Data,Vencimento,Categoria,Cliente\n'
        '001,1000.00,01/01/2024,10/01/2024,RECEITA,Alfa\n'
        '001,1000.00,01/01/2024,10/01/2024,RECEITA,Alfa\n'
        '002,200.00,05/01/2024,15/01/2024,DESPESA OPERACIONAL,Beta\n',
        encoding='utf-8',
    )
    return str(p)


# ── carregar_config ───────────────────────────────────────────────

class TestCarregarConfig:
    def test_arquivo_inexistente_retorna_vazio(self, tmp_path):
        cfg = carregar_config(str(tmp_path / 'nao_existe.yaml'))
        assert cfg == {}

    def test_yaml_invalido_levanta_system_exit(self, tmp_path):
        p = tmp_path / 'ruim.yaml'
        p.write_text('{chave: [sem fechar', encoding='utf-8')
        with pytest.raises(SystemExit):
            carregar_config(str(p))

    def test_config_valido_carregado(self, tmp_path):
        p = tmp_path / 'cfg.yaml'
        p.write_text('pastas:\n  entrada: x\n  saida: y\n', encoding='utf-8')
        cfg = carregar_config(str(p))
        assert cfg['pastas']['entrada'] == 'x'

    def test_falhar_em_config_invalida_levanta_system_exit(self, tmp_path):
        p = tmp_path / 'inv.yaml'
        p.write_text(
            'pastas:\n  entrada: ""\n  saida: ""\n'
            'validacao:\n  falhar_em_config_invalida: true\n',
            encoding='utf-8',
        )
        with pytest.raises(SystemExit):
            carregar_config(str(p))


# ── AnalisadorClaudeAPI ───────────────────────────────────────────

class TestAnalisadorClaudeAPI:
    def test_inativo_retorna_vazio(self):
        api = AnalisadorClaudeAPI({'claude_api': {'ativo': False}})
        assert api.analisar('briefing') == ''

    def test_ativo_sem_api_key_desativa(self):
        with patch.dict('os.environ', {}, clear=True):
            api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
        assert not api.ativo

    def test_ativo_sem_pacote_anthropic_desativa(self):
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key123'}):
            with patch.dict('sys.modules', {'anthropic': None}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
        assert not api.ativo

    def test_ativo_com_key_inicializa(self, tmp_path):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key123'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
        assert api.ativo
        assert api._client == mock_client

    def test_analisar_retorna_texto(self):
        mock_anthropic = MagicMock()
        mock_client    = MagicMock()
        mock_bloco     = MagicMock()
        mock_bloco.type = 'text'
        mock_bloco.text = 'análise gerada'
        mock_client.messages.create.return_value.content = [mock_bloco]
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key123'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
                result = api.analisar('briefing')
        assert result == 'análise gerada'

    def test_analisar_content_vazio_retorna_string_vazia(self):
        mock_anthropic = MagicMock()
        mock_client    = MagicMock()
        mock_client.messages.create.return_value.content = []
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key123'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
                assert api.analisar('x') == ''

    def test_analisar_erro_autenticacao_retorna_vazio(self):
        mock_anthropic = MagicMock()
        mock_client    = MagicMock()
        mock_anthropic.AuthenticationError = Exception
        mock_anthropic.RateLimitError = Exception
        mock_anthropic.APIConnectionError = Exception
        mock_anthropic.APIError = Exception
        mock_client.messages.create.side_effect = mock_anthropic.AuthenticationError('chave inválida')
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key123'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
                assert api.analisar('x') == ''

    def test_prompt_sistema_lido_do_arquivo(self, tmp_path):
        prompt_file = tmp_path / 'prompt.md'
        prompt_file.write_text('Você é analista.', encoding='utf-8')
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = MagicMock()

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key123'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({
                    'claude_api': {'ativo': True, 'prompt_sistema': str(prompt_file)}
                })
        assert 'analista' in api._system_prompt


# ── ProcessadorArquivo.processar() ───────────────────────────────

class TestProcessarPipeline:
    def test_processar_csv_ok(self, proc, csv_file):
        res = proc.processar(csv_file)
        assert res['status'] in ('OK', 'ALERTA', 'AVISO')
        assert res['html'] is not None
        assert Path(res['html']).exists()
        assert res['xlsx'] is not None
        assert Path(res['xlsx']).exists()

    def test_processar_csv_cria_html(self, proc, csv_file):
        res = proc.processar(csv_file)
        html_content = Path(res['html']).read_text(encoding='utf-8')
        assert '<!DOCTYPE html>' in html_content

    def test_processar_csv_cria_xlsx(self, proc, csv_file):
        res = proc.processar(csv_file)
        assert res['xlsx'].endswith('.xlsx')

    def test_processar_com_duplicatas_status_alerta(self, proc, csv_duplicata):
        res = proc.processar(csv_duplicata)
        assert res['criticos'] > 0
        assert res['status'] == 'ALERTA'
        assert res['acoes'] is not None

    def test_processar_arquivo_inexistente_retorna_erro(self, proc):
        res = proc.processar('/nao/existe/arquivo.csv')
        assert res['status'] == 'ERRO'
        assert res['erro'] is not None

    def test_processar_extensao_invalida_levanta_ou_retorna_erro(self, proc, tmp_path):
        p = tmp_path / 'dados.txt'
        p.write_text('col1,col2\na,b\n')
        try:
            res = proc.processar(str(p))
            assert res['status'] == 'ERRO'
        except ValueError:
            pass  # _validar_caminho_arquivo levanta ValueError antes do try-except

    def test_processar_retorna_padrao(self, proc, csv_file):
        res = proc.processar(csv_file)
        assert 'padrao' in res
        assert Path(res['padrao']).exists()

    def test_processar_csv_vazio_retorna_erro(self, proc, tmp_path):
        p = tmp_path / 'vazio.csv'
        p.write_text('', encoding='utf-8')
        res = proc.processar(str(p))
        assert res['status'] == 'ERRO'

    def test_processar_com_claude_ativo_envia_briefing(self, cfg, tmp_path, csv_file):
        mock_anthropic = MagicMock()
        mock_bloco = MagicMock(); mock_bloco.type = 'text'; mock_bloco.text = 'análise'
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [mock_bloco]
        mock_anthropic.Anthropic.return_value = mock_client
        mock_anthropic.AuthenticationError = Exception
        mock_anthropic.RateLimitError = Exception
        mock_anthropic.APIConnectionError = Exception
        mock_anthropic.APIError = Exception

        cfg['claude_api'] = {'ativo': True}
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key123'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                proc = ProcessadorArquivo(cfg)
                res = proc.processar(csv_file)
                assert res['analise'] is not None


# ── Helpers internos ──────────────────────────────────────────────

class TestHelpersInternos:
    def test_calcular_aging_retorna_dataframe(self, proc, csv_file):
        df = pd.read_csv(csv_file)
        result = proc._calcular_aging(df, 'Vencimento', 'Valor')
        assert result is not None

    def test_calcular_aging_sem_coluna_retorna_none(self, proc):
        df = pd.DataFrame({'Valor': [100]})
        assert proc._calcular_aging(df, 'Vencimento', 'Valor') is None

    def test_construir_dre_retorna_dataframe(self, proc, csv_file):
        df = pd.read_csv(csv_file)
        result = proc._construir_dre(df, 'Categoria', 'Valor')
        assert result is not None

    def test_construir_dre_sem_coluna_retorna_none(self, proc):
        df = pd.DataFrame({'Valor': [100]})
        assert proc._construir_dre(df, 'Categoria', 'Valor') is None

    def test_calcular_pareto_retorna_dataframe(self, proc, csv_file):
        df = pd.read_csv(csv_file)
        result = proc._calcular_pareto(df, 'Cliente', 'Valor')
        assert result is not None

    def test_calcular_pareto_sem_coluna_retorna_none(self, proc):
        df = pd.DataFrame({'Valor': [100]})
        assert proc._calcular_pareto(df, 'Cliente', 'Valor') is None

    def test_calcular_ticket_retorna_dataframe(self, proc, csv_file):
        df = pd.read_csv(csv_file)
        result = proc._calcular_ticket(df, 'Valor', 'Cliente')
        assert result is not None

    def test_calcular_ticket_sem_coluna_retorna_none(self, proc):
        df = pd.DataFrame({'Outra': [1]})
        assert proc._calcular_ticket(df, 'Valor', 'Cliente') is None

    def test_montar_metricas_com_valor(self, proc, csv_file):
        df = pd.read_csv(csv_file)
        df_audit = pd.DataFrame(columns=['Severidade'])
        metricas = proc._montar_metricas(df, df_audit, 'Valor', 0)
        assert 'Total Geral' in metricas
        assert 'Ticket Médio' in metricas
        assert 'Total de Registros' in metricas

    def test_gerar_relatorio_acoes_retorna_html(self, proc):
        resultado = {'arquivo_origem': 'teste.csv', 'criticos': 1, 'total_problemas': 2}
        df_audit = pd.DataFrame([{
            'Severidade': 'CRÍTICA', 'Tipo': 'DUPLICATA',
            'Coluna': 'NF', 'Linha': 5, 'Descrição': 'Duplicata',
        }])
        html = proc._gerar_relatorio_acoes(resultado, df_audit)
        assert '<!DOCTYPE html>' in html
        assert 'DUPLICATA' in html

    def test_gerar_relatorio_acoes_linha_lista(self, proc):
        resultado = {'arquivo_origem': 'teste.csv', 'criticos': 0, 'total_problemas': 1}
        df_audit = pd.DataFrame([{
            'Severidade': 'MÉDIA', 'Tipo': 'CAMPO_VAZIO',
            'Coluna': 'Valor', 'Linha': [3, 4, 5], 'Descrição': 'Vazio',
        }])
        html = proc._gerar_relatorio_acoes(resultado, df_audit)
        assert '3, 4, 5' in html

    def test_normalizar_colunas_sem_erp_retorna_df(self, proc, csv_file):
        df = pd.read_csv(csv_file)
        result = proc._normalizar_colunas(df)
        assert isinstance(result, pd.DataFrame)

    def test_coletar_dups_preenche_lista(self, proc, csv_file):
        df = pd.read_csv(csv_file).copy()
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        lista = []
        proc._coletar_dups(df, 'NF', 'Dados', lista)
        assert len(lista) > 0
        assert lista[0]['tipo'] == 'DUPLICATA'

    def test_coletar_outliers_preenche_lista(self, proc):
        # 10 valores normais + 1 extremo para garantir detecção
        normais = [100.0] * 10
        df = pd.DataFrame({'Valor': normais + [1_000_000.0], 'NF': [str(i) for i in range(11)]})
        lista = []
        proc._coletar_outliers(df, 'Valor', 'Aba', lista)
        assert len(lista) > 0


# ── Email SMTP_SSL porta 465 ──────────────────────────────────────

class TestEmailSMTPSSL:
    def test_enviar_email_porta_465_usa_smtp_ssl(self, cfg, tmp_path):
        cfg['email'] = {
            'ativo': True,
            'smtp_servidor': 'smtp.gmail.com',
            'smtp_porta': 465,
            'remetente': 'from@example.com',
            'destinatarios': ['to@example.com'],
        }
        proc = ProcessadorArquivo(cfg)
        resultado = {'arquivo_origem': 'a.csv', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
        df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])

        chamadas = []

        class FakeSMTP_SSL:
            def __init__(self, host, port, context=None, timeout=None):
                chamadas.append({'class': 'SSL', 'host': host, 'port': port})
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def login(self, *a): pass
            def sendmail(self, *a): pass

        with patch('smtplib.SMTP_SSL', FakeSMTP_SSL), \
             patch.dict('os.environ', {'EMAIL_SENHA': 'secret'}):
            proc._enviar_email(resultado, df_audit)

        assert chamadas and chamadas[0]['class'] == 'SSL'
        assert chamadas[0]['port'] == 465

    def test_enviar_email_porta_587_usa_starttls(self, cfg, tmp_path):
        cfg['email'] = {
            'ativo': True,
            'smtp_servidor': 'smtp.example.com',
            'smtp_porta': 587,
            'remetente': 'from@example.com',
            'destinatarios': ['to@example.com'],
        }
        proc = ProcessadorArquivo(cfg)
        resultado = {'arquivo_origem': 'a.csv', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
        df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])

        starttls_chamado = []

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, context=None): starttls_chamado.append(True)
            def login(self, *a): pass
            def sendmail(self, *a): pass

        with patch('smtplib.SMTP', FakeSMTP), \
             patch.dict('os.environ', {'EMAIL_SENHA': 'secret'}):
            proc._enviar_email(resultado, df_audit)

        assert starttls_chamado

    def test_enviar_email_erro_smtp_nao_propaga(self, cfg):
        cfg['email'] = {
            'ativo': True,
            'smtp_servidor': 'smtp.example.com',
            'smtp_porta': 587,
            'remetente': 'from@example.com',
            'destinatarios': ['to@example.com'],
        }
        proc = ProcessadorArquivo(cfg)
        resultado = {'arquivo_origem': 'a.csv', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
        df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])

        with patch('smtplib.SMTP', side_effect=ConnectionRefusedError), \
             patch.dict('os.environ', {'EMAIL_SENHA': 'secret'}):
            proc._enviar_email(resultado, df_audit)  # não deve levantar exceção


# ── _validar_caminho_arquivo ──────────────────────────────────────

class TestValidarCaminho:
    def test_extensao_invalida_levanta_value_error(self):
        with pytest.raises(ValueError, match='não suportada'):
            ProcessadorArquivo._validar_caminho_arquivo('/tmp/arquivo.doc')

    def test_arquivo_valido_retorna_path(self, tmp_path):
        p = tmp_path / 'dados.csv'
        p.write_text('a,b\n1,2\n')
        result = ProcessadorArquivo._validar_caminho_arquivo(str(p))
        assert result.suffix == '.csv'
