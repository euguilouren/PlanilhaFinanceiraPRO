import { describe, it, expect } from 'vitest';
import { calcularFluxoPeriodo } from './helpers/extract-analise.js';

describe('calcularFluxoPeriodo', () => {
  it('agrupa por mês corretamente', () => {
    const dados = [
      { Data: '15/01/2024', Valor: 1000, Tipo: 'RECEITA' },
      { Data: '20/01/2024', Valor: -300, Tipo: 'DESPESA' },
      { Data: '10/02/2024', Valor: 500,  Tipo: 'RECEITA' },
    ];
    const r = calcularFluxoPeriodo(dados, 'Data', 'Valor', 'Tipo', 'M');
    expect(r).toHaveLength(2);
    expect(r[0].periodo).toBe('01/2024');
    expect(r[1].periodo).toBe('02/2024');
  });

  it('ordena ascendente por data', () => {
    const dados = [
      { Data: '15/03/2024', Valor: 100, Tipo: 'RECEITA' },
      { Data: '10/01/2024', Valor: 200, Tipo: 'RECEITA' },
      { Data: '20/02/2024', Valor: 300, Tipo: 'RECEITA' },
    ];
    const r = calcularFluxoPeriodo(dados, 'Data', 'Valor', 'Tipo', 'M');
    expect(r.map(x => x.periodo)).toEqual(['01/2024', '02/2024', '03/2024']);
  });

  // Regressão: o grupo era criado ANTES da validação do valor, então
  // datas com valor inválido/zero produziam períodos fantasma em R$ 0.
  it('NÃO cria período fantasma quando todos os valores do mês são inválidos', () => {
    const dados = [
      { Data: '15/01/2024', Valor: 'abc',  Tipo: 'RECEITA' },
      { Data: '20/01/2024', Valor: 0,      Tipo: 'DESPESA' },
      { Data: '10/02/2024', Valor: 500,    Tipo: 'RECEITA' },
    ];
    const r = calcularFluxoPeriodo(dados, 'Data', 'Valor', 'Tipo', 'M');
    expect(r).toHaveLength(1);
    expect(r[0].periodo).toBe('02/2024');
  });

  it('NÃO cria período fantasma quando todos os valores são zero', () => {
    const dados = [
      { Data: '01/01/2024', Valor: 0, Tipo: 'RECEITA' },
      { Data: '02/01/2024', Valor: 0, Tipo: 'DESPESA' },
    ];
    const r = calcularFluxoPeriodo(dados, 'Data', 'Valor', 'Tipo', 'M');
    expect(r).toHaveLength(0);
  });

  it('mantém período quando pelo menos uma linha tem valor válido', () => {
    const dados = [
      { Data: '01/01/2024', Valor: 0,    Tipo: 'RECEITA' },
      { Data: '02/01/2024', Valor: 100,  Tipo: 'RECEITA' },
    ];
    const r = calcularFluxoPeriodo(dados, 'Data', 'Valor', 'Tipo', 'M');
    expect(r).toHaveLength(1);
    expect(r[0].receita).toBe(100);
    expect(r[0].nfRec).toBe(1);
  });

  it('freq diária produz DD/MM/YYYY', () => {
    const r = calcularFluxoPeriodo(
      [{ Data: '15/03/2024', Valor: 100, Tipo: 'RECEITA' }],
      'Data', 'Valor', 'Tipo', 'D'
    );
    expect(r[0].periodo).toBe('15/03/2024');
  });

  it('freq anual produz YYYY', () => {
    const r = calcularFluxoPeriodo(
      [{ Data: '15/03/2024', Valor: 100, Tipo: 'RECEITA' }],
      'Data', 'Valor', 'Tipo', 'A'
    );
    expect(r[0].periodo).toBe('2024');
  });

  it('ignora linhas com data inválida', () => {
    const dados = [
      { Data: 'lixo',       Valor: 100, Tipo: 'RECEITA' },
      { Data: '01/01/2024', Valor: 200, Tipo: 'RECEITA' },
    ];
    const r = calcularFluxoPeriodo(dados, 'Data', 'Valor', 'Tipo', 'M');
    expect(r).toHaveLength(1);
  });
});
