import { describe, it, expect } from 'vitest';
import { toNum, toDate } from './helpers/extract-analise.js';

// Parsers críticos sem testes diretos antes. Cobertura aqui também serve de
// documentação executável do contrato: o que aceita, o que rejeita, e onde
// o comportamento é ambíguo por design.

describe('toNum', () => {
  describe('inputs vazios/inválidos retornam NaN', () => {
    it.each([null, undefined, '', NaN, Infinity, -Infinity])('toNum(%s) === NaN', (v) => {
      expect(Number.isNaN(toNum(v))).toBe(true);
    });

    it('string sem dígitos retorna NaN', () => {
      expect(Number.isNaN(toNum('abc'))).toBe(true);
    });
  });

  describe('formato brasileiro (1.234,56)', () => {
    it('parse R$ com decimal BR', () => {
      expect(toNum('R$ 1.234,56')).toBeCloseTo(1234.56, 2);
    });

    it('separador de milhar BR sem decimal', () => {
      expect(toNum('1.234.567')).toBe(1234567);
    });

    it('vírgula sozinha vira decimal', () => {
      expect(toNum('123,45')).toBeCloseTo(123.45, 2);
    });
  });

  describe('formato americano (1,234.56)', () => {
    it('milhar US com decimal', () => {
      expect(toNum('1,234.56')).toBeCloseTo(1234.56, 2);
    });

    it('milhar US sem decimal', () => {
      expect(toNum('1,000,000')).toBe(1000000);
    });
  });

  describe('parênteses contábeis', () => {
    it('(1.234,56) é negativo', () => {
      expect(toNum('(1.234,56)')).toBeCloseTo(-1234.56, 2);
    });

    it('(1000) é negativo', () => {
      expect(toNum('(1000)')).toBe(-1000);
    });
  });

  describe('ambiguidade conhecida: "1.234" sem vírgula', () => {
    // BR users may type "1.234" meaning R$ 1.234 (mil reais, sem decimais).
    // US default em parseFloat → 1.234. Diferença de 1000x em valor monetário.
    // O parser default é US — sem contexto da coluna, "1.234" é interpretado
    // como decimal. Test documenta esse comportamento para que ninguém
    // mude sem perceber o impacto.
    it('"1.234" → 1.234 (parser US-default — ambiguidade documentada)', () => {
      expect(toNum('1.234')).toBeCloseTo(1.234, 3);
    });

    it('"1.234.567" (múltiplos pontos) → 1234567 (BR thousands)', () => {
      expect(toNum('1.234.567')).toBe(1234567);
    });
  });

  describe('number pass-through', () => {
    it('preserva números finitos', () => {
      expect(toNum(42)).toBe(42);
      expect(toNum(-3.14)).toBeCloseTo(-3.14, 2);
      expect(toNum(0)).toBe(0);
    });
  });
});

describe('toDate', () => {
  describe('formatos válidos', () => {
    it('DD/MM/YYYY (BR)', () => {
      const d = toDate('15/03/2024');
      expect(d).not.toBeNull();
      expect(d.getFullYear()).toBe(2024);
      expect(d.getMonth()).toBe(2);
      expect(d.getDate()).toBe(15);
    });

    it('YYYY-MM-DD (ISO)', () => {
      const d = toDate('2024-03-15');
      expect(d).not.toBeNull();
      expect(d.getMonth()).toBe(2);
    });

    it('D/M/YYYY loose BR', () => {
      const d = toDate('5/3/2024');
      expect(d).not.toBeNull();
      expect(d.getDate()).toBe(5);
      expect(d.getMonth()).toBe(2);
    });

    it('Date object passa direto', () => {
      const orig = new Date(2024, 2, 15);
      expect(toDate(orig)).toBe(orig);
    });

    it('Excel serial number', () => {
      // 44927 = 1/1/2023 no calendário do Excel
      const d = toDate(44927);
      expect(d).not.toBeNull();
      expect(d.getFullYear()).toBe(2023);
    });
  });

  describe('formatos inválidos retornam null', () => {
    it.each([null, undefined, '', 0, false])('toDate(%s) === null', (v) => {
      expect(toDate(v)).toBeNull();
    });

    it('string sem padrão data retorna null', () => {
      expect(toDate('abc')).toBeNull();
    });

    it('DD/MM/YYYY inválido (mês 13) retorna null', () => {
      expect(toDate('15/13/2024')).toBeNull();
    });

    it('YYYY-MM-DD inválido (dia 32) retorna null', () => {
      expect(toDate('2024-01-32')).toBeNull();
    });

    // Regressão: o fallback `new Date(s)` aceitava qualquer string que o
    // construtor do Date entende, corrompendo aging/projeção silenciosamente.
    it('"Mar 5" (texto solto) retorna null — era valid Date silencioso', () => {
      expect(toDate('Mar 5')).toBeNull();
    });

    it('"2024" sozinho retorna null — era 1/1/2024 silencioso', () => {
      expect(toDate('2024')).toBeNull();
    });

    it('"January 2024" retorna null — era valid Date silencioso', () => {
      expect(toDate('January 2024')).toBeNull();
    });

    it('"15" sozinho retorna null', () => {
      expect(toDate('15')).toBeNull();
    });
  });

  describe('formatos ISO-like ainda aceitos no fallback', () => {
    it('YYYY/MM/DD (slash em vez de hífen)', () => {
      const d = toDate('2024/03/15');
      expect(d).not.toBeNull();
      expect(d.getFullYear()).toBe(2024);
    });
  });
});
