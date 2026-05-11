import { describe, it, expect } from 'vitest';
import { calcularPareto } from './helpers/extract-analise.js';

function makeRows(entries) {
  // entries: array of [nome, valor]
  return entries.map(([nome, valor]) => ({ Cliente: nome, Valor: valor }));
}

describe('calcularPareto', () => {
  it('returns null when columns are missing', () => {
    expect(calcularPareto([], null, 'Valor')).toBeNull();
    expect(calcularPareto([], 'Cliente', null)).toBeNull();
  });

  it('returns empty array for empty dados', () => {
    const result = calcularPareto([], 'Cliente', 'Valor');
    expect(result).toHaveLength(0);
  });

  it('returns max 15 entities by default', () => {
    const dados = Array.from({ length: 20 }, (_, i) => ({
      Cliente: `Cliente${i}`,
      Valor: (20 - i) * 100,
    }));
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    expect(result.length).toBeLessThanOrEqual(15);
  });

  it('respects custom top parameter', () => {
    const dados = makeRows([['A', 300], ['B', 200], ['C', 100], ['D', 50]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor', 2);
    expect(result).toHaveLength(2);
  });

  it('is sorted by value descending (absolute)', () => {
    const dados = makeRows([['C', 100], ['A', 300], ['B', 200]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    expect(result[0].nome).toBe('A');
    expect(result[1].nome).toBe('B');
    expect(result[2].nome).toBe('C');
  });

  it('Ranking starts at 1', () => {
    const dados = makeRows([['A', 300], ['B', 200]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    expect(result[0].ranking).toBe(1);
    expect(result[1].ranking).toBe(2);
  });

  it('pct values sum to ~100%', () => {
    const dados = makeRows([['A', 400], ['B', 300], ['C', 200], ['D', 100]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    const totalPct = result.reduce((s, r) => s + r.pct, 0);
    expect(totalPct).toBeCloseTo(100, 4);
  });

  it('acumulado is monotonically increasing', () => {
    const dados = makeRows([['A', 400], ['B', 300], ['C', 200], ['D', 100]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    for (let i = 1; i < result.length; i++) {
      expect(result[i].acumulado).toBeGreaterThanOrEqual(result[i - 1].acumulado);
    }
  });

  it('top entities get Classe_Pareto "A" (cumulative <= 80%)', () => {
    // 80% concentrated in first entity
    const dados = makeRows([['A', 800], ['B', 100], ['C', 100]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    expect(result[0].classe).toBe('A');
  });

  it('remaining entities get Classe_Pareto "B"', () => {
    const dados = makeRows([['A', 800], ['B', 100], ['C', 100]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    // After 'A' (80%), B and C should be class B
    const classB = result.filter(r => r.classe === 'B');
    expect(classB.length).toBeGreaterThan(0);
  });

  it('handles negative values (expenses) — sorted by absolute value', () => {
    const dados = makeRows([['A', -500], ['B', -200], ['C', -100]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    expect(result[0].nome).toBe('A');
    expect(result[0].total).toBe(-500);
  });

  it('aggregates multiple rows for same entity', () => {
    const dados = makeRows([['A', 100], ['A', 200], ['B', 150]]);
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    const a = result.find(r => r.nome === 'A');
    expect(a).toBeDefined();
    expect(a.total).toBe(300);
  });

  it('assigns (sem nome) to blank entity names', () => {
    const dados = [{ Cliente: '', Valor: 100 }];
    const result = calcularPareto(dados, 'Cliente', 'Valor');
    expect(result[0].nome).toBe('(sem nome)');
  });
});
