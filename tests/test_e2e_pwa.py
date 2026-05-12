"""
E2E tests for FluxoPRO PWA using Playwright.

Run with:
    pytest tests/test_e2e_pwa.py -m e2e

Skip with:
    pytest tests/ --ignore=tests/test_e2e_pwa.py
    or
    pytest tests/ -m "not e2e"
"""
import pytest


@pytest.mark.e2e
def test_page_title(e2e_page):
    """A página carrega com o título correto."""
    e2e_page.goto("http://localhost:8765/index.html")
    assert "FluxoPRO" in e2e_page.title()


@pytest.mark.e2e
def test_drop_zone_exists(e2e_page):
    """A zona de upload/drop existe na página."""
    e2e_page.goto("http://localhost:8765/index.html")
    # Aceita tanto #file-input quanto um elemento com classe .drop-zone
    file_input = e2e_page.locator("#file-input")
    drop_zone = e2e_page.locator(".drop-zone")
    assert file_input.count() > 0 or drop_zone.count() > 0, (
        "Nenhum elemento de upload encontrado (#file-input ou .drop-zone)"
    )


@pytest.mark.e2e
def test_dark_mode_toggle(e2e_page):
    """O botão de modo escuro existe e é clicável."""
    e2e_page.goto("http://localhost:8765/index.html")
    # Procura por botão de dark mode por variações comuns de seletor
    toggle = e2e_page.locator(
        "#btn-dark-mode, .dark-mode-toggle, [aria-label*='dark'], [aria-label*='escuro'], #toggle-dark"
    )
    assert toggle.count() > 0, "Botão de modo escuro não encontrado"
    # Verifica que é clicável (não lança exceção)
    toggle.first().click()


@pytest.mark.e2e
def test_erp_selector_exists(e2e_page):
    """O seletor de sistema ERP existe na página."""
    e2e_page.goto("http://localhost:8765/index.html")
    erp_select = e2e_page.locator("#sel-erp-sistema")
    assert erp_select.count() > 0, "Seletor #sel-erp-sistema não encontrado"
    # Verifica que tem opções
    options = e2e_page.locator("#sel-erp-sistema option")
    assert options.count() > 1, "Seletor de ERP deveria ter mais de uma opção"


@pytest.mark.e2e
def test_analyse_button_exists(e2e_page):
    """O botão de análise existe na página."""
    e2e_page.goto("http://localhost:8765/index.html")
    btn = e2e_page.locator(
        "#btn-analisar, button[onclick*='executarAnalise'], button[onclick*='analisar']"
    )
    assert btn.count() > 0, (
        "Botão de análise não encontrado (#btn-analisar ou onclick*='executarAnalise')"
    )
