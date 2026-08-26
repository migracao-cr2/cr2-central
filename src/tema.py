# -*- coding: utf-8 -*-
"""
Aparência do programa: cores, modo claro/escuro e logo.

>>> AS CORES ESTÃO TODAS AQUI. É O ÚNICO ARQUIVO A MEXER PARA MUDAR A MARCA. <<<

ATENÇÃO — PALETA PROVISÓRIA
A única cor que se conseguiu confirmar da CR2 é o cinza-azulado #CFD4DB, usado
como borda no site cr2.co. O restante desta paleta é uma composição neutra e
profissional construída em volta dele: nada aqui foi copiado de um manual de
marca, porque não havia um disponível.

Para deixar a identidade correta, troque os valores de COR_MARCA abaixo pelos
hexadecimais oficiais. Nada mais precisa mudar: todo o resto é derivado.

LOGO
Ponha o arquivo em  logo.png  na pasta do programa (a mesma do app.py). Ele é
carregado sozinho e redimensionado para caber na barra de título. Sem o
arquivo, aparece o nome "CR2" escrito, e o programa funciona igual.
"""

import os
import tkinter as tk
from tkinter import ttk

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
ARQ_LOGO = os.path.join(PASTA_BASE, "logo.png")

ASSINATURA = "Desenvolvido por Mauricio"

# --------------------------------------------------------------------------
# A marca. TROQUE AQUI pelos hexadecimais oficiais da CR2.
# --------------------------------------------------------------------------
COR_MARCA = {
    # cor principal, usada nos botões de ação e no cabeçalho
    "primaria": "#1F4E79",
    # variação mais clara, para o modo escuro (precisa contrastar com fundo escuro)
    "primaria_clara": "#4D8FD1",
    # única cor confirmada do site cr2.co
    "neutra": "#CFD4DB",
}

# --------------------------------------------------------------------------
# As duas paletas. Contraste conferido: texto sobre fundo acima de 7:1, e
# texto suave acima de 4,5:1 — legível também em tela ruim de escritório.
# --------------------------------------------------------------------------
CLARO = {
    "nome": "claro",
    "fundo": "#F4F6F9",
    "superficie": "#FFFFFF",
    "borda": COR_MARCA["neutra"],
    "texto": "#1B2430",
    "texto_suave": "#5B6672",
    "destaque": COR_MARCA["primaria"],
    "destaque_texto": "#FFFFFF",
    "destaque_suave": "#E3ECF6",
    "cabecalho_fundo": COR_MARCA["primaria"],
    "cabecalho_texto": "#FFFFFF",
    "linha_alternada": "#F7F9FC",
    "selecao": COR_MARCA["primaria"],
    "selecao_texto": "#FFFFFF",
    "alerta": "#8A5300",
    "erro": "#A32020",
    "ok": "#1E6B3A",
}

ESCURO = {
    "nome": "escuro",
    "fundo": "#161A1F",
    "superficie": "#1E242B",
    "borda": "#2C343D",
    "texto": "#E6EAEE",
    "texto_suave": "#9AA5B1",
    "destaque": COR_MARCA["primaria_clara"],
    "destaque_texto": "#0F1418",
    "destaque_suave": "#243447",
    "cabecalho_fundo": "#12171C",
    "cabecalho_texto": "#E6EAEE",
    "linha_alternada": "#222A32",
    "selecao": COR_MARCA["primaria_clara"],
    "selecao_texto": "#0F1418",
    "alerta": "#E0A93B",
    "erro": "#E8736B",
    "ok": "#6BC48A",
}

PALETAS = {"claro": CLARO, "escuro": ESCURO}

# Altura máxima do logo na barra de título, em pixels.
ALTURA_LOGO = 44


class Tema:
    """Guarda a paleta em uso e sabe repintar a janela inteira.

    Os widgets do tk puro (tk.Text, tk.Canvas) não seguem o ttk.Style: cada um
    tem de ser repintado na mão. Por isso eles se registram aqui em
    registrar(), e trocar de tema repinta todos de uma vez — inclusive os que
    foram criados depois, como a janela de ajuda.
    """

    def __init__(self, raiz, modo="claro"):
        self.raiz = raiz
        self.cor = PALETAS.get(modo, CLARO)
        self.estilo = ttk.Style(raiz)
        self._registrados = []          # (widget, papel)
        self._logo = None               # PhotoImage precisa de referência viva

    # ------------------------------------------------------------- paleta
    @property
    def modo(self):
        return self.cor["nome"]

    def alternar(self):
        """Troca claro <-> escuro e repinta tudo. Devolve o modo novo."""
        self.cor = ESCURO if self.modo == "claro" else CLARO
        self.aplicar()
        return self.modo

    def registrar(self, widget, papel="superficie"):
        """Widget de tk puro que precisa ser repintado a cada troca de tema.

        papel: "superficie" (caixa de texto), "fundo" (moldura) ou "suave"
        (texto secundário).
        """
        self._registrados.append((widget, papel))
        self._pintar_um(widget, papel)
        return widget

    # ------------------------------------------------------------ aplicar
    def aplicar(self):
        c = self.cor
        # "clam" é o único tema do ttk que aceita cor em tudo. O "vista" ignora
        # background em botão e em cabeçalho de tabela, e o modo escuro saía
        # pela metade — cinza claro no meio do escuro.
        try:
            self.estilo.theme_use("clam")
        except tk.TclError:
            pass

        self.raiz.configure(background=c["fundo"])
        e = self.estilo

        e.configure(".", background=c["fundo"], foreground=c["texto"],
                    fieldbackground=c["superficie"], bordercolor=c["borda"],
                    lightcolor=c["borda"], darkcolor=c["borda"],
                    troughcolor=c["fundo"], focuscolor=c["destaque"])

        e.configure("TFrame", background=c["fundo"])
        e.configure("TLabel", background=c["fundo"], foreground=c["texto"])
        e.configure("Suave.TLabel", background=c["fundo"],
                    foreground=c["texto_suave"])
        e.configure("TLabelframe", background=c["fundo"],
                    bordercolor=c["borda"])
        e.configure("TLabelframe.Label", background=c["fundo"],
                    foreground=c["texto_suave"])
        e.configure("TPanedwindow", background=c["fundo"])
        e.configure("TCheckbutton", background=c["fundo"],
                    foreground=c["texto"])
        e.map("TCheckbutton",
              background=[("active", c["fundo"])],
              indicatorcolor=[("selected", c["destaque"])])

        # ---- botões ----
        e.configure("TButton", background=c["superficie"],
                    foreground=c["texto"], bordercolor=c["borda"],
                    padding=(10, 6), relief="flat")
        e.map("TButton",
              background=[("pressed", c["destaque_suave"]),
                          ("active", c["destaque_suave"]),
                          ("disabled", c["fundo"])],
              foreground=[("disabled", c["texto_suave"])])

        # botão dos três passos: é a ação principal, então leva a cor da marca
        e.configure("Acao.TButton", background=c["destaque"],
                    foreground=c["destaque_texto"], padding=(10, 6),
                    relief="flat", bordercolor=c["destaque"])
        e.map("Acao.TButton",
              background=[("pressed", c["cabecalho_fundo"]),
                          ("active", c["destaque"]),
                          ("disabled", c["borda"])],
              foreground=[("disabled", c["texto_suave"])])

        # ---- campos ----
        for nome in ("TEntry", "TCombobox"):
            e.configure(nome, fieldbackground=c["superficie"],
                        foreground=c["texto"], bordercolor=c["borda"],
                        insertcolor=c["texto"], arrowcolor=c["texto_suave"],
                        padding=3)
            e.map(nome,
                  fieldbackground=[("readonly", c["superficie"]),
                                   ("disabled", c["fundo"])],
                  foreground=[("disabled", c["texto_suave"])])
        # a lista suspensa do Combobox é uma janela do tk puro, e só obedece
        # a estas opções globais
        self.raiz.option_add("*TCombobox*Listbox.background", c["superficie"])
        self.raiz.option_add("*TCombobox*Listbox.foreground", c["texto"])
        self.raiz.option_add("*TCombobox*Listbox.selectBackground",
                             c["selecao"])
        self.raiz.option_add("*TCombobox*Listbox.selectForeground",
                             c["selecao_texto"])

        # ---- tabela ----
        e.configure("Treeview", background=c["superficie"],
                    fieldbackground=c["superficie"], foreground=c["texto"],
                    bordercolor=c["borda"], rowheight=24)
        e.map("Treeview",
              background=[("selected", c["selecao"])],
              foreground=[("selected", c["selecao_texto"])])
        e.configure("Treeview.Heading", background=c["destaque_suave"],
                    foreground=c["texto"], relief="flat", padding=(6, 4))
        e.map("Treeview.Heading",
              background=[("active", c["destaque_suave"])])

        # ---- barras ----
        e.configure("TScrollbar", background=c["fundo"],
                    troughcolor=c["fundo"], bordercolor=c["borda"],
                    arrowcolor=c["texto_suave"])
        e.configure("TProgressbar", background=c["destaque"],
                    troughcolor=c["destaque_suave"], bordercolor=c["borda"])

        # ---- cabeçalho da marca ----
        e.configure("Marca.TFrame", background=c["cabecalho_fundo"])
        e.configure("Marca.TLabel", background=c["cabecalho_fundo"],
                    foreground=c["cabecalho_texto"])
        e.configure("MarcaSuave.TLabel", background=c["cabecalho_fundo"],
                    foreground=c["cabecalho_texto"])

        for widget, papel in list(self._registrados):
            self._pintar_um(widget, papel)

    def _pintar_um(self, widget, papel):
        c = self.cor
        try:
            if not widget.winfo_exists():
                return
        except tk.TclError:
            return
        fundo = c["superficie"] if papel == "superficie" else c["fundo"]
        frente = c["texto_suave"] if papel == "suave" else c["texto"]
        try:
            widget.configure(background=fundo, foreground=frente,
                             insertbackground=c["texto"],
                             selectbackground=c["selecao"],
                             selectforeground=c["selecao_texto"],
                             highlightthickness=1,
                             highlightbackground=c["borda"],
                             highlightcolor=c["destaque"], relief="flat")
        except tk.TclError:
            # widget sem alguma dessas opções (Canvas, por exemplo)
            try:
                widget.configure(background=fundo)
            except tk.TclError:
                pass

    # --------------------------------------------------------------- logo
    def logo(self):
        """PhotoImage do logo.png, já reduzido. None quando não há arquivo.

        Usa só o tkinter: PNG é lido nativamente pelo Tk 8.6, e a redução é
        por subsample (número inteiro). Sem Pillow aqui de propósito — a barra
        de título não é lugar para depender de biblioteca externa.
        """
        if self._logo is not None:
            return self._logo
        if not os.path.isfile(ARQ_LOGO):
            return None
        try:
            imagem = tk.PhotoImage(file=ARQ_LOGO)
        except tk.TclError:
            return None
        altura = imagem.height()
        if altura > ALTURA_LOGO:
            fator = max(1, int(round(altura / float(ALTURA_LOGO))))
            imagem = imagem.subsample(fator, fator)
        self._logo = imagem
        return self._logo
