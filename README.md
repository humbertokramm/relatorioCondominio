# Relatório do Condomínio

Lê os boletos de condomínio em PDF emitidos pela **Aliança Administradora** (Porto Alegre) e gera um relatório que separa, para água e gás, o que mudou por **consumo** e o que mudou por **preço** do m³.

O relatório mostra:

- consumo de água e gás por mês (m³) e o preço cobrado por m³;
- a variação de cada boleto dividida em "por consumo" e "por preço";
- a composição do boleto (taxa ordinária, rateios, reservas, energia das áreas comuns etc.);
- os rateios e extras item a item, com parcela atual, quando termina e quanto falta pagar.

## Como usar (Windows)

1. Baixe o `RelatorioCondominio.exe` na página de [Releases](../../releases/latest).
2. Salve os boletos em PDF numa pasta (o nome dos arquivos não importa; boletos repetidos são contados uma vez).
3. Abra o programa, clique em **Selecionar pasta dos boletos** e escolha a pasta.

O relatório (`relatorio.html`) é salvo na mesma pasta e abre no navegador. Junto ficam `dados.csv` (para abrir no Excel) e `dados.json`.

Nada sai do seu computador: os boletos são lidos localmente.

> O Windows pode mostrar o aviso "O Windows protegeu o computador" porque o executável não é assinado. Clique em **Mais informações → Executar assim mesmo**.

## Pela linha de comando

Requer Python 3.10+ e `pypdf`:

```bash
pip install pypdf
python extrair.py "C:\caminho\da\pasta\dos\boletos"
```

## Gerar o executável

```bash
pip install pypdf pyinstaller
pyinstaller --onefile --windowed --name RelatorioCondominio --add-data "relatorio_modelo.html;." app.py
```

O executável fica em `dist\RelatorioCondominio.exe`.

## Arquivos

- `extrair.py`: lê os PDFs e gera os dados e o relatório.
- `relatorio_modelo.html`: modelo do relatório (os dados são inseridos no lugar de `/*DADOS*/[]`).
- `app.py`: janela com o botão de selecionar pasta.

Os códigos das rubricas (00260 água, 00106 gás etc.) seguem o padrão dos boletos da Aliança. Rubricas desconhecidas aparecem no grupo "Outros".
