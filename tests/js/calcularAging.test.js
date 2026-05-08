import { describe, it, expect } from 'vitest';
import { calcularAging } from './helpers/extract-analise.js';

const DAY = 86400000;

function dateStr(daysFromNow) {
  const d = new Date(Date.now() + daysFromNow * DAY);
  // Format as DD/MM/YYYY
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

describe('calcularAging', () => {
  it('returns null when columns are missing', () => {
    expect(calcularAging([], null, 'Valor')).toBeNull();
    expect(calcularAging([], 'Vencimento', null)).toBeNull();
  });

  it('returns empty array for empty dados', () => {
    const result = calcularAging([], 'Venc', 'Val');
    expect(result).toEqual([]);
  });

  it('classifies future vencimento as "A vencer"', () => {
    const dados = [{ Venc: dateStr(10), Val: 100 }];
    const result = calcularAging(dados, 'Venc', 'Val');
    const faixa = result.find(f => f.faixa === 'A vencer');
    expect(faixa).toBeDefined();
    expect(faixa.qtd).toBe(1);
    expect(faixa.total).toBe(100);
  });

  it('classifies 15-days overdue as "Vencido 1-30d"', () => {
    const dados = [{ Venc: dateStr(-15), Val: 200 }];
    const result = calcularAging(dados, 'Venc', 'Val');
    const faixa = result.find(f => f.faixa === 'Vencido 1-30d');
    expect(faixa).toBeDefined();
    expect(faixa.qtd).toBe(1);
    expect(faixa.total).toBe(200);
  });

  it('classifies 45-days overdue as "Vencido 31-60d"', () => {
    const dados = [{ Venc: dateStr(-45), Val: 300 }];
    const result = calcularAging(dados, 'Venc', 'Val');
    const faixa = result.find(f => f.faixa === 'Vencido 31-60d');
    expect(faixa).toBeDefined();
    expect(faixa.qtd).toBe(1);
    expect(faixa.total).toBe(300);
  });

  it('classifies 75-days overdue as "Vencido 61-90d"', () => {
    const dados = [{ Venc: dateStr(-75), Val: 400 }];
    const result = calcularAging(dados, 'Venc', 'Val');
    const faixa = result.find(f => f.faixa === 'Vencido 61-90d');
    expect(faixa).toBeDefined();
    expect(faixa.qtd).toBe(1);
    expect(faixa.total).toBe(400);
  });

  it('classifies 120-days overdue as "Vencido +90d"', () => {
    const dados = [{ Venc: dateStr(-120), Val: 500 }];
    const result = calcularAging(dados, 'Venc', 'Val');
    const faixa = result.find(f => f.faixa === 'Vencido +90d');
    expect(faixa).toBeDefined();
    expect(faixa.qtd).toBe(1);
    expect(faixa.total).toBe(500);
  });

  it('classifies null/empty vencimento as "Sem data"', () => {
    const dados = [{ Venc: '', Val: 150 }, { Venc: null, Val: 250 }];
    const result = calcularAging(dados, 'Venc', 'Val');
    const faixa = result.find(f => f.faixa === 'Sem data');
    expect(faixa).toBeDefined();
    expect(faixa.qtd).toBe(2);
    expect(faixa.total).toBe(400);
  });

  it('total values sum correctly across all buckets', () => {
    const dados = [
      { Venc: dateStr(5),   Val: 100 },  // A vencer
      { Venc: dateStr(-15), Val: 200 },  // 1-30d
      { Venc: dateStr(-45), Val: 300 },  // 31-60d
      { Venc: '',           Val: 400 },  // Sem data
    ];
    const result = calcularAging(dados, 'Venc', 'Val');
    const totalSum = result.reduce((s, f) => s + f.total, 0);
    expect(totalSum).toBeCloseTo(1000, 5);
  });

  it('pct values sum to ~100 for non-empty result', () => {
    const dados = [
      { Venc: dateStr(5),   Val: 100 },
      { Venc: dateStr(-15), Val: 200 },
      { Venc: dateStr(-120),Val: 300 },
    ];
    const result = calcularAging(dados, 'Venc', 'Val');
    const pctSum = result.reduce((s, f) => s + f.pct, 0);
    expect(pctSum).toBeCloseTo(100, 5);
  });

  it('uses absolute values (handles negative amounts)', () => {
    const dados = [{ Venc: dateStr(-15), Val: -200 }];
    const result = calcularAging(dados, 'Venc', 'Val');
    const faixa = result.find(f => f.faixa === 'Vencido 1-30d');
    expect(faixa).toBeDefined();
    expect(faixa.total).toBe(200);
  });
});
