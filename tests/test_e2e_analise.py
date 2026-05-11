"""
E2E functional tests: upload CSV and verify analysis results.

Run with:
    pytest tests/test_e2e_analise.py -m e2e

Requires playwright:
    pip install -r requirements-e2e.txt
    playwright install chromium
"""
import os
import pytest

FIXTURE_CSV = os.path.join(os.path.dirname(__file__), "fixtures", "sample_financeiro.csv")
BASE_URL = "http://localhost:8765/index.html"


def _upload_and_analyse(page):
    """Helper: load page, upload CSV, confirm columns and run analysis."""
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # Upload CSV via file input
    page.set_input_files("#file-input", FIXTURE_CSV)

    # Wait for column config panel to appear
    page.wait_for_selector("#col-config", state="visible", timeout=5000)

    # Click the analyse button
    btn = page.locator("button.btn-analisar")
    btn.wait_for(state="visible", timeout=5000)
    btn.click()

    # Wait for dashboard to appear
    page.wait_for_selector("#dashboard", state="visible", timeout=10000)


@pytest.mark.e2e
def test_upload_csv_mostra_config_colunas(e2e_page):
    """Após upload de CSV, o painel de configuração de colunas aparece."""
    e2e_page.goto(BASE_URL)
    e2e_page.wait_for_load_state("networkidle")
    e2e_page.set_input_files("#file-input", FIXTURE_CSV)
    e2e_page.wait_for_selector("#col-config", state="visible", timeout=5000)
    assert e2e_page.locator("#col-config").is_visible()


@pytest.mark.e2e
def test_analise_mostra_kpis(e2e_page):
    """Após análise, os cards de KPI ficam visíveis com valores."""
    _upload_and_analyse(e2e_page)
    kpis = e2e_page.locator("#kpis")
    assert kpis.is_visible(), "Seção de KPIs não apareceu após análise"
    # Verifica que tem pelo menos um valor de receita
    receita = e2e_page.locator("#kpi-receita")
    assert receita.count() > 0, "KPI de receita não encontrado"
    assert receita.inner_text() != "", "KPI de receita está vazio"


@pytest.mark.e2e
def test_analise_mostra_aging(e2e_page):
    """Após análise, o card de aging aparece."""
    _upload_and_analyse(e2e_page)
    aging = e2e_page.locator("#card-aging")
    assert aging.is_visible(), "Card de aging não apareceu"


@pytest.mark.e2e
def test_analise_mostra_pareto(e2e_page):
    """Após análise, o conteúdo Pareto aparece com pelo menos uma linha."""
    _upload_and_analyse(e2e_page)
    pareto = e2e_page.locator("#pareto-content")
    assert pareto.is_visible(), "Conteúdo Pareto não apareceu"
    # Deve ter pelo menos uma linha de entidade
    rows = e2e_page.locator("#pareto-content tr")
    assert rows.count() > 0, "Tabela Pareto sem linhas"


@pytest.mark.e2e
def test_analise_mostra_dre(e2e_page):
    """Após análise, o card DRE aparece."""
    _upload_and_analyse(e2e_page)
    dre = e2e_page.locator("#card-dre")
    assert dre.is_visible(), "Card de DRE não apareceu"


@pytest.mark.e2e
def test_analise_mostra_tabela_dados(e2e_page):
    """Após análise, a tabela de dados brutos mostra as 15 linhas do CSV."""
    _upload_and_analyse(e2e_page)
    rows = e2e_page.locator("#tbody-dados tr")
    assert rows.count() == 15, f"Esperado 15 linhas, encontrado {rows.count()}"


@pytest.mark.e2e
def test_filtro_tabela(e2e_page):
    """O campo de busca filtra as linhas da tabela de dados."""
    _upload_and_analyse(e2e_page)
    search = e2e_page.locator("#busca")
    search.fill("Alpha")
    e2e_page.wait_for_timeout(400)
    rows = e2e_page.locator("#tbody-dados tr")
    # "Empresa Alpha" aparece em 3 linhas do fixture
    assert 1 <= rows.count() < 15, (
        f"Filtro não funcionou: {rows.count()} linhas (esperado entre 1 e 14)"
    )


@pytest.mark.e2e
def test_exportar_json(e2e_page):
    """O botão exportar JSON dispara download de arquivo .json."""
    _upload_and_analyse(e2e_page)
    btn = e2e_page.locator("button[onclick='exportarJSON()']")
    if btn.count() == 0:
        pytest.skip("Botão exportarJSON não encontrado nesta versão")
    with e2e_page.expect_download(timeout=5000) as dl_info:
        btn.click()
    download = dl_info.value
    assert download.suggested_filename.endswith(".json"), (
        f"Download não é JSON: {download.suggested_filename}"
    )
