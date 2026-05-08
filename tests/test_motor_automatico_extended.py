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

    def test_arquivo_muito_grande_levanta_value_error(self, tmp_path):
        p = tmp_path / 'grande.csv'
        p.write_text('a,b\n1,2\n')
        with pytest.raises(ValueError, match='grande'):
            ProcessadorArquivo._validar_caminho_arquivo(str(p), max_bytes=1)


# ── AnalisadorClaudeAPI — branches faltando ───────────────────────

class TestAnalisadorClaudeAPIBranches:
    def _make_api(self, mock_anthropic):
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                return AnalisadorClaudeAPI({'claude_api': {'ativo': True}})

    def test_prompt_oserror_usa_padrao(self, tmp_path):
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = MagicMock()
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({
                    'claude_api': {'ativo': True, 'prompt_sistema': '/nao/existe.md'}
                })
        assert 'analista' in api._system_prompt.lower()

    def test_analisar_bloco_sem_tipo_text_retorna_vazio(self):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        bloco = MagicMock()
        bloco.type = 'tool_use'
        mock_client.messages.create.return_value.content = [bloco]
        mock_anthropic.Anthropic.return_value = mock_client
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
                result = api.analisar('briefing')
        assert result == ''

    def test_analisar_rate_limit_retorna_vazio(self):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AuthenticationError = type('AuthErr', (Exception,), {})
        mock_anthropic.RateLimitError = type('RateErr', (Exception,), {})
        mock_anthropic.APIConnectionError = type('ConnErr', (Exception,), {})
        mock_anthropic.APIError = type('APIErr', (Exception,), {})
        mock_client.messages.create.side_effect = mock_anthropic.RateLimitError('rate limit')
        mock_anthropic.Anthropic.return_value = mock_client
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
                assert api.analisar('x') == ''

    def test_analisar_connection_error_retorna_vazio(self):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AuthenticationError = type('AuthErr', (Exception,), {})
        mock_anthropic.RateLimitError = type('RateErr', (Exception,), {})
        mock_anthropic.APIConnectionError = type('ConnErr', (Exception,), {})
        mock_anthropic.APIError = type('APIErr', (Exception,), {})
        mock_client.messages.create.side_effect = mock_anthropic.APIConnectionError('conn')
        mock_anthropic.Anthropic.return_value = mock_client
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
                assert api.analisar('x') == ''

    def test_analisar_api_error_retorna_vazio(self):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AuthenticationError = type('AuthErr', (Exception,), {})
        mock_anthropic.RateLimitError = type('RateErr', (Exception,), {})
        mock_anthropic.APIConnectionError = type('ConnErr', (Exception,), {})
        mock_anthropic.APIError = type('APIErr', (Exception,), {})
        mock_client.messages.create.side_effect = mock_anthropic.APIError('err')
        mock_anthropic.Anthropic.return_value = mock_client
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'key'}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
                api = AnalisadorClaudeAPI({'claude_api': {'ativo': True}})
                assert api.analisar('x') == ''


# ── ProcessadorArquivo — exception paths ──────────────────────────

class TestProcessadorExceptionPaths:
    def test_empty_data_error_retorna_erro(self, cfg):
        proc = ProcessadorArquivo(cfg)
        with patch('motor_automatico.Leitor.ler_arquivo') as mock:
            import pandas as _pd
            mock.side_effect = _pd.errors.EmptyDataError('vazio')
            res = proc.processar('/fake/dados.csv')
        assert res['status'] == 'ERRO'

    def test_runtime_error_retorna_erro(self, cfg):
        proc = ProcessadorArquivo(cfg)
        with patch('motor_automatico.Leitor.ler_arquivo') as mock:
            mock.side_effect = RuntimeError('falha crítica')
            res = proc.processar('/fake/dados.csv')
        assert res['status'] == 'ERRO'

    def test_normalizar_colunas_com_erp(self, cfg):
        proc = ProcessadorArquivo(cfg)
        df = pd.DataFrame({'DocNum': ['001'], 'CardName': ['Alfa'], 'DocTotal': [100.0]})
        with patch('base_conhecimento.detectar_erp', return_value='SAP_B1'), \
             patch('base_conhecimento.normalizar_colunas', return_value=df):
            result = proc._normalizar_colunas(df)
        assert isinstance(result, pd.DataFrame)

    def test_calcular_aging_exception_retorna_none(self, cfg):
        proc = ProcessadorArquivo(cfg)
        df = pd.DataFrame({'Vencimento': ['2024-01-01'], 'Valor': [100.0]})
        with patch('motor_automatico.AnalistaFinanceiro.calcular_aging',
                   side_effect=ValueError('dados inválidos')):
            result = proc._calcular_aging(df, 'Vencimento', 'Valor')
        assert result is None

    def test_construir_dre_exception_retorna_none(self, cfg):
        proc = ProcessadorArquivo(cfg)
        df = pd.DataFrame({'Categoria': [None], 'Valor': [None]})
        with patch('motor_automatico.AnalistaFinanceiro.construir_dre', side_effect=KeyError('x')):
            result = proc._construir_dre(df, 'Categoria', 'Valor')
        assert result is None

    def test_calcular_pareto_exception_retorna_none(self, cfg):
        proc = ProcessadorArquivo(cfg)
        df = pd.DataFrame({'Cliente': ['X'], 'Valor': [0.0]})
        with patch('motor_automatico.AnalistaComercial.pareto', side_effect=ZeroDivisionError):
            result = proc._calcular_pareto(df, 'Cliente', 'Valor')
        assert result is None

    def test_calcular_ticket_exception_retorna_none(self, cfg):
        proc = ProcessadorArquivo(cfg)
        df = pd.DataFrame({'Valor': [100.0]})
        with patch('motor_automatico.AnalistaComercial.ticket_medio', side_effect=ValueError):
            result = proc._calcular_ticket(df, 'Valor', 'Cliente')
        assert result is None

    def test_log_handler_nao_duplicado(self, cfg):
        proc1 = ProcessadorArquivo(cfg)
        proc2 = ProcessadorArquivo(cfg)
        assert proc2._log_handler is None


# ── _gerar_briefing — branches ────────────────────────────────────

class TestGerarBriefing:
    def test_briefing_com_problemas_formato(self, proc):
        df = pd.DataFrame({'NF': ['001'], 'Valor': [100.0]})
        df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Linha', 'Coluna', 'Descrição'])
        diag = {
            'arquivo': 'teste.csv', 'total_registros': 1,
            'problemas_formato': [{'severidade': 'ALTA', 'descricao': 'Números como texto'}],
        }
        briefing = proc._gerar_briefing(df, diag, df_audit, None, None, None, None)
        assert 'Números como texto' in briefing
        assert 'ALTA' in briefing

    def test_briefing_com_auditoria_problemas(self, proc):
        df = pd.DataFrame({'NF': ['001'], 'Valor': [100.0]})
        df_audit = pd.DataFrame([{
            'Severidade': 'CRÍTICA', 'Tipo': 'DUPLICATA',
            'Linha': 2, 'Coluna': 'NF', 'Descrição': 'Duplicata em NF',
        }])
        diag = {'arquivo': 'teste.csv', 'total_registros': 1, 'problemas_formato': []}
        briefing = proc._gerar_briefing(df, diag, df_audit, None, None, None, None)
        assert 'Duplicata em NF' in briefing
        assert 'CRÍTICA' in briefing


# ── _enviar_email — branches adicionais ──────────────────────────

class TestEnviarEmailBranches:
    def _cfg_email(self, senha=''):
        return {
            'ativo': True, 'smtp_servidor': 'smtp.test.com', 'smtp_porta': 587,
            'remetente': 'a@b.com', 'senha': senha, 'destinatarios': ['d@b.com'],
        }

    def test_senha_vazia_nao_envia(self, cfg):
        cfg['email'] = self._cfg_email(senha='')
        proc = ProcessadorArquivo(cfg)
        resultado = {'arquivo_origem': 'x.csv', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
        df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])
        with patch('smtplib.SMTP') as mock_smtp, \
             patch.dict('os.environ', {}, clear=True):
            proc._enviar_email(resultado, df_audit)
            mock_smtp.assert_not_called()

    def test_email_com_criticos_monta_html(self, cfg):
        cfg['email'] = self._cfg_email(senha='s')
        proc = ProcessadorArquivo(cfg)
        resultado = {'arquivo_origem': 'x.csv', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
        df_audit = pd.DataFrame([{'Severidade': 'CRÍTICA', 'Tipo': 'DUPLICATA', 'Descrição': 'Dup'}])
        chamadas = []
        class FakeSMTP:
            def __init__(self, *a, **kw): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, **kw): pass
            def login(self, *a): pass
            def sendmail(self, *a): chamadas.append(True)
        with patch('smtplib.SMTP', FakeSMTP), \
             patch.dict('os.environ', {'EMAIL_SENHA': 's'}):
            proc._enviar_email(resultado, df_audit)
        assert chamadas

    def test_smtp_auth_error_nao_rejeita(self, cfg):
        import smtplib
        cfg['email'] = self._cfg_email(senha='wrong')
        proc = ProcessadorArquivo(cfg)
        resultado = {'arquivo_origem': 'x.csv', 'total_problemas': 0, 'criticos': 0, 'timestamp': '20240101'}
        df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])
        class FakeSMTP:
            def __init__(self, *a, **kw): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, **kw): pass
            def login(self, *a): raise smtplib.SMTPAuthenticationError(535, b'Auth failed')
            def sendmail(self, *a): pass
        with patch('smtplib.SMTP', FakeSMTP), \
             patch.dict('os.environ', {'EMAIL_SENHA': 'wrong'}):
            proc._enviar_email(resultado, df_audit)

    def test_email_config_incompleta_keyerror(self, cfg):
        cfg['email'] = {'ativo': True, 'destinatarios': ['d@b.com']}
        proc = ProcessadorArquivo(cfg)
        resultado = {'arquivo_origem': 'x.csv', 'total_problemas': 0, 'criticos': 0, 'timestamp': '20240101'}
        df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])
        with patch.dict('os.environ', {'EMAIL_SENHA': 'x'}):
            proc._enviar_email(resultado, df_audit)


# ── ObservadorPasta ───────────────────────────────────────────────

class TestObservadorPasta:
    def test_varrer_processa_arquivo_novo(self, cfg, tmp_path):
        from motor_automatico import ObservadorPasta
        pasta = tmp_path / 'entrada'
        pasta.mkdir()
        arq = pasta / 'dados.csv'
        arq.write_text('NF,Valor\n001,100\n', encoding='utf-8')
        proc = ProcessadorArquivo(cfg)
        obs = ObservadorPasta(proc, str(pasta))
        obs.varrer_uma_vez()
        obs.varrer_uma_vez()
        assert any(name == arq.name for name, _ in obs._vistos)

    def test_varrer_nao_reprocessa_arquivo_visto(self, cfg, tmp_path):
        from motor_automatico import ObservadorPasta
        pasta = tmp_path / 'entrada'
        pasta.mkdir()
        arq = pasta / 'dados.csv'
        arq.write_text('NF,Valor\n001,100\n', encoding='utf-8')
        proc = ProcessadorArquivo(cfg)
        obs = ObservadorPasta(proc, str(pasta))
        obs.varrer_uma_vez()
        obs.varrer_uma_vez()
        contagem_inicial = len(obs._vistos)
        obs.varrer_uma_vez()
        assert len(obs._vistos) == contagem_inicial

    def test_monitorar_para_no_keyboard_interrupt(self, cfg, tmp_path):
        from motor_automatico import ObservadorPasta
        pasta = tmp_path / 'entrada'
        pasta.mkdir()
        proc = ProcessadorArquivo(cfg)
        obs = ObservadorPasta(proc, str(pasta))
        with patch.object(obs, 'varrer_uma_vez', side_effect=KeyboardInterrupt):
            obs.monitorar(intervalo=0)
