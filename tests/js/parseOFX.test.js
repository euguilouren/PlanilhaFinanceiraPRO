import { describe, it, expect } from 'vitest';
import { parseOFX } from './helpers/extract-analise.js';

// Minimal OFX SGML (sem aspas em tags, padrão real de bancos brasileiros)
const OFX_VALIDO = `
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKACCTFROM>
<BANKID>0001
<ACCTID>123456
</BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20240115120000[-3:BRT]
<TRNAMT>1500.50
<FITID>TX001
<MEMO>Salário Empresa XYZ
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240116
<TRNAMT>-250.00
<FITID>TX002
<MEMO>Compra Supermercado
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>`;

describe('parseOFX', () => {
  it('lança erro quando bloco <OFX> está ausente', () => {
    expect(() => parseOFX('arquivo sem marca ofx')).toThrow(/inválido/i);
  });

  it('lança erro quando não há transações', () => {
    expect(() => parseOFX('<OFX></OFX>')).toThrow(/transação/i);
  });

  it('retorna headers fixos esperados pelo dashboard', () => {
    const { headers } = parseOFX(OFX_VALIDO);
    expect(headers).toEqual(['Data', 'Vencimento', 'Valor', 'Descrição', 'ID', 'Tipo']);
  });

  it('parseia múltiplas transações preservando ordem', () => {
    const { dados } = parseOFX(OFX_VALIDO);
    expect(dados).toHaveLength(2);
    expect(dados[0].ID).toBe('TX001');
    expect(dados[1].ID).toBe('TX002');
  });

  it('converte data OFX YYYYMMDD para DD/MM/YYYY', () => {
    const { dados } = parseOFX(OFX_VALIDO);
    expect(dados[0].Data).toBe('15/01/2024');
    expect(dados[1].Data).toBe('16/01/2024');
  });

  it('aceita também ISO YYYY-MM-DD', () => {
    const ofx = `<OFX><STMTTRN><DTPOSTED>2024-03-20<TRNAMT>100<FITID>X</STMTTRN></OFX>`;
    const { dados } = parseOFX(ofx);
    expect(dados[0].Data).toBe('20/03/2024');
  });

  it('mapeia TRNTYPE para CRÉDITO/DÉBITO', () => {
    const { dados } = parseOFX(OFX_VALIDO);
    expect(dados[0].Tipo).toBe('CRÉDITO');
    expect(dados[1].Tipo).toBe('DÉBITO');
  });

  it('extrai valor numérico positivo e negativo', () => {
    const { dados } = parseOFX(OFX_VALIDO);
    expect(dados[0].Valor).toBe(1500.50);
    expect(dados[1].Valor).toBe(-250);
  });

  it('usa MEMO como descrição quando disponível', () => {
    const { dados } = parseOFX(OFX_VALIDO);
    expect(dados[0].Descrição).toMatch(/Salário/);
    expect(dados[1].Descrição).toMatch(/Supermercado/);
  });

  it('sintetiza FITID quando ausente, sem colidir entre transações', () => {
    const ofx = `<OFX>
      <STMTTRN><DTPOSTED>20240101<TRNAMT>50</STMTTRN>
      <STMTTRN><DTPOSTED>20240101<TRNAMT>50</STMTTRN>
    </OFX>`;
    const { dados } = parseOFX(ofx);
    expect(dados[0].ID).not.toBe(dados[1].ID);
  });

  it('decodifica entidades HTML em campos', () => {
    const ofx = `<OFX><STMTTRN><DTPOSTED>20240101<TRNAMT>10<FITID>X<MEMO>Caf&#233; &amp; Cia</STMTTRN></OFX>`;
    const { dados } = parseOFX(ofx);
    expect(dados[0].Descrição).toBe('Café & Cia');
  });

  it('Data e Vencimento são iguais no OFX (mesma data de postagem)', () => {
    const { dados } = parseOFX(OFX_VALIDO);
    expect(dados[0].Data).toBe(dados[0].Vencimento);
  });
});
