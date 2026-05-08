import { describe, it, expect } from 'vitest';
import { auditoria } from './helpers/extract-analise.js';

const COLS = { valor: 'Valor', data: 'Data', chave: 'NF', entidade: 'Cliente', vencimento: 'Vencimento', categoria: 'Categoria', tipo: 'Tipo' };

function makeRow(nf, valor, data) {
  return { NF: nf, Valor: valor, Data: data || '01/01/2024', Cliente: 'Teste', Vencimento: '', Categoria: '', Tipo: '' };
}

describe('auditoria', () => {
  it('returns empty array for empty dados', () => {
    const result = auditoria([], COLS);
    expect(Array.isArray(result)).toBe(true);
    expect(result).toHaveLength(0);
  });

  it('returns array of problems', () => {
    const dados = [makeRow('NF001', 100), makeRow('NF002', 200)];
    const result = auditoria(dados, COLS);
    expect(Array.isArray(result)).toBe(true);
  });

  it('detects duplicate keys', () => {
    const dados = [makeRow('NF001', 100), makeRow('NF001', 200), makeRow('NF002', 300)];
    const result = auditoria(dados, COLS);
    const duplicatas = result.filter(p => p.tipo === 'DUPLICATA');
    expect(duplicatas.length).toBeGreaterThan(0);
  });

  it('each problem has severidade and tipo properties', () => {
    const dados = [makeRow('NF001', 100), makeRow('NF001', 200)];
    const result = auditoria(dados, COLS);
    result.forEach(p => {
      expect(p).toHaveProperty('severidade');
      expect(p).toHaveProperty('tipo');
    });
  });

  it('each problem has linha and descricao properties', () => {
    const dados = [makeRow('NF001', 100), makeRow('NF001', 200)];
    const result = auditoria(dados, COLS);
    result.forEach(p => {
      expect(p).toHaveProperty('linha');
      expect(p).toHaveProperty('descricao');
    });
  });

  it('detects empty required fields (valor)', () => {
    const dados = [
      makeRow('NF001', ''),
      makeRow('NF002', 100),
    ];
    const result = auditoria(dados, COLS);
    const vazios = result.filter(p => p.tipo === 'CAMPO_VAZIO');
    expect(vazios.length).toBeGreaterThan(0);
  });

  it('detects empty required fields (data)', () => {
    const dados = [
      { NF: 'NF001', Valor: 100, Data: '', Cliente: 'A', Vencimento: '', Categoria: '', Tipo: '' },
      makeRow('NF002', 200),
    ];
    const result = auditoria(dados, COLS);
    const vazios = result.filter(p => p.tipo === 'CAMPO_VAZIO' && p.coluna === 'Data');
    expect(vazios.length).toBeGreaterThan(0);
  });

  it('detects outliers (values > 3 std deviations from mean)', () => {
    // Create a dataset where one value is far outside normal range
    const dados = [
      makeRow('NF001', 100), makeRow('NF002', 110), makeRow('NF003', 90),
      makeRow('NF004', 105), makeRow('NF005', 95),  makeRow('NF006', 1000000),
    ];
    const result = auditoria(dados, COLS);
    const outliers = result.filter(p => p.tipo === 'OUTLIER');
    expect(outliers.length).toBeGreaterThan(0);
  });

  it('does not flag normal values as outliers', () => {
    const dados = [
      makeRow('NF001', 100), makeRow('NF002', 110), makeRow('NF003', 90),
      makeRow('NF004', 105), makeRow('NF005', 95),
    ];
    const result = auditoria(dados, COLS);
    const outliers = result.filter(p => p.tipo === 'OUTLIER');
    expect(outliers).toHaveLength(0);
  });

  it('detects future dates', () => {
    const futureDate = new Date(Date.now() + 30 * 86400000);
    const dd = String(futureDate.getDate()).padStart(2, '0');
    const mm = String(futureDate.getMonth() + 1).padStart(2, '0');
    const yyyy = futureDate.getFullYear();
    const dateStr = `${dd}/${mm}/${yyyy}`;
    const dados = [makeRow('NF001', 100, dateStr), makeRow('NF002', 200)];
    const result = auditoria(dados, COLS);
    const futuras = result.filter(p => p.tipo === 'DATA_FUTURA');
    expect(futuras.length).toBeGreaterThan(0);
  });

  it('does not flag past dates as future', () => {
    const dados = [makeRow('NF001', 100, '01/01/2020'), makeRow('NF002', 200, '15/06/2023')];
    const result = auditoria(dados, COLS);
    const futuras = result.filter(p => p.tipo === 'DATA_FUTURA');
    expect(futuras).toHaveLength(0);
  });

  it('sorts results by severity: CRÍTICA before ALTA before MÉDIA', () => {
    // Duplicate produces CRÍTICA, empty field produces ALTA, outlier produces MÉDIA
    const dados = [
      makeRow('NF001', 100), makeRow('NF001', 200),   // duplicate → CRÍTICA
      { NF: 'NF003', Valor: '', Data: '01/01/2024', Cliente: 'A', Vencimento: '', Categoria: '', Tipo: '' }, // empty → ALTA
      makeRow('NF004', 110), makeRow('NF005', 90),
      makeRow('NF006', 1000000),   // outlier → MÉDIA
    ];
    const result = auditoria(dados, COLS);
    const severidades = result.map(p => p.severidade);
    const ord = { 'CRÍTICA': 0, 'ALTA': 1, 'MÉDIA': 2, 'BAIXA': 3 };
    for (let i = 1; i < severidades.length; i++) {
      const prev = ord[severidades[i - 1]] ?? 4;
      const curr = ord[severidades[i]] ?? 4;
      expect(prev).toBeLessThanOrEqual(curr);
    }
  });
});
