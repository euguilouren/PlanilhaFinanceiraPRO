import { describe, it, expect } from 'vitest';
import { calcularSazonalidade } from './helpers/extract-analise.js';

function makeRow(dateStr, valor, tipo) {
  const row = { Data: dateStr, Valor: valor };
  if (tipo !== undefined) row.Tipo = tipo;
  return row;
}

describe('calcularSazonalidade', () => {
  it('returns null when colData is missing', () => {
    expect(calcularSazonalidade([makeRow('2024-01-15', 100)], null, 'Valor')).toBeNull();
  });

  it('returns null when colValor is missing', () => {
    expect(calcularSazonalidade([makeRow('2024-01-15', 100)], 'Data', null)).toBeNull();
  });

  it('returns null for empty data', () => {
    expect(calcularSazonalidade([], 'Data', 'Valor')).toBeNull();
  });

  it('returns null when all values are zero', () => {
    const dados = [makeRow('2024-01-15', 0), makeRow('2024-02-10', 0)];
    expect(calcularSazonalidade(dados, 'Data', 'Valor')).toBeNull();
  });

  it('returns array of 12 months', () => {
    const dados = [makeRow('2024-03-15', 500)];
    const result = calcularSazonalidade(dados, 'Data', 'Valor');
    expect(result).not.toBeNull();
    expect(result).toHaveLength(12);
  });

  it('each item has mes, receita, despesa, resultado, nAnos', () => {
    const dados = [makeRow('2024-01-15', 100)];
    const result = calcularSazonalidade(dados, 'Data', 'Valor');
    result.forEach(item => {
      expect(typeof item.mes).toBe('string');
      expect(typeof item.receita).toBe('number');
      expect(typeof item.despesa).toBe('number');
      expect(typeof item.resultado).toBe('number');
      expect(typeof item.nAnos).toBe('number');
    });
  });

  it('month names are in correct order Jan..Dez', () => {
    const dados = [makeRow('2024-06-15', 100)];
    const result = calcularSazonalidade(dados, 'Data', 'Valor');
    const nomes = result.map(r => r.mes);
    expect(nomes[0]).toBe('Jan');
    expect(nomes[5]).toBe('Jun');
    expect(nomes[11]).toBe('Dez');
  });

  it('positive value without Tipo column classified as receita', () => {
    const dados = [makeRow('2024-03-10', 1000)];
    const result = calcularSazonalidade(dados, 'Data', 'Valor');
    expect(result[2].receita).toBeCloseTo(1000, 2);
    expect(result[2].despesa).toBeCloseTo(0, 2);
  });

  it('negative value without Tipo column classified as despesa', () => {
    const dados = [makeRow('2024-03-10', -400)];
    const result = calcularSazonalidade(dados, 'Data', 'Valor');
    expect(result[2].despesa).toBeCloseTo(400, 2);
    expect(result[2].receita).toBeCloseTo(0, 2);
  });

  it('Tipo=RECEITA forces positive classification', () => {
    const dados = [makeRow('2024-05-20', 800, 'RECEITA')];
    const result = calcularSazonalidade(dados, 'Data', 'Valor', 'Tipo');
    expect(result[4].receita).toBeCloseTo(800, 2);
  });

  it('Tipo=DESPESA forces despesa classification', () => {
    const dados = [makeRow('2024-07-01', 600, 'DESPESA')];
    const result = calcularSazonalidade(dados, 'Data', 'Valor', 'Tipo');
    expect(result[6].despesa).toBeCloseTo(600, 2);
  });

  it('averages across multiple years for the same month', () => {
    const dados = [
      makeRow('2023-01-15', 1000),
      makeRow('2024-01-15', 2000),
    ];
    const result = calcularSazonalidade(dados, 'Data', 'Valor');
    // Jan receives 1000+2000 across 2 years → avg 1500
    expect(result[0].receita).toBeCloseTo(1500, 2);
    expect(result[0].nAnos).toBe(2);
  });

  it('resultado equals receita minus despesa', () => {
    const dados = [
      makeRow('2024-04-10', 2000),
      makeRow('2024-04-20', -500),
    ];
    const result = calcularSazonalidade(dados, 'Data', 'Valor');
    expect(result[3].resultado).toBeCloseTo(result[3].receita - result[3].despesa, 2);
  });

  it('skips rows with invalid dates', () => {
    const dados = [
      makeRow('invalid-date', 9999),
      makeRow('2024-08-15', 100),
    ];
    const result = calcularSazonalidade(dados, 'Data', 'Valor');
    expect(result[7].receita).toBeCloseTo(100, 2);
  });

  // Regressão: agent alegou que regex /SA[IÍ]DA/ não casava "SAIDA" sem acento.
  // Falso — char class [IÍ] aceita os dois. Travando classificação correta.
  it.each([
    ['SAIDA',  'D'],   // sem acento
    ['SAÍDA',  'D'],   // com acento
    ['DEBITO', 'D'],   // sem acento
    ['DÉBITO', 'D'],   // com acento
    ['DESPESA','D'],
    ['ENTRADA','R'],
    ['CREDITO','R'],   // sem acento — fallback regex CR[EÉ]DI
    ['CRÉDITO','R'],   // com acento
    ['RECEITA','R'],
    ['VENDA',  'R'],
  ])('classifica tipo "%s" corretamente (R=receita, D=despesa)', (tipo, expected) => {
    const result = calcularSazonalidade(
      [makeRow('2024-01-15', 100, tipo)],
      'Data', 'Valor', 'Tipo'
    );
    // Janeiro = índice 0
    if (expected === 'R') {
      expect(result[0].receita).toBeGreaterThan(0);
      expect(result[0].despesa).toBe(0);
    } else {
      expect(result[0].despesa).toBeGreaterThan(0);
      expect(result[0].receita).toBe(0);
    }
  });
});
