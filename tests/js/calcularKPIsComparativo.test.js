import { describe, it, expect } from 'vitest';
import { calcularKPIsComparativo } from './helpers/extract-analise.js';

const A = { receita: 1000, despesa: 600, resultado: 400, margem: 40, ticket: 100, totalRegistros: 10 };
const B = { receita: 1500, despesa: 900, resultado: 600, margem: 40, ticket: 150, totalRegistros: 10 };

describe('calcularKPIsComparativo', () => {
  it('retorna todas as 6 chaves esperadas pelo renderComparativo', () => {
    const r = calcularKPIsComparativo(A, B);
    expect(Object.keys(r).sort()).toEqual(
      ['despesa', 'margem', 'receita', 'resultado', 'ticket', 'totalRegistros']
    );
  });

  it('cada chave inclui a, b, abs e pct', () => {
    const r = calcularKPIsComparativo(A, B);
    for (const k of Object.keys(r)) {
      expect(r[k]).toHaveProperty('a');
      expect(r[k]).toHaveProperty('b');
      expect(r[k]).toHaveProperty('abs');
      expect(r[k]).toHaveProperty('pct');
    }
  });

  it('delta absoluto = b - a', () => {
    const r = calcularKPIsComparativo(A, B);
    expect(r.receita.abs).toBe(500);
    expect(r.despesa.abs).toBe(300);
    expect(r.resultado.abs).toBe(200);
  });

  it('delta percentual normalizado por |a|', () => {
    const r = calcularKPIsComparativo(A, B);
    expect(r.receita.pct).toBe(50);     // (1500-1000)/1000 = 50%
    expect(r.despesa.pct).toBe(50);     // (900-600)/600
    expect(r.ticket.pct).toBe(50);      // (150-100)/100
  });

  it('pct é null quando a=0 (evita divisão por zero)', () => {
    const zero = { receita: 0, despesa: 100, resultado: 0, margem: 0, ticket: 0, totalRegistros: 0 };
    const r = calcularKPIsComparativo(zero, A);
    expect(r.receita.pct).toBeNull();
    expect(r.ticket.pct).toBeNull();
  });

  it('pct positivo para crescimento, negativo para queda', () => {
    const r = calcularKPIsComparativo(B, A);  // inverte: receita cai
    expect(r.receita.pct).toBeLessThan(0);
    expect(r.receita.abs).toBe(-500);
  });

  it('pct usa |a| no denominador (não preserva sinal de a)', () => {
    // Quando a é negativo (resultado prejuízo) e b é positivo (recuperação),
    // pct deve ser positivo (melhoria), não negativo.
    const prejuizo = { ...A, resultado: -200 };
    const lucro    = { ...B, resultado:  100 };
    const r = calcularKPIsComparativo(prejuizo, lucro);
    expect(r.resultado.abs).toBe(300);
    expect(r.resultado.pct).toBe(150);  // (100-(-200))/|-200| = 300/200 = 150%
  });

  it('NaN em qualquer lado retorna abs=0 e pct=null', () => {
    const comNaN = { ...A, receita: NaN };
    const r = calcularKPIsComparativo(comNaN, B);
    expect(r.receita.abs).toBe(0);
    expect(r.receita.pct).toBeNull();
  });

  it('a e b são preservados no resultado', () => {
    const r = calcularKPIsComparativo(A, B);
    expect(r.margem.a).toBe(40);
    expect(r.margem.b).toBe(40);
    expect(r.margem.abs).toBe(0);
    expect(r.margem.pct).toBe(0);
  });
});
