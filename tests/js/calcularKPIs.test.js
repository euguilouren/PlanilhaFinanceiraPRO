import { describe, it, expect } from 'vitest';
import { calcularKPIs } from './helpers/extract-analise.js';

const COLS = { valor: 'Valor', data: 'Data', tipo: 'Tipo', entidade: 'Cliente', chave: 'NF', vencimento: 'Vencimento', categoria: 'Categoria' };

function makeRow(valor, tipo, data) {
  return { Valor: valor, Tipo: tipo, Data: data || '01/01/2024', NF: String(Math.random()), Cliente: 'X', Vencimento: '', Categoria: '' };
}

describe('calcularKPIs', () => {
  it('returns zero-valued KPIs for empty array', () => {
    const kpis = calcularKPIs([], COLS);
    expect(kpis.receita).toBe(0);
    expect(kpis.despesa).toBe(0);
    expect(kpis.resultado).toBe(0);
    expect(kpis.ticket).toBe(0);
    expect(kpis.totalRegistros).toBe(0);
  });

  it('totalRegistros equals dados.length', () => {
    const dados = [makeRow(100, 'Receita'), makeRow(200, 'Receita'), makeRow(50, 'Despesa')];
    expect(calcularKPIs(dados, COLS).totalRegistros).toBe(3);
  });

  it('receita_total sums receita entries', () => {
    const dados = [makeRow(100, 'Receita'), makeRow(200, 'Receita'), makeRow(50, 'Despesa')];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.receita).toBeCloseTo(300, 5);
  });

  it('despesa_total sums despesa entries', () => {
    const dados = [makeRow(100, 'Receita'), makeRow(50, 'Despesa'), makeRow(75, 'Despesa')];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.despesa).toBeCloseTo(125, 5);
  });

  it('resultado equals receita minus despesa', () => {
    const dados = [makeRow(500, 'Receita'), makeRow(200, 'Despesa')];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.resultado).toBeCloseTo(300, 5);
  });

  it('margem_pct equals resultado / receita * 100', () => {
    const dados = [makeRow(200, 'Receita'), makeRow(100, 'Despesa')];
    const kpis = calcularKPIs(dados, COLS);
    // resultado = 100, receita = 200 → margem = 50%
    expect(kpis.margem).toBeCloseTo(50, 5);
  });

  it('margem is 0 (or handled) when receita is 0', () => {
    const dados = [makeRow(100, 'Despesa')];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.receita).toBe(0);
    // When receita=0 and despesa>0, margem should not be NaN
    expect(isNaN(kpis.margem)).toBe(false);
  });

  it('ticket_medio equals receita / count of receita entries', () => {
    const dados = [makeRow(100, 'Receita'), makeRow(300, 'Receita'), makeRow(50, 'Despesa')];
    const kpis = calcularKPIs(dados, COLS);
    // receita = 400, nfRec = 2 → ticket = 200
    expect(kpis.ticket).toBeCloseTo(200, 5);
  });

  it('ticket is 0 when no receita entries', () => {
    const dados = [makeRow(100, 'Despesa')];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.ticket).toBe(0);
  });

  it('classifies positive values without Tipo as receita', () => {
    const dados = [{ Valor: 300, Tipo: '', Data: '01/01/2024', NF: '1', Cliente: 'A', Vencimento: '', Categoria: '' }];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.receita).toBeCloseTo(300, 5);
    expect(kpis.despesa).toBe(0);
  });

  it('classifies negative values without Tipo as despesa', () => {
    const dados = [{ Valor: -150, Tipo: '', Data: '01/01/2024', NF: '1', Cliente: 'A', Vencimento: '', Categoria: '' }];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.despesa).toBeCloseTo(150, 5);
    expect(kpis.receita).toBe(0);
  });

  it('periodoInicio and periodoFim are correct', () => {
    const dados = [
      makeRow(100, 'Receita', '01/01/2024'),
      makeRow(200, 'Receita', '15/06/2024'),
      makeRow(50,  'Receita', '31/12/2024'),
    ];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.periodoInicio).toBeDefined();
    expect(kpis.periodoFim).toBeDefined();
    expect(kpis.periodoInicio.getFullYear()).toBe(2024);
    expect(kpis.periodoFim.getFullYear()).toBe(2024);
    expect(kpis.periodoInicio.getMonth()).toBe(0);  // January
    expect(kpis.periodoFim.getMonth()).toBe(11);    // December
  });

  it('colsDetectadas counts non-null cols', () => {
    const dados = [makeRow(100, 'Receita')];
    const kpis = calcularKPIs(dados, COLS);
    expect(kpis.colsDetectadas).toBeGreaterThan(0);
  });
});
