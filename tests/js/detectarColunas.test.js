import { describe, it, expect } from 'vitest';
import { detectarColunas } from './helpers/extract-analise.js';

describe('detectarColunas', () => {
  it('detects valor column', () => {
    const cols = detectarColunas(['NF', 'Cliente', 'Valor', 'Data', 'Vencimento']);
    expect(cols.valor).toBe('Valor');
  });

  it('detects data column', () => {
    const cols = detectarColunas(['NF', 'Cliente', 'Valor', 'Data', 'Vencimento']);
    expect(cols.data).toBe('Data');
  });

  it('detects vencimento column', () => {
    const cols = detectarColunas(['NF', 'Cliente', 'Valor', 'Data', 'Vencimento']);
    expect(cols.vencimento).toBe('Vencimento');
  });

  it('detects entidade from Cliente', () => {
    const cols = detectarColunas(['NF', 'Cliente', 'Valor', 'Data', 'Vencimento']);
    expect(cols.entidade).toBe('Cliente');
  });

  it('detects entidade from Fornecedor', () => {
    const cols = detectarColunas(['NF', 'Fornecedor', 'Valor', 'Data', 'Vencimento']);
    expect(cols.entidade).toBe('Fornecedor');
  });

  it('detects chave from NF', () => {
    const cols = detectarColunas(['NF', 'Cliente', 'Valor', 'Data', 'Vencimento']);
    expect(cols.chave).toBe('NF');
  });

  it('detects chave from Numero', () => {
    const cols = detectarColunas(['Numero', 'Cliente', 'Valor', 'Data', 'Vencimento']);
    expect(cols.chave).toBe('Numero');
  });

  it('returns null for unrecognized columns', () => {
    const cols = detectarColunas(['coluna_desconhecida_xyz', 'outra_estranha_abc']);
    expect(cols.valor).toBeNull();
    expect(cols.data).toBeNull();
    expect(cols.entidade).toBeNull();
  });

  it('handles case-insensitive matching for VALOR', () => {
    const cols = detectarColunas(['VALOR', 'DATA', 'VENCIMENTO']);
    expect(cols.valor).toBe('VALOR');
  });

  it('handles case-insensitive matching for DATA', () => {
    const cols = detectarColunas(['VALOR', 'DATA', 'VENCIMENTO']);
    expect(cols.data).toBe('DATA');
  });

  it('handles typical ERP headers (OMIE style)', () => {
    const headers = ['numero_documento', 'nome_cliente', 'valor_documento', 'data_emissao', 'data_vencimento'];
    const cols = detectarColunas(headers);
    expect(cols.valor).toBe('valor_documento');
    expect(cols.data).toBe('data_emissao');
    expect(cols.vencimento).toBe('data_vencimento');
    expect(cols.entidade).toBe('nome_cliente');
    expect(cols.chave).toBe('numero_documento');
  });

  it('detects receita as valor column', () => {
    const cols = detectarColunas(['receita', 'data', 'cliente']);
    expect(cols.valor).toBe('receita');
  });

  it('detects total as valor column', () => {
    const cols = detectarColunas(['total', 'data', 'cliente']);
    expect(cols.valor).toBe('total');
  });
});
