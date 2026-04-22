/**
 * analise.js — Motor de análise financeira no navegador
 * Equivalente JavaScript do toolkit_financeiro.py
 * Sem dependências externas — puro JavaScript
 */

// ══════════════════════════════════════════════════════
// DETECÇÃO DE COLUNAS
// ══════════════════════════════════════════════════════

const PADROES_COLUNAS = {
  valor:      /valor|total|amount|price|preco|receita|despesa|saldo|liquido|bruto|montante/i,
  data:       /^(data|date|emiss[aã]o|lan[cç]amento|compet[eê]ncia|registro)/i,
  vencimento: /vencimento|vencto|due|prazo|venc\b/i,
  categoria:  /categoria|category|tipo|type|natureza|hist[oó]rico|descri[cç][aã]o|conta\b/i,
  entidade:   /cliente|fornecedor|customer|supplier|nome|name|empresa|parceiro|favorecido/i,
  chave:      /^(nf|nfe|numero|n[uú]mero|id\b|doc|documento|chave|key|c[oó]digo|pedido)/i,
};

function detectarColunas(headers) {
  const cols = {};
  for (const [tipo, regex] of Object.entries(PADROES_COLUNAS)) {
    cols[tipo] = headers.find(h => regex.test(String(h).trim())) || null;
  }
  return cols;
}

// ══════════════════════════════════════════════════════
// UTILITÁRIOS
// ══════════════════════════════════════════════════════

function toNum(v) {
  if (v === null || v === undefined || v === '') return NaN;
  if (typeof v === 'number') return v;
  const s = String(v).replace(/R\$\s?/g,'').replace(/\./g,'').replace(',','.').trim();
  return parseFloat(s);
}

function toDate(v) {
  if (!v) return null;
  if (v instanceof Date) return isNaN(v) ? null : v;
  // Número serial do Excel
  if (typeof v === 'number') {
    const d = new Date(Math.round((v - 25569) * 86400 * 1000));
    return isNaN(d) ? null : d;
  }
  const s = String(v).trim();
  // DD/MM/YYYY
  const br = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) return new Date(+br[3], +br[2]-1, +br[1]);
  const d = new Date(s);
  return isNaN(d) ? null : d;
}

function fmtBRL(v) {
  if (isNaN(v) || v === null) return '—';
  return new Intl.NumberFormat('pt-BR', { style:'currency', currency:'BRL' }).format(v);
}

function fmtNum(v, dec=0) {
  if (isNaN(v) || v === null) return '—';
  return new Intl.NumberFormat('pt-BR', { minimumFractionDigits:dec, maximumFractionDigits:dec }).format(v);
}

function fmtData(d) {
  if (!d) return '—';
  return d.toLocaleDateString('pt-BR');
}

// ══════════════════════════════════════════════════════
// MÓDULO 1: AUDITORIA
// ══════════════════════════════════════════════════════

function auditoria(dados, cols) {
  const problemas = [];
  const hoje = new Date();

  // Duplicatas por chave
  if (cols.chave) {
    const contagem = {};
    dados.forEach((row, i) => {
      const k = String(row[cols.chave] ?? '').trim();
      if (!k) return;
      if (!contagem[k]) contagem[k] = [];
      contagem[k].push(i + 2);
    });
    for (const [k, linhas] of Object.entries(contagem)) {
      if (linhas.length > 1) {
        problemas.push({
          severidade: 'CRÍTICA', tipo: 'DUPLICATA',
          coluna: cols.chave, linha: linhas.join(', '),
          valor: k,
          descricao: `"${k}" aparece ${linhas.length}x — possível lançamento duplicado`,
        });
      }
    }
  }

  // Campos obrigatórios vazios
  const obrigatorias = [cols.valor, cols.data, cols.chave].filter(Boolean);
  for (const col of obrigatorias) {
    const vazios = dados.map((r, i) => [r, i]).filter(([r]) => {
      const v = r[col];
      return v === null || v === undefined || v === '';
    }).map(([,i]) => i + 2);
    if (vazios.length > 0) {
      problemas.push({
        severidade: 'ALTA', tipo: 'CAMPO_VAZIO',
        coluna: col, linha: vazios.slice(0,5).join(', ') + (vazios.length > 5 ? '...' : ''),
        valor: `${vazios.length} registros`,
        descricao: `${vazios.length} linha(s) sem "${col}" preenchido`,
      });
    }
  }

  // Outliers (±3σ) na coluna de valor
  if (cols.valor) {
    const nums = dados.map(r => toNum(r[cols.valor])).filter(n => !isNaN(n));
    if (nums.length > 4) {
      const media = nums.reduce((a,b)=>a+b,0) / nums.length;
      const desvio = Math.sqrt(nums.map(n=>(n-media)**2).reduce((a,b)=>a+b,0)/nums.length);
      const limSup = media + 3*desvio;
      const limInf = media - 3*desvio;
      dados.forEach((row, i) => {
        const v = toNum(row[cols.valor]);
        if (!isNaN(v) && (v > limSup || v < limInf)) {
          problemas.push({
            severidade: 'MÉDIA', tipo: 'OUTLIER',
            coluna: cols.valor, linha: i + 2,
            valor: fmtBRL(v),
            descricao: `Valor fora do padrão (média ${fmtBRL(media)}, ±3σ = ${fmtBRL(desvio)})`,
          });
        }
      });
    }
  }

  // Datas futuras
  if (cols.data) {
    dados.forEach((row, i) => {
      const d = toDate(row[cols.data]);
      if (d && d > hoje) {
        problemas.push({
          severidade: 'ALTA', tipo: 'DATA_FUTURA',
          coluna: cols.data, linha: i + 2,
          valor: fmtData(d),
          descricao: `Data futura: ${fmtData(d)} — possível erro de digitação`,
        });
      }
    });
  }

  // Receita negativa
  if (cols.valor && cols.categoria) {
    dados.forEach((row, i) => {
      const cat = String(row[cols.categoria] ?? '').toUpperCase();
      const v   = toNum(row[cols.valor]);
      if (/RECEITA|VENDA|FATURAMENTO/.test(cat) && v < 0) {
        problemas.push({
          severidade: 'ALTA', tipo: 'CLASSIFICAÇÃO_ERRADA',
          coluna: cols.valor, linha: i + 2,
          valor: fmtBRL(v),
          descricao: `Receita com valor negativo — possível estorno não tratado`,
        });
      }
    });
  }

  // Ordenar: CRÍTICA → ALTA → MÉDIA → BAIXA
  const ord = { 'CRÍTICA':0, 'ALTA':1, 'MÉDIA':2, 'BAIXA':3 };
  return problemas.sort((a,b) => (ord[a.severidade]??4) - (ord[b.severidade]??4));
}

// ══════════════════════════════════════════════════════
// MÓDULO 2: AGING
// ══════════════════════════════════════════════════════

function calcularAging(dados, colVenc, colValor) {
  if (!colVenc || !colValor) return null;
  const hoje = new Date(); hoje.setHours(0,0,0,0);
  const faixas = {
    'A vencer':         { min:-Infinity, max:-1,  qtd:0, total:0 },
    'Vencido 1-30d':    { min:0,         max:30,  qtd:0, total:0 },
    'Vencido 31-60d':   { min:31,        max:60,  qtd:0, total:0 },
    'Vencido 61-90d':   { min:61,        max:90,  qtd:0, total:0 },
    'Vencido +90d':     { min:91,        max:Infinity, qtd:0, total:0 },
    'Sem data':         { min:null,      max:null, qtd:0, total:0 },
  };

  dados.forEach(row => {
    const d = toDate(row[colVenc]);
    const v = toNum(row[colValor]);
    if (isNaN(v)) return;
    if (!d) { faixas['Sem data'].qtd++; faixas['Sem data'].total += v; return; }
    const dias = Math.floor((hoje - d) / 86400000);
    for (const [nome, f] of Object.entries(faixas)) {
      if (nome === 'Sem data') continue;
      if (dias >= f.min && dias <= f.max) {
        f.qtd++; f.total += v; break;
      }
    }
  });

  const totalGeral = Object.values(faixas).reduce((s,f)=>s+f.total, 0);
  return Object.entries(faixas)
    .filter(([,f]) => f.qtd > 0)
    .map(([nome, f]) => ({
      faixa: nome, qtd: f.qtd,
      total: f.total,
      pct: totalGeral ? (f.total / totalGeral * 100) : 0,
    }));
}

// ══════════════════════════════════════════════════════
// MÓDULO 3: PARETO
// ══════════════════════════════════════════════════════

function calcularPareto(dados, colEntidade, colValor, top = 15) {
  if (!colEntidade || !colValor) return null;
  const mapa = {};
  dados.forEach(row => {
    const ent = String(row[colEntidade] ?? '').trim() || '(sem nome)';
    const v   = toNum(row[colValor]);
    if (!isNaN(v)) mapa[ent] = (mapa[ent] || 0) + v;
  });
  const lista = Object.entries(mapa)
    .map(([nome, total]) => ({ nome, total }))
    .sort((a,b) => b.total - a.total);
  const totalGeral = lista.reduce((s,i)=>s+i.total, 0);
  let acum = 0;
  return lista.slice(0, top).map((item, idx) => {
    const pct = totalGeral ? item.total / totalGeral * 100 : 0;
    acum += pct;
    return { ranking: idx+1, nome: item.nome, total: item.total,
             pct, acumulado: acum, classe: acum <= 80 ? 'A' : 'B' };
  });
}

// ══════════════════════════════════════════════════════
// MÓDULO 4: DRE
// ══════════════════════════════════════════════════════

const MAPA_DRE = [
  { linha:'Receita Bruta',              termos:/RECEITA|VENDA|FATURAMENTO/ },
  { linha:'(-) Deduções',               termos:/DEDU[CÇ]|IMPOSTO.*VENDA|DEVOLU|ABATIMENTO|PIS|COFINS|ISS|ICMS/ },
  { linha:'(-) CMV/CPV',                termos:/CMV|CPV|CUSTO.*MERCADORIA|CUSTO.*PRODUTO|CUSTO.*VARI/ },
  { linha:'(-) Despesas Operacionais',  termos:/DESPESA.*(ADM|COMERCIAL|OPERACIONAL|GERAL)|SALARIO|ALUGUEL/ },
  { linha:'(-/+) Resultado Financeiro', termos:/FINANCEI|JUROS|CAMBIAL/ },
  { linha:'(-) IR\/CSLL',              termos:/\bIR\b|IRPJ|CSLL|IMPOSTO.*RENDA|CONTRIBUI.*SOCIAL/ },
];

function construirDRE(dados, colCat, colValor) {
  if (!colCat || !colValor) return null;
  const valores = {};
  MAPA_DRE.forEach(({ linha }) => { valores[linha] = 0; });

  dados.forEach(row => {
    const cat = String(row[colCat] ?? '').toUpperCase().trim();
    const v   = toNum(row[colValor]);
    if (isNaN(v)) return;
    for (const { linha, termos } of MAPA_DRE) {
      if (termos.test(cat)) { valores[linha] += v; break; }
    }
  });

  const rb  = valores['Receita Bruta'];
  const ded = Math.abs(valores['(-) Deduções']);
  const rl  = rb - ded;
  const cmv = Math.abs(valores['(-) CMV/CPV']);
  const lb  = rl - cmv;
  const dop = Math.abs(valores['(-) Despesas Operacionais']);
  const ebit= lb - dop;
  const rf  = valores['(-/+) Resultado Financeiro'];
  const lair= ebit + rf;
  const ir  = Math.abs(valores['(-) IR/CSLL']);
  const ll  = lair - ir;

  const linhas = [
    { linha:'Receita Bruta',                    valor:rb,   tipo:'input' },
    { linha:'(-) Deduções',                     valor:-ded, tipo:'input' },
    { linha:'(=) Receita Líquida',              valor:rl,   tipo:'total' },
    { linha:'(-) CMV/CPV',                      valor:-cmv, tipo:'input' },
    { linha:'(=) Lucro Bruto',                  valor:lb,   tipo:'total' },
    { linha:'(-) Despesas Operacionais',        valor:-dop, tipo:'input' },
    { linha:'(=) EBIT (Resultado Operacional)', valor:ebit, tipo:'total' },
    { linha:'(-/+) Resultado Financeiro',       valor:rf,   tipo:'input' },
    { linha:'(=) Resultado antes IR/CSLL',      valor:lair, tipo:'total' },
    { linha:'(-) IR/CSLL',                      valor:-ir,  tipo:'input' },
    { linha:'(=) Lucro Líquido',                valor:ll,   tipo:'total lucro' },
  ];
  return linhas.map(l => ({ ...l, av: rl ? (l.valor/rl*100) : 0 }));
}

// ══════════════════════════════════════════════════════
// MÓDULO 5: KPIs RESUMO
// ══════════════════════════════════════════════════════

function calcularKPIs(dados, cols) {
  const valores = dados.map(r => toNum(r[cols.valor])).filter(n => !isNaN(n));
  const datas   = cols.data ? dados.map(r => toDate(r[cols.data])).filter(Boolean) : [];
  const total   = valores.reduce((a,b)=>a+b, 0);
  const ticket  = valores.length ? total / valores.length : 0;
  const minData = datas.length ? new Date(Math.min(...datas)) : null;
  const maxData = datas.length ? new Date(Math.max(...datas)) : null;

  return {
    totalRegistros: dados.length,
    totalValor:     total,
    ticketMedio:    ticket,
    periodoInicio:  minData,
    periodoFim:     maxData,
    colsDetectadas: Object.values(cols).filter(Boolean).length,
  };
}

// Exportar para uso no app.js
if (typeof module !== 'undefined') {
  module.exports = { detectarColunas, auditoria, calcularAging, calcularPareto, construirDRE, calcularKPIs, fmtBRL, fmtNum, fmtData, toNum, toDate };
}
