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
    // Create a large dataset with tight cluster + one extreme outlier.
    // Need enough points for sample-std to be meaningful (function requires > 4).
    // Using 20 tightly clustered values + 1 extreme outlier ensures z > 3.
    const dados = Array.from({ length: 20 }, (_, i) =>
      makeRow(`NF${String(i).padStart(3, '0')}`, 100 + (i % 3))   // values 100–102
    );
    dados.push(makeRow('NF999', 10000));  // very extreme outlier
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

  // Regressão: a regex /RECEITA|VENDA|FATURAMENTO/ casava "DEVOLUÇÃO DE
  // VENDA", "CANCELAMENTO DE VENDA", "ESTORNO DE VENDA" — todas com
  // valor negativo por convenção contábil — e flagava como
  // "Classificação errada".
  describe('CLASSIFICAÇÃO_ERRADA: estornos não devem ser falso-positivo', () => {
    function rowComCategoria(cat, valor) {
      return { NF: 'X', Valor: valor, Data: '01/01/2024', Cliente: 'C',
               Vencimento: '', Categoria: cat, Tipo: '' };
    }

    it('RECEITA com valor negativo (real) ainda é flagada', () => {
      const result = auditoria([rowComCategoria('RECEITA DE SERVIÇOS', -100)], COLS);
      const classErr = result.filter(p => p.tipo === 'CLASSIFICAÇÃO_ERRADA');
      expect(classErr).toHaveLength(1);
    });

    it.each([
      'DEVOLUÇÃO DE VENDA',
      'CANCELAMENTO DE VENDA',
      'ESTORNO RECEITA',
      'REVERSÃO DE FATURAMENTO',
      'CHARGEBACK',
    ])('"%s" negativa NÃO é falso-positivo', (cat) => {
      const result = auditoria([rowComCategoria(cat, -100)], COLS);
      const classErr = result.filter(p => p.tipo === 'CLASSIFICAÇÃO_ERRADA');
      expect(classErr).toHaveLength(0);
    });
  });
});
