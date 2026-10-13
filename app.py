"""Janela do Relatório do Condomínio: escolhe a pasta dos boletos e abre o relatório."""
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, ttk

from extrair import BoletoInvalido, gerar


class App:
    def __init__(self, raiz):
        self.raiz = raiz
        raiz.title("Relatório do Condomínio")
        raiz.geometry("520x300")
        raiz.minsize(420, 240)

        quadro = ttk.Frame(raiz, padding=20)
        quadro.pack(fill="both", expand=True)
        ttk.Label(quadro, text="Relatório do Condomínio", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(quadro, wraplength=470, justify="left",
                  text="Escolha a pasta onde estão os boletos em PDF. O relatório é salvo nessa "
                       "mesma pasta (relatorio.html) e abre no navegador.").pack(anchor="w", pady=(6, 14))
        self.botao = ttk.Button(quadro, text="Selecionar pasta dos boletos…", command=self.escolher)
        self.botao.pack(anchor="w")
        self.status = tk.Text(quadro, height=7, wrap="word", relief="flat", font=("Segoe UI", 9),
                              background=raiz.cget("background"))
        self.status.pack(fill="both", expand=True, pady=(14, 0))
        self.mostrar("")

    def mostrar(self, texto):
        self.status.configure(state="normal")
        self.status.delete("1.0", "end")
        self.status.insert("1.0", texto)
        self.status.configure(state="disabled")

    def escolher(self):
        pasta = filedialog.askdirectory(title="Pasta com os boletos em PDF")
        if not pasta:
            return
        self.botao.state(["disabled"])
        self.mostrar(f"Lendo os boletos de {pasta}…")
        threading.Thread(target=self.processar, args=(pasta,), daemon=True).start()

    def processar(self, pasta):
        try:
            destino, lista, avisos = gerar(pasta)
            def ok():
                meses = f"{lista[0]['competencia']} a {lista[-1]['competencia']}"
                linhas = [f"{len(lista)} boletos lidos ({meses}).", f"Relatório salvo em {destino}"] + avisos
                self.mostrar("\n".join(linhas))
                webbrowser.open(destino.as_uri())
            self.raiz.after(0, ok)
        except BoletoInvalido as e:
            msg = str(e)
            self.raiz.after(0, lambda: self.mostrar(msg))
        except Exception as e:
            msg = f"Não foi possível gerar o relatório: {e}"
            self.raiz.after(0, lambda: self.mostrar(msg))
        finally:
            self.raiz.after(0, lambda: self.botao.state(["!disabled"]))


if __name__ == "__main__":
    raiz = tk.Tk()
    app = App(raiz)
    # Pasta arrastada sobre o ícone do programa (ou passada na linha de comando)
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir():
        app.botao.state(["disabled"])
        app.mostrar(f"Lendo os boletos de {sys.argv[1]}…")
        threading.Thread(target=app.processar, args=(sys.argv[1],), daemon=True).start()
    raiz.mainloop()
