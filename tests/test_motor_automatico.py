"""
Testes para motor_automatico.py — ProcessadorArquivo e helpers

Execução:
    pytest tests/test_motor_automatico.py -v
"""

import logging
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from motor_automatico import ProcessadorArquivo


@pytest.fixture
def config_basico(tmp_path):
    return {
        "pastas": {
            "saida": str(tmp_path / "saida"),
            "log": str(tmp_path / "log.txt"),
        },
        "colunas": {
            "valor": "Valor",
            "categoria": "Categoria",
            "data": "Data",
            "vencimento": "Vencimento",
            "chave": "NF",
            "entidade": "Cliente",
        },
        "auditoria": {"outlier_desvios": 3.0},
        "email": {"ativo": False},
    }


@pytest.fixture
def processador(config_basico):
    return ProcessadorArquivo(config_basico)


# ── Testes de processamento de arquivo ────────────────────────────


def test_processar_arquivo_inexistente(processador):
    resultado = processador.processar("/caminho/que/nao/existe.xlsx")
    assert resultado["status"] == "ERRO"
    assert resultado["erro"] is not None


def test_processar_dados_vazios(processador):
    with patch("motor_automatico.Leitor.ler_arquivo") as mock_ler:
        mock_ler.return_value = {
            "dados": {},
            "diagnostico": {"arquivo": "vazio.xlsx", "total_registros": 0, "problemas_formato": []},
        }
        resultado = processador.processar("vazio.xlsx")
    assert resultado["status"] == "ERRO"
    assert resultado["erro"] is not None


# ── Testes de envio de email ──────────────────────────────────────


def test_enviar_email_desativado(processador):
    resultado_fake = {"arquivo_origem": "x.xlsx", "total_problemas": 1, "criticos": 1, "timestamp": "20240101"}
    df_audit = pd.DataFrame(columns=["Severidade", "Tipo", "Descrição"])
    with patch("smtplib.SMTP") as mock_smtp:
        processador._enviar_email(resultado_fake, df_audit)
        mock_smtp.assert_not_called()


def test_enviar_email_sem_destinatarios(config_basico):
    cfg = dict(config_basico)
    cfg["email"] = {"ativo": True, "smtp_servidor": "smtp.test.com", "remetente": "a@b.com", "destinatarios": []}
    proc = ProcessadorArquivo(cfg)
    resultado_fake = {"arquivo_origem": "x.xlsx", "total_problemas": 1, "criticos": 1, "timestamp": "20240101"}
    df_audit = pd.DataFrame(columns=["Severidade", "Tipo", "Descrição"])
    with patch("smtplib.SMTP") as mock_smtp:
        proc._enviar_email(resultado_fake, df_audit)
        mock_smtp.assert_not_called()


def test_enviar_email_credencial_warning_via_config(config_basico, caplog):
    cfg = dict(config_basico)
    cfg["email"] = {
        "ativo": True,
        "smtp_servidor": "smtp.test.com",
        "smtp_porta": 587,
        "remetente": "a@b.com",
        "senha": "senha_secreta_config",
        "destinatarios": ["dest@exemplo.com"],
    }
    proc = ProcessadorArquivo(cfg)
    resultado_fake = {"arquivo_origem": "x.xlsx", "total_problemas": 1, "criticos": 1, "timestamp": "20240101"}
    df_audit = pd.DataFrame(columns=["Severidade", "Tipo", "Descrição"])
    with patch("smtplib.SMTP") as mock_smtp, patch.dict("os.environ", {}, clear=True):
        mock_smtp.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        with caplog.at_level(logging.WARNING, logger="motor_automatico"):
            proc._enviar_email(resultado_fake, df_audit)
    assert any("config.yaml" in rec.message for rec in caplog.records)


def test_enviar_email_smtp_timeout_configurado(config_basico):
    cfg = dict(config_basico)
    cfg["email"] = {
        "ativo": True,
        "smtp_servidor": "smtp.test.com",
        "smtp_porta": 587,
        "remetente": "a@b.com",
        "senha": "qualquer",
        "destinatarios": ["dest@exemplo.com"],
    }
    proc = ProcessadorArquivo(cfg)
    resultado_fake = {"arquivo_origem": "x.xlsx", "total_problemas": 1, "criticos": 1, "timestamp": "20240101"}
    df_audit = pd.DataFrame(columns=["Severidade", "Tipo", "Descrição"])
    chamadas = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            chamadas.append({"host": host, "port": port, "timeout": timeout})

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            pass

        def login(self, *a):
            pass

        def sendmail(self, *a):
            pass

    with patch("smtplib.SMTP", FakeSMTP), patch.dict("os.environ", {"EMAIL_SENHA": "env_senha"}):
        proc._enviar_email(resultado_fake, df_audit)

    assert chamadas, "SMTP não foi chamado"
    assert chamadas[0]["timeout"] == 10


# ── Validação de caminho e magic bytes ───────────────────────────


def test_validar_caminho_extensao_invalida():
    with pytest.raises(ValueError, match="Extensão"):
        ProcessadorArquivo._validar_caminho_arquivo("arquivo.exe")


def test_validar_magic_bytes_csv_pula_validacao(tmp_path):
    f = tmp_path / "dados.csv"
    f.write_text("NF,Valor\n001,100\n", encoding="utf-8")
    ProcessadorArquivo._validar_magic_bytes(f)  # CSV: sem assinatura binária


def test_validar_magic_bytes_xlsx_invalido_levanta(tmp_path):
    f = tmp_path / "dados.xlsx"
    f.write_bytes(b"CONTEUDO_ERRADO\x00\x00\x00")
    with pytest.raises(ValueError, match="não corresponde"):
        ProcessadorArquivo._validar_magic_bytes(f)


def test_validar_magic_bytes_xlsx_correto_nao_levanta(tmp_path):
    f = tmp_path / "dados.xlsx"
    f.write_bytes(b"PK\x03\x04" + b"\x00" * 20)
    ProcessadorArquivo._validar_magic_bytes(f)


# ── CSV injection sanitization ────────────────────────────────────


def test_sanitizar_csv_injection_prefixos():
    df = pd.DataFrame({"A": ["=CMD()", "+fórmula", "-100", "@user", "seguro"]})
    result = ProcessadorArquivo._sanitizar_csv_injection(df)
    assert result["A"].iloc[0] == "'=CMD()"
    assert result["A"].iloc[1] == "'+fórmula"
    assert result["A"].iloc[2] == "'-100"
    assert result["A"].iloc[3] == "'@user"
    assert result["A"].iloc[4] == "seguro"


def test_sanitizar_csv_injection_numericos_nao_afetados():
    df = pd.DataFrame({"Valor": [100.0, -50.0, 0.0]})
    result = ProcessadorArquivo._sanitizar_csv_injection(df)
    assert list(result["Valor"]) == [100.0, -50.0, 0.0]


# ── carregar_config ───────────────────────────────────────────────


def test_carregar_config_sem_arquivo(tmp_path):
    from motor_automatico import carregar_config

    cfg = carregar_config(str(tmp_path / "nao_existe.yaml"))
    assert cfg == {}


def test_carregar_config_com_arquivo_valido(tmp_path):
    from motor_automatico import carregar_config

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("pastas:\n  saida: saida/\nemail:\n  ativo: false\n", encoding="utf-8")
    cfg = carregar_config(str(cfg_file))
    assert cfg.get("email", {}).get("ativo") is False


# ── Integração: pipeline completo via processar() ─────────────────


def test_processar_csv_completo(tmp_path):
    """Cobre o pipeline completo — processar(), helpers internos e geração de relatórios."""
    csv_file = tmp_path / "lancamentos.csv"
    csv_file.write_text(
        "NF,Data,Vencimento,Valor,Categoria,Cliente\n"
        "001,01/01/2024,31/01/2024,1000.00,RECEITA,Cliente A\n"
        "002,15/01/2024,14/02/2024,-500.00,DESPESA,Fornecedor B\n"
        "003,20/01/2024,19/02/2024,2000.00,RECEITA,Cliente C\n"
        "004,25/01/2024,24/02/2024,-300.00,ALUGUEL,Imobiliária D\n",
        encoding="utf-8",
    )
    cfg = {
        "pastas": {
            "saida": str(tmp_path / "saida"),
            "log": str(tmp_path / "log.txt"),
        },
        "email": {"ativo": False},
    }
    proc = ProcessadorArquivo(cfg)
    resultado = proc.processar(str(csv_file))
    assert resultado["status"] in ("OK", "ALERTA")
    assert resultado["erro"] is None
    assert resultado["html"] is not None


def test_processar_csv_com_duplicatas_gera_relatorio_acoes(tmp_path):
    """Duplicatas disparam _gerar_relatorio_acoes (cobrir linhas de HTML de ações)."""
    csv_file = tmp_path / "dups.csv"
    csv_file.write_text(
        "NF,Data,Vencimento,Valor,Categoria,Cliente\n"
        "001,01/01/2024,31/01/2024,1000.00,RECEITA,Cliente A\n"
        "001,01/01/2024,31/01/2024,1000.00,RECEITA,Cliente A\n"
        "002,15/01/2024,14/02/2024,500.00,DESPESA,Fornecedor B\n",
        encoding="utf-8",
    )
    cfg = {
        "pastas": {
            "saida": str(tmp_path / "saida"),
            "log": str(tmp_path / "log.txt"),
        },
        "email": {"ativo": False},
    }
    proc = ProcessadorArquivo(cfg)
    resultado = proc.processar(str(csv_file))
    assert resultado["total_problemas"] > 0
