import { describe, it, expect } from 'vitest';
import { calcularIntegridade } from './helpers/extract-analise.js';

const DADOS_OK = [
  { Valor: 100,  Data: '01/01/2024' },
  { Valor: 200,  Data: '02/01/2024' },
  { Valor: 300,  Data: '03/01/2024' },
  { Valor: 400,  Data: '04/01/2024' },
  { Valor: 500,  Data: '05/01/2024' },
];
const COLS = { valor: 'Valor', data: 'Data' };

describe('calcularIntegridade', () => {
  it('retorna estrutura { checks, confianca, checksum, registros }', () => {
    const r = calcularIntegridade(DADOS_OK, COLS, null, null, null);
    expect(r).toHaveProperty('checks');
    expect(r).toHaveProperty('confianca');
    expect(r).toHaveProperty('checksum');
    expect(r).toHaveProperty('registros');
    expect(Array.isArray(r.checks)).toBe(true);
  });

  it('confiança é 100 para dados perfeitos', () => {
    const r = calcularIntegridade(DADOS_OK, COLS, null, null, null);
    expect(r.confianca).toBe(100);
  });

  it('checksum é a soma dos valores absolutos', () => {
    const r = calcularIntegridade(DADOS_OK, COLS, null, null, null);
    expect(r.checksum).toBe(1500);
  });

  it('checksum trata negativos via |valor|', () => {
    const dados = [{ Valor: -100 }, { Valor: 50 }];
    const r = calcularIntegridade(dados, { valor: 'Valor' }, null, null, null);
    expect(r.checksum).toBe(150);
  });

  it('check "Valores processados" passa quando ≥85% têm valor válido', () => {
    const r = calcularIntegridade(DADOS_OK, COLS, null, null, null);
    const valoresCheck = r.checks.find(c => c.nome === 'Valores processados');
    expect(valoresCheck.status).toBe('OK');
  });

  it('check "Valores processados" alerta quando <85% válidos', () => {
    const ruim = [
      { Valor: 100 }, { Valor: '' }, { Valor: 'texto' }, { Valor: null }, { Valor: 200 },
    ];
    const r = calcularIntegridade(ruim, { valor: 'Valor' }, null, null, null);
    const c = r.checks.find(c => c.nome === 'Valores processados');
    expect(c.status).toBe('ALERTA');
    expect(c.como).toBeTruthy();  // tem instruções para o usuário
  });

  it('inclui sempre check INFO de checksum', () => {
    const r = calcularIntegridade(DADOS_OK, COLS, null, null, null);
    const cs = r.checks.find(c => c.nome === 'Checksum (soma |valores|)');
    expect(cs.status).toBe('INFO');
    expect(cs.checksum).toBe(1500);
  });

  it('check de Pareto só aparece quando pareto é fornecido', () => {
    const semP = calcularIntegridade(DADOS_OK, COLS, null, null, null);
    expect(semP.checks.find(c => c.nome.includes('Pareto'))).toBeUndefined();

    const pareto = Object.assign([{ total: 500 }, { total: 500 }, { total: 500 }],
      { totalGeral: 1500, totalEntidades: 3 });
    const comP = calcularIntegridade(DADOS_OK, COLS, null, null, pareto);
    expect(comP.checks.find(c => c.nome.includes('Pareto'))).toBeTruthy();
  });

  it('Pareto truncado retorna status INFO (não DIVERGENTE)', () => {
    const pareto = Object.assign([{ total: 100 }, { total: 100 }, { total: 100 }],
      { totalGeral: 1500, totalEntidades: 15 });  // 3 exibidos de 15 → truncado
    const r = calcularIntegridade(DADOS_OK, COLS, null, null, pareto);
    const cP = r.checks.find(c => c.nome.includes('Pareto'));
    expect(cP.status).toBe('INFO');
  });

  it('cobertura de datas check só aparece quando cols.data está definido', () => {
    const sem = calcularIntegridade(DADOS_OK, { valor: 'Valor' }, null, null, null);
    expect(sem.checks.find(c => c.nome === 'Cobertura de datas')).toBeUndefined();

    const com = calcularIntegridade(DADOS_OK, COLS, null, null, null);
    expect(com.checks.find(c => c.nome === 'Cobertura de datas')).toBeTruthy();
  });

  it('cobertura de datas alerta quando <80% válidas', () => {
    const dados = [
      { Valor: 100, Data: '01/01/2024' },
      { Valor: 100, Data: 'invalida' },
      { Valor: 100, Data: '' },
      { Valor: 100, Data: '' },
      { Valor: 100, Data: '' },
    ];
    const r = calcularIntegridade(dados, COLS, null, null, null);
    const c = r.checks.find(x => x.nome === 'Cobertura de datas');
    expect(c.status).toBe('ALERTA');
  });

  it('classificação automática INFO surge quando não há categoria e há valores negativos', () => {
    const dados = [{ Valor: 100 }, { Valor: -50 }, { Valor: 200 }];
    const r = calcularIntegridade(dados, { valor: 'Valor' }, null, null, null);
    expect(r.checks.find(c => c.nome === 'Classificação automática')).toBeTruthy();
  });

  it('registros traz contagem total e contagem com valor válido', () => {
    const r = calcularIntegridade(DADOS_OK, COLS, null, null, null);
    expect(r.registros.total).toBe(5);
    expect(r.registros.comValor).toBe(5);
  });

  it('dados vazios não quebram (retorna confiança 0% mas estrutura íntegra)', () => {
    const r = calcularIntegridade([], COLS, null, null, null);
    expect(r.checksum).toBe(0);
    expect(r.registros.total).toBe(0);
    expect(typeof r.confianca).toBe('number');
  });
});
