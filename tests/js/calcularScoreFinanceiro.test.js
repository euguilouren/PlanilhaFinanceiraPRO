import { describe, it, expect } from 'vitest';
import { calcularScoreFinanceiro } from './helpers/extract-analise.js';

describe('calcularScoreFinanceiro', () => {
  it('retorna estrutura {score, classe, pilares}', () => {
    const r = calcularScoreFinanceiro(null, null, null, null);
    expect(r).toHaveProperty('score');
    expect(r).toHaveProperty('classe');
    expect(r).toHaveProperty('pilares');
  });

  it('cobre 4 pilares: margem, aging, pareto, auditoria', () => {
    const r = calcularScoreFinanceiro(null, null, null, null);
    expect(Object.keys(r.pilares).sort()).toEqual(['aging', 'auditoria', 'margem', 'pareto']);
  });

  it('soma dos pilares é exatamente o score total', () => {
    const r = calcularScoreFinanceiro(
      { margem: 35 },
      [{ faixa: 'A vencer', total: 100 }],
      Object.assign([{ total: 10 }, { total: 10 }, { total: 10 }], { totalGeral: 30 }),
      []
    );
    const soma = Object.values(r.pilares).reduce((s, p) => s + p.pts, 0);
    expect(r.score).toBe(soma);
  });

  it('score é 0 quando todos os pilares estão zerados (margem<5, prejuízo crítico)', () => {
    const r = calcularScoreFinanceiro(
      { margem: 0 },
      [{ faixa: '90+ dias', total: 100 }],   // 100% vencido
      // ≥3 entradas exigidas para acionar cálculo de concentração
      Object.assign([{ total: 100 }, { total: 0.1 }, { total: 0.1 }], { totalGeral: 100.2 }),
      Array(10).fill({ severidade: 'CRÍTICA' }),  // 10 críticos
    );
    expect(r.score).toBe(0);
    expect(r.classe).toBe('vermelho');
  });

  it('margem ≥30% rende 30 pts (faixa máxima)', () => {
    const r = calcularScoreFinanceiro({ margem: 50 }, null, null, null);
    expect(r.pilares.margem.pts).toBe(30);
    expect(r.pilares.margem.detalhe).toBe('50.0%');
  });

  it('margem em 15-29 rende 20 pts; 5-14 rende 10 pts', () => {
    expect(calcularScoreFinanceiro({ margem: 20 }, null, null, null).pilares.margem.pts).toBe(20);
    expect(calcularScoreFinanceiro({ margem: 10 }, null, null, null).pilares.margem.pts).toBe(10);
    expect(calcularScoreFinanceiro({ margem:  4 }, null, null, null).pilares.margem.pts).toBe(0);
  });

  it('aging 0% vencido rende 25 pts máximos', () => {
    const aging = [{ faixa: 'A vencer', total: 1000 }];
    const r = calcularScoreFinanceiro(null, aging, null, null);
    expect(r.pilares.aging.pts).toBe(25);
  });

  it('aging <10% vencido rende 18 pts', () => {
    const aging = [
      { faixa: 'A vencer', total: 900 },
      { faixa: '1-30 dias', total: 50 },
    ];
    const r = calcularScoreFinanceiro(null, aging, null, null);
    expect(r.pilares.aging.pts).toBe(18);
  });

  it('aging sem dados (vencimento não mapeado) rende 0 pts com detalhe explicativo', () => {
    const r = calcularScoreFinanceiro(null, null, null, null);
    expect(r.pilares.aging.pts).toBe(0);
    expect(r.pilares.aging.detalhe).toMatch(/vencimento não mapeado/);
  });

  it('Pareto baixa concentração (top3 <40%) rende 20 pts', () => {
    // 10 entradas iguais → top3 = 30% do total
    const pareto = Object.assign(
      Array(10).fill(null).map(() => ({ total: 100 })),
      { totalGeral: 1000 },
    );
    const r = calcularScoreFinanceiro(null, null, pareto, null);
    expect(r.pilares.pareto.pts).toBe(20);
  });

  it('auditoria sem críticos rende 25 pts; ≤2 críticos rende 18', () => {
    expect(calcularScoreFinanceiro(null, null, null, []).pilares.auditoria.pts).toBe(25);
    expect(calcularScoreFinanceiro(null, null, null, [
      { severidade: 'CRÍTICA' }, { severidade: 'CRÍTICA' },
    ]).pilares.auditoria.pts).toBe(18);
  });

  it('problemas não-CRÍTICA não afetam a auditoria', () => {
    const r = calcularScoreFinanceiro(null, null, null, Array(20).fill({ severidade: 'AVISO' }));
    expect(r.pilares.auditoria.pts).toBe(25);
  });

  it('classe verde≥80, amarelo 60-79, vermelho<60', () => {
    // score máximo possível: 30 + 25 + 20 + 25 = 100
    const max = calcularScoreFinanceiro(
      { margem: 50 },
      [{ faixa: 'A vencer', total: 100 }],
      Object.assign([{ total: 10 }, { total: 10 }, { total: 10 }, { total: 70 }], { totalGeral: 100 }),
      [],
    );
    expect(max.score).toBeGreaterThanOrEqual(80);
    expect(max.classe).toBe('verde');
  });
});
