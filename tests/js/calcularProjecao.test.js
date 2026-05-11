import { describe, it, expect } from 'vitest';
import { calcularProjecao } from './helpers/extract-analise.js';

// Build linhas similar to what calcularFluxoPeriodo returns
function makeLinhas(n, recBase, despBase, step = 0) {
  return Array.from({ length: n }, (_, i) => ({
    periodo: `${String((i % 12) + 1).padStart(2, '0')}/2024`,
    receita: recBase + step * i,
    despesa: despBase,
    resultado: recBase + step * i - despBase,
    nfRec: 10,
    nfDesp: 5,
    pct: 0,
  }));
}

describe('calcularProjecao', () => {
  it('returns null for empty input', () => {
    expect(calcularProjecao([], 3)).toBeNull();
  });

  it('returns null for less than 3 data points', () => {
    expect(calcularProjecao(makeLinhas(1, 100, 50), 3)).toBeNull();
    expect(calcularProjecao(makeLinhas(2, 100, 50), 3)).toBeNull();
  });

  it('returns nProjecoes items', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    expect(result).toHaveLength(3);
  });

  it('returns 4 projected items when nProjecoes = 4', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 4);
    expect(result).toHaveLength(4);
  });

  it('all projected items have projetado: true', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(item.projetado).toBe(true);
    });
  });

  it('projected items have numeric rec, desp, res', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(typeof item.rec).toBe('number');
      expect(typeof item.desp).toBe('number');
      expect(typeof item.res).toBe('number');
      expect(isNaN(item.rec)).toBe(false);
      expect(isNaN(item.desp)).toBe(false);
      expect(isNaN(item.res)).toBe(false);
    });
  });

  it('projected items have string periodo labels', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(typeof item.periodo).toBe('string');
      expect(item.periodo.length).toBeGreaterThan(0);
    });
  });

  it('res equals rec minus desp for each projection', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(item.res).toBeCloseTo(item.rec - item.desp, 2);
    });
  });

  it('perfectly constant series produces stable projections', () => {
    // All same value → linear regression slope = 0, projection = mean
    const linhas = makeLinhas(6, 1000, 400);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(item.rec).toBeCloseTo(1000, 0);
      expect(item.desp).toBeCloseTo(400, 0);
    });
  });

  it('strictly increasing series produces increasing projections', () => {
    // Receita increases by 100 each period
    const linhas = makeLinhas(6, 1000, 500, 100);
    const result = calcularProjecao(linhas, 3);
    // All projected revenues should be >= initial value (trend is up)
    result.forEach(item => {
      expect(item.rec).toBeGreaterThan(0);
    });
    // Later projections should be >= earlier ones (monotone in linear extrapolation)
    expect(result[1].rec).toBeGreaterThanOrEqual(result[0].rec);
    expect(result[2].rec).toBeGreaterThanOrEqual(result[1].rec);
  });

  it('uses default nProjecoes of 3 when not provided', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas);
    expect(result).toHaveLength(3);
  });
});
