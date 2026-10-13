"""Lê os boletos de condomínio (PDF da Aliança) de uma pasta e gera o relatório.

Uso:  python extrair.py [pasta]      (sem pasta, usa a pasta atual)
Gera na própria pasta: relatorio.html, dados.csv e dados.json.
"""
import csv
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

# Junto do script, ou dentro do executável gerado pelo PyInstaller
RECURSOS = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
MODELO = RECURSOS / "relatorio_modelo.html"

# Agrupamento das rubricas do boleto (código -> grupo)
GRUPOS = {
    "00260": "Água (seu consumo)",
    "00106": "Gás (seu consumo)",
    "00120": "Condomínio (taxa ordinária)",
    "02516": "Condomínio (taxa ordinária)",
    "00052": "Energia das áreas comuns",
    "00233": "Energia das áreas comuns",
    "02161": "Água comum e purificação",
    "02423": "Água comum e purificação",
    "00083": "Rateios e extras",
    "00084": "Rateios e extras",
    "00090": "Rateios e extras",
    "00195": "Rateios e extras",
    "02479": "Rateios e extras",
    "02498": "Rateios e extras",
    "02791": "Rateios e extras",
    "00024": "Reservas (salão, gourmet)",
    "02201": "Reservas (salão, gourmet)",
    "02363": "Reservas (salão, gourmet)",
    "00122": "Tarifa bancária",
}

MOEDA = r"\d{1,3}(?:\.\d{3})*,\d{2}"


class BoletoInvalido(Exception):
    pass


def num(s):
    return float(s.replace(".", "").replace(",", "."))


def dec(s):
    return float(s.replace(",", "."))


def texto(pdf):
    return "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)


def ler_medidor(desc):
    """Retorna (leitura_atual, consumo_m3) a partir da descrição da rubrica."""
    m = re.search(r"\(L:([\d,]+)\s*/C:([\d,]+)\)", desc)
    if m:  # formato atual: (L:357,7670/C:19,8020)
        return dec(m.group(1)), dec(m.group(2))
    m = re.search(r"\s(\d+,\d{3})\s+\(.*LEIT:([\d,]+)/([\d,]+)", desc)
    if m:  # formato antigo: 17,160 (AGUA- LEIT:159,0870/176,2470)
        return dec(m.group(3)), dec(m.group(1))
    return None, None


def ler_boleto(pdf):
    t = texto(pdf)
    comp = re.search(r"COMPETÊNCIA:\s*(\d{2})/(\d{4})", t)
    total = re.search(r"VALOR DO DOCUMENTO\s+(" + MOEDA + ")", t)
    if not (comp and total and "DESCRIÇÃO DAS TAXAS" in t):
        raise BoletoInvalido(f"{pdf.name} não parece um boleto de condomínio da Aliança")
    condominio = re.search(r"CONDOMÍNIO\s*:\s*\d+-(.+?)\s+NRO\.DOC", t)
    unidade = re.search(r"ECONOMIA\s*:\s*(.+?)\s+NOSSO", t)
    secao = t.split("DESCRIÇÃO DAS TAXAS", 1)[1].split("-----", 1)[0]

    itens, buf = [], ""
    for linha in secao.strip().splitlines():
        buf = (buf + " " + linha.strip()).strip()
        m = re.match(r"^(\d{5})-(.*?)\s+(" + MOEDA + r")$", buf)
        if m:
            itens.append({"codigo": m.group(1), "descricao": m.group(2), "valor": num(m.group(3))})
            buf = ""

    b = {
        "arquivo": pdf.name,
        "competencia": f"{comp.group(2)}-{comp.group(1)}",
        "condominio": condominio.group(1).strip() if condominio else "",
        "unidade": unidade.group(1).strip() if unidade else "",
        "total": num(total.group(1)),
        "itens": itens,
        "grupos": {},
    }
    soma = round(sum(i["valor"] for i in itens), 2)
    if abs(soma - b["total"]) > 0.01:
        raise BoletoInvalido(f"{pdf.name}: os itens somam {soma:.2f}, mas o boleto diz {b['total']:.2f}")

    for i in itens:
        g = i["grupo"] = GRUPOS.get(i["codigo"], "Outros")
        b["grupos"][g] = round(b["grupos"].get(g, 0) + i["valor"], 2)
        if i["codigo"] in ("00260", "00106"):
            chave = "agua" if i["codigo"] == "00260" else "gas"
            leitura, m3 = ler_medidor(i["descricao"])
            if not m3:
                raise BoletoInvalido(f"{pdf.name}: não consegui ler os m³ de {i['descricao']}")
            b[chave] = {"valor": i["valor"], "m3": m3, "leitura": leitura, "preco_m3": round(i["valor"] / m3, 4)}
    if "agua" not in b or "gas" not in b:
        raise BoletoInvalido(f"{pdf.name}: o boleto não tem as cobranças de água e gás")
    return b


def ler_pasta(pasta):
    """Lê todos os PDFs da pasta. Retorna (boletos por competência, avisos)."""
    boletos, avisos = {}, []
    for pdf in sorted(Path(pasta).glob("*.pdf")):
        try:
            b = ler_boleto(pdf)
        except BoletoInvalido as e:
            avisos.append(f"Ignorado: {e}")
            continue
        except Exception as e:  # PDF corrompido, protegido etc.
            avisos.append(f"Ignorado: {pdf.name} ({e})")
            continue
        anterior = boletos.get(b["competencia"])
        if anterior:
            if anterior["total"] != b["total"]:
                avisos.append(f"{pdf.name} e {anterior['arquivo']} são do mesmo mês com valores diferentes; usei {anterior['arquivo']}")
            anterior.setdefault("duplicados", []).append(pdf.name)
            continue
        boletos[b["competencia"]] = b
    return [boletos[k] for k in sorted(boletos)], avisos


def gravar_csv(lista, destino):
    grupos = sorted(set(GRUPOS.values()) | {g for b in lista for g in b["grupos"]})
    br = lambda x: "" if x is None else f"{x:.4f}".rstrip("0").rstrip(".").replace(".", ",")
    with open(destino, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["competencia", "total", "agua_m3", "agua_R$", "agua_R$/m3", "gas_m3", "gas_R$", "gas_R$/m3"] + grupos)
        for b in lista:
            a, g = b["agua"], b["gas"]
            w.writerow([b["competencia"], br(b["total"]), br(a["m3"]), br(a["valor"]), br(a["preco_m3"]),
                        br(g["m3"]), br(g["valor"]), br(g["preco_m3"])] + [br(b["grupos"].get(k, 0)) for k in grupos])


def gerar(pasta):
    """Gera relatorio.html, dados.csv e dados.json na pasta. Retorna (caminho do html, boletos, avisos)."""
    pasta = Path(pasta)
    lista, avisos = ler_pasta(pasta)
    if not lista:
        raise BoletoInvalido("Nenhum boleto de condomínio encontrado nessa pasta.")
    (pasta / "dados.json").write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")
    gravar_csv(lista, pasta / "dados.csv")
    html = MODELO.read_text(encoding="utf-8").replace("/*DADOS*/[]", json.dumps(lista, ensure_ascii=False))
    cabeca = '<!doctype html>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    destino = pasta / "relatorio.html"
    destino.write_text(cabeca + html, encoding="utf-8")
    return destino, lista, avisos


def main():
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    destino, lista, avisos = gerar(pasta)
    for b in lista:
        a, g = b["agua"], b["gas"]
        dup = f"  (duplicado: {', '.join(b['duplicados'])})" if b.get("duplicados") else ""
        print(f"{b['competencia']}  total {b['total']:8.2f} | água {a['m3']:6.3f} m³ R$ {a['valor']:7.2f} "
              f"({a['preco_m3']:.4f}/m³) | gás {g['m3']:6.3f} m³ R$ {g['valor']:7.2f} ({g['preco_m3']:.4f}/m³){dup}")
    for aviso in avisos:
        print(aviso)
    print(f"Relatório: {destino}")


if __name__ == "__main__":
    main()
