# -*- coding: utf-8 -*-
"""
Central de Automações CR2 — a janela.

Uma tela, um cartão por automação, três botões em cada: Instalar, Abrir,
Atualizar. O que a Central faz de verdade é pouco e é isto:

    * saber quais automações existem          (catalogo.json, vem do GitHub)
    * saber onde cada uma está nesta máquina  (config.json, fica na máquina)
    * clonar, comparar com o GitHub e atualizar   (repos.py)
    * abrir o programa do jeito que ele já abre hoje — pelo .bat dele

O que a Central NÃO faz, de propósito: ela não engole o código dos programas.
Cada automação continua sendo o repositório dela, com o .bat dela, evoluindo
sozinha. Juntar tudo num programa só misturaria as dependências (Selenium,
Tesseract, Pillow) e quebraria caminhos que hoje funcionam.

A JANELA NÃO TRAVA: git é rede, e rede demora. Todo git roda numa thread de
trabalho, que devolve o resultado por uma fila; o Tk esvazia essa fila a cada
120 ms. É o mesmo mecanismo do Gestor de Licitações e do Publicador de
Emendas — quem conhece um, conhece os três.

A THREAD É UMA SÓ, e de propósito: se dois clones de repositório privado
começassem juntos, o Credential Manager poderia abrir duas janelas de login
ao mesmo tempo. Em fila, isso não acontece.
"""

import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

PASTA_SRC = os.path.dirname(os.path.abspath(__file__))
if PASTA_SRC not in sys.path:
    sys.path.insert(0, PASTA_SRC)

import catalogo as cat                                        # noqa: E402
import repos                                                  # noqa: E402
import tema                                                   # noqa: E402

TITULO = "Central de Automações CR2"
ID_CENTRAL = "__central__"


# --------------------------------------------------------------------------
# Registro de erros inesperados
# --------------------------------------------------------------------------
def registrar_erro(exc_type, exc_value, exc_tb):
    texto = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        os.makedirs(os.path.dirname(cat.ARQ_LOG), exist_ok=True)
        with open(cat.ARQ_LOG, "a", encoding="utf-8") as f:
            f.write(texto + "\n" + "-" * 70 + "\n")
    except Exception:
        pass
    try:
        messagebox.showerror(
            TITULO,
            "Ocorreu um erro inesperado:\n\n%s\n\nDetalhes gravados em:\n%s"
            % (exc_value, cat.ARQ_LOG),
        )
    except Exception:
        pass


# --------------------------------------------------------------------------
# O cartão de uma automação
# --------------------------------------------------------------------------
class Cartao(ttk.Frame):
    """Uma automação na tela. Só desenha e avisa a janela; não decide nada.

    O cartão é desenhado para viver numa GRADE de duas colunas, não numa faixa
    de largura total. Por isso o texto tem largura fixa de quebra e as ações
    ficam ancoradas embaixo: numa grade, cartão que cresce conforme o conteúdo
    deixa a fileira desalinhada.
    """

    # Ícone usado quando o catálogo não traz um. Não deixar sem nada: o cartão
    # sem ícone ao lado de cinco com ícone fica com cara de erro.
    ICONE_PADRAO = "\U0001F4E6"          # caixa

    # Largura de quebra do texto, em pixels. Casa com a coluna da grade.
    QUEBRA = 300

    def __init__(self, pai, app, central):
        ttk.Frame.__init__(self, pai, style="Cartao.TFrame", padding=(14, 12))
        self.app = app
        self.central = central
        self.retrato = {}
        self.ocupado = False
        # rótulos cuja quebra acompanha a largura do cartão, com a folga que
        # cada um tem à esquerda (ícone, recuo)
        self._textos = []
        self._quebra_atual = 0

        # As molduras de dentro usam CartaoLinha, sem borda: só o cartão tem
        # contorno. Com o estilo Cartao aqui, cada linha desenhava um retângulo
        # próprio e o cartão virava uma grade.
        topo = ttk.Frame(self, style="CartaoLinha.TFrame")
        topo.pack(fill="x")

        ttk.Label(topo, text=app.icone or self.ICONE_PADRAO,
                  style="CartaoIcone.TLabel").pack(side="left", padx=(0, 10))

        titulos = ttk.Frame(topo, style="CartaoLinha.TFrame")
        titulos.pack(side="left", fill="x", expand=True)
        titulo = ttk.Label(titulos, text=app.nome, style="CartaoTitulo.TLabel",
                           wraplength=self.QUEBRA, justify="left")
        titulo.pack(anchor="w")
        # 64 = ícone (30) + espaço (10) + recuos do cartão (24)
        self._textos.append((titulo, 64))
        self.lbl_estado = ttk.Label(titulos, text="",
                                    style="CartaoSuave.TLabel")
        self.lbl_estado.pack(anchor="w")

        if app.descricao:
            desc = ttk.Label(self, text=app.descricao,
                             style="CartaoSuave.TLabel",
                             wraplength=self.QUEBRA, justify="left")
            desc.pack(anchor="w", pady=(8, 0))
            self._textos.append((desc, 4))
        if app.observacao:
            obs = ttk.Label(self, text="⚠  " + app.observacao,
                            style="CartaoAviso.TLabel",
                            wraplength=self.QUEBRA, justify="left")
            obs.pack(anchor="w", pady=(6, 0))
            self._textos.append((obs, 4))

        # empurra as ações para o rodapé do cartão, alinhando as fileiras
        ttk.Frame(self, style="CartaoLinha.TFrame").pack(fill="both",
                                                        expand=True)

        acoes = ttk.Frame(self, style="CartaoLinha.TFrame")
        acoes.pack(fill="x", pady=(10, 0))
        self.btn = {}
        self.btn["instalar"] = ttk.Button(
            acoes, text="Instalar", style="Acao.TButton",
            command=lambda: central.instalar(self.app))
        self.btn["abrir"] = ttk.Button(
            acoes, text="Abrir", style="Acao.TButton",
            command=lambda: central.abrir(self.app))
        self.btn["atualizar"] = ttk.Button(
            acoes, text="Atualizar", command=lambda: central.atualizar(
                self.app))
        self.btn["pasta"] = ttk.Button(
            acoes, text="Mais  ▾", width=9,
            command=lambda: central.menu_do_cartao(self))
        for nome in ("instalar", "abrir", "atualizar", "pasta"):
            self.btn[nome].pack(side="left", padx=(0, 8))

        self.lbl_versao = ttk.Label(acoes, text="", style="CartaoFraco.TLabel")
        self.lbl_versao.pack(side="right")

        self.bind("<Configure>", self._ajustar_quebra)

    def _ajustar_quebra(self, evento):
        """A quebra do texto acompanha a largura do cartão.

        Sem isto, o cartão numa coluna só (janela estreita) mantinha o texto
        quebrando na largura de duas colunas e sobrava um vazio à direita.

        A comparação com `_quebra_atual` não é economia: mudar wraplength
        redesenha o cartão, o que dispara <Configure> de novo — sem a guarda,
        vira um laço.
        """
        largura = max(evento.width - 28, 180)
        # A guarda é pequena de propósito. Com 10px, a primeira medida (tirada
        # antes de a grade assentar) vinha maior que a definitiva, a diferença
        # ficava abaixo do limite e a correção nunca acontecia — o título do
        # cartão mais comprido saía cortado na borda.
        if abs(largura - self._quebra_atual) < 3:
            return
        self._quebra_atual = largura
        for rotulo, folga in self._textos:
            rotulo.configure(wraplength=max(largura - folga, 140))

    # --------------------------------------------------------------- estado
    def mostrar(self, retrato):
        """Repinta o cartão a partir do retrato devolvido por repos.py."""
        self.retrato = retrato or {}
        self.ocupado = False
        r = self.retrato
        instalado = r.get("instalado")
        atrasado = r.get("atrasado", 0)

        # O sinal é um ponto colorido antes do texto: numa grade de cartões,
        # a cor sozinha se perde, e o texto sozinho não salta.
        if r.get("erro"):
            self._estado("✕  " + r["erro"].split("\n")[0], "Erro.TLabel")
        elif not instalado:
            self._estado("○  não instalado", "CartaoFraco.TLabel")
        elif atrasado:
            self._estado("▲  %d %s no GitHub"
                         % (atrasado,
                            "novidade" if atrasado == 1 else "novidades"),
                         "Alerta.TLabel")
        elif r.get("adiantado"):
            self._estado("▲  com trabalho ainda não enviado",
                         "Alerta.TLabel")
        else:
            self._estado("●  em dia", "Ok.TLabel")

        versao = r.get("versao", "")
        if instalado and r.get("sujo"):
            versao = (versao + "  (alterado)").strip()
        self.lbl_versao.configure(text=versao)

        self._botao("instalar", mostrar=not instalado)
        self._botao("abrir", mostrar=bool(instalado))
        self._botao("atualizar", mostrar=bool(instalado and atrasado))
        self.btn["atualizar"].configure(
            text="Atualizar" if atrasado <= 1 else "Atualizar (%d)" % atrasado)

    def trabalhando(self, texto):
        self.ocupado = True
        self._estado("◌  " + texto, "CartaoSuave.TLabel")
        for b in self.btn.values():
            b.state(["disabled"])

    def _estado(self, texto, estilo):
        self.lbl_estado.configure(text=texto, style=estilo)

    def _botao(self, nome, mostrar):
        b = self.btn[nome]
        if mostrar:
            if not b.winfo_ismapped():
                b.pack(side="left", padx=(0, 8),
                       before=self.btn["pasta"])
            b.state(["!disabled"])
        else:
            b.pack_forget()
        self.btn["pasta"].state(["!disabled"])


# --------------------------------------------------------------------------
# A janela
# --------------------------------------------------------------------------
class Central(tk.Tk):

    # Identidade da janela para o Windows. Sem isto a barra de tarefas agrupa
    # a Central junto de qualquer outro programa em Python e mostra o ícone do
    # Python — e um atalho fixado não reconhece a janela como sendo dele.
    ID_WINDOWS = "CR2.Central.Automacoes"

    def __init__(self):
        tk.Tk.__init__(self)
        self._identificar_no_windows()
        self.title(TITULO)
        self.geometry("940x760")
        self.minsize(700, 520)

        self.cfg = cat.carregar_config()
        self.fila = queue.Queue()          # thread de trabalho -> tela
        self.trabalho = queue.Queue()      # tela -> thread de trabalho
        self.cartoes = {}
        self.pendentes = 0                 # tarefas de app ainda sem resposta
        self.apps = []
        self.retrato_central = {}
        self.erro_catalogo = ""
        # lido uma vez aqui: é leitura de arquivo local, não de rede, e o
        # menu da Central precisa dele para abrir o repositório no navegador.
        self.url_central = repos.endereco_origem(cat.pasta_da_central())

        try:
            self.apps = cat.carregar_catalogo()
        except RuntimeError as e:
            self.erro_catalogo = str(e)

        self._montar()

        self.thread = threading.Thread(target=self._trabalhar, daemon=True)
        self.thread.start()
        self.after(120, self._drenar_fila)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        if not repos.disponivel():
            self._avisar_sem_git()
        elif self.cfg.get("buscar_ao_abrir", True):
            self.verificar_tudo(silencioso=True)
        else:
            self._olhar_local()

    def _identificar_no_windows(self):
        """Diz ao Windows que esta janela é a Central, não "um Python".

        É o que faz a barra de tarefas usar o nosso ícone e o atalho fixado
        apontar para a janela certa. Só existe no Windows; em outro sistema a
        chamada não existe e o programa segue igual.
        """
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                self.ID_WINDOWS)
        except Exception:
            pass

    def _por_o_icone(self):
        """Ícone da janela e da barra de tarefas.

        Usa o logo.ico quando existe: no Windows ele rende ícone nítido em
        todos os tamanhos, porque o arquivo já traz um desenho por tamanho. O
        PNG entra como reserva — é o que funciona fora do Windows.
        """
        ico = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "logo.ico")
        if os.path.isfile(ico):
            try:
                self.iconbitmap(default=ico)
                return True
            except tk.TclError:
                pass
        imagem = self.tema.logo()
        if imagem is not None:
            try:
                self.iconphoto(True, imagem)
                return True
            except tk.TclError:
                pass
        return False

    # ------------------------------------------------------------------ UI
    def _montar(self):
        self.tema = tema.Tema(self, self.cfg.get("tema", "claro"))
        self.tema.aplicar()
        self._por_o_icone()
        self._estilos_extras()
        self._montar_cabecalho()
        self._montar_faixa_central()
        self._montar_lista()
        self._montar_rodape()

    def _estilos_extras(self):
        """Os estilos que só a Central usa. Refeitos a cada troca de tema."""
        c = self.tema.cor
        e = self.tema.estilo
        e.configure("Cartao.TFrame", background=c["superficie"],
                    bordercolor=c["borda"], relief="solid", borderwidth=1)
        e.configure("CartaoLinha.TFrame", background=c["superficie"],
                    relief="flat", borderwidth=0)
        e.configure("Cartao.TLabel", background=c["superficie"],
                    foreground=c["texto"])
        e.configure("CartaoTitulo.TLabel", background=c["superficie"],
                    foreground=c["texto"], font=("Segoe UI", 12, "bold"))
        e.configure("CartaoSuave.TLabel", background=c["superficie"],
                    foreground=c["texto_suave"])
        # O ícone do cartão. Fonte própria porque o emoji do Segoe UI comum
        # sai pequeno demais ao lado de um título em 12.
        e.configure("CartaoIcone.TLabel", background=c["superficie"],
                    foreground=c["destaque"],
                    font=("Segoe UI Emoji", 20))
        # Mais apagado que o Suave: para o hash da versão e o "não instalado",
        # que são informação de canto de olho, não de leitura.
        e.configure("CartaoFraco.TLabel", background=c["superficie"],
                    foreground=c["texto_suave"], font=("Segoe UI", 8))
        e.configure("CartaoAviso.TLabel", background=c["superficie"],
                    foreground=c["alerta"])
        e.configure("Ok.TLabel", background=c["superficie"],
                    foreground=c["ok"])
        e.configure("Alerta.TLabel", background=c["superficie"],
                    foreground=c["alerta"])
        e.configure("Erro.TLabel", background=c["superficie"],
                    foreground=c["erro"])
        # A barra de rolagem ganha estilo próprio por dois motivos: no tema.py
        # o polegar e o trilho recebem a mesma cor (fundo), o que deixa o
        # polegar invisível; e o estilo genérico às vezes não repinta ao
        # alternar o tema — com nome próprio, refeito aqui, sempre repinta.
        e.configure("Central.Vertical.TScrollbar",
                    background=c["borda"], troughcolor=c["fundo"],
                    bordercolor=c["borda"], lightcolor=c["borda"],
                    darkcolor=c["borda"], arrowcolor=c["texto_suave"])
        e.map("Central.Vertical.TScrollbar",
              background=[("active", c["texto_suave"])])

        # a faixa de aviso do topo fica sobre o fundo da janela, não do cartão
        e.configure("Faixa.TFrame", background=c["destaque_suave"])
        e.configure("Faixa.TLabel", background=c["destaque_suave"],
                    foreground=c["texto"])

    def _montar_cabecalho(self):
        """Faixa da marca: logo (ou o nome), título, modo escuro e o crédito."""
        faixa = ttk.Frame(self, style="Marca.TFrame", padding=(12, 8))
        faixa.pack(fill="x")

        imagem = self.tema.logo()
        if imagem is not None:
            marca = ttk.Label(faixa, image=imagem, style="Marca.TLabel")
            marca.image = imagem          # sem isto o Tk descarta a imagem
        else:
            marca = ttk.Label(faixa, text="CR2", style="Marca.TLabel",
                              font=("Segoe UI", 20, "bold"))
        marca.pack(side="left", padx=(0, 12))

        textos = ttk.Frame(faixa, style="Marca.TFrame")
        textos.pack(side="left")
        ttk.Label(textos, text=TITULO, style="Marca.TLabel",
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(textos, text=tema.ASSINATURA, style="MarcaSuave.TLabel",
                  font=("Segoe UI", 9)).pack(anchor="w")

        self.btn_tema = ttk.Button(faixa, text=self._rotulo_tema(),
                                   command=self.alternar_tema, width=14)
        self.btn_tema.pack(side="right")
        self.btn_verificar = ttk.Button(faixa, text="Verificar tudo",
                                        width=16,
                                        command=self.verificar_tudo)
        self.btn_verificar.pack(side="right", padx=(0, 8))
        # A faixa do topo só acende quando existe versão nova da Central.
        # Este botão está sempre aqui: atualizar a própria Central não pode
        # depender de a faixa ter aparecido.
        self.btn_central = ttk.Button(faixa, text="A Central  ▾", width=14,
                                      command=self.menu_da_central)
        self.btn_central.pack(side="right", padx=(0, 8))

    def _montar_faixa_central(self):
        """Aviso do topo. Fica escondido enquanto não há o que dizer."""
        self.faixa = ttk.Frame(self, style="Faixa.TFrame", padding=(12, 8))
        self.faixa_texto = ttk.Label(self.faixa, text="", style="Faixa.TLabel",
                                     wraplength=600, justify="left")
        self.faixa_texto.pack(side="left", fill="x", expand=True)
        self.faixa_botao = ttk.Button(self.faixa, text="", width=22)
        self.faixa_botao.pack(side="right", padx=(8, 0))

    def _mostrar_faixa(self, texto, rotulo_botao=None, comando=None):
        self.faixa_texto.configure(text=texto)
        if rotulo_botao and comando:
            # o !disabled importa: quem clicou em "Atualizar a Central" deixou
            # este botão desligado, e sem isto ele nunca mais voltaria.
            self.faixa_botao.configure(text=rotulo_botao, command=comando)
            self.faixa_botao.state(["!disabled"])
            self.faixa_botao.pack(side="right", padx=(8, 0))
        else:
            self.faixa_botao.pack_forget()
        if not self.faixa.winfo_ismapped():
            self.faixa.pack(fill="x", after=self.winfo_children()[0])

    def _esconder_faixa(self):
        self.faixa.pack_forget()

    # Largura mínima que um cartão precisa para caber numa coluna da grade.
    # Abaixo disso a grade passa a uma coluna só — cartão apertado fica pior
    # do que cartão largo.
    LARGURA_CARTAO = 380

    def _montar_lista(self):
        """Área rolável com os cartões numa grade que reflui."""
        moldura = ttk.Frame(self, padding=(12, 10))
        moldura.pack(fill="both", expand=True)

        self.tela = tk.Canvas(moldura, highlightthickness=0, borderwidth=0)
        barra = ttk.Scrollbar(moldura, orient="vertical",
                              style="Central.Vertical.TScrollbar",
                              command=self.tela.yview)
        self.tela.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tela.pack(side="left", fill="both", expand=True)
        self.tema.registrar(self.tela, "fundo")

        self.dentro = ttk.Frame(self.tela)
        self.janela_dentro = self.tela.create_window(
            (0, 0), window=self.dentro, anchor="nw")
        self.dentro.bind(
            "<Configure>",
            lambda e: self.tela.configure(scrollregion=self.tela.bbox("all")))
        self.tela.bind("<Configure>", self._largura_mudou)
        self.tela.bind_all("<MouseWheel>", self._rolar)

        if self.erro_catalogo:
            ttk.Label(self.dentro, text=self.erro_catalogo,
                      style="Suave.TLabel", wraplength=700,
                      justify="left").pack(anchor="w", pady=20)
            return

        for app in self.apps:
            cartao = Cartao(self.dentro, app, self)
            self.cartoes[app.id] = cartao
            cartao.mostrar({})

        self.colunas_na_tela = 0
        self._dispor(colunas=2)

    def _largura_mudou(self, evento):
        """A janela mudou de tamanho: refaz a grade se o número de colunas mudou.

        Sem isto os cartões ficavam com a largura do conteúdo, não da janela.
        """
        self.tela.itemconfigure(self.janela_dentro, width=evento.width)
        colunas = max(1, min(2, evento.width // self.LARGURA_CARTAO))
        if colunas != getattr(self, "colunas_na_tela", 0):
            self._dispor(colunas)

    def _dispor(self, colunas):
        """Coloca os cartões em `colunas` colunas, todos do mesmo tamanho."""
        self.colunas_na_tela = colunas
        for cartao in self.cartoes.values():
            cartao.grid_forget()
        # zera pesos antigos antes de redistribuir
        for i in range(4):
            self.dentro.columnconfigure(i, weight=0, uniform="")
        for i, cartao in enumerate(self.cartoes.values()):
            cartao.grid(row=i // colunas, column=i % colunas,
                        sticky="nsew", padx=(0, 10), pady=(0, 10))
        # uniform faz as colunas terem exatamente a mesma largura; sem isso,
        # a coluna com o texto mais comprido fica maior e a grade torta
        for c in range(colunas):
            self.dentro.columnconfigure(c, weight=1, uniform="cartoes")
        self.tela.configure(scrollregion=self.tela.bbox("all"))

    def _rolar(self, evento):
        # o Tk do Windows manda 120 por "clique" da rodinha
        self.tela.yview_scroll(int(-evento.delta / 120), "units")

    def _montar_rodape(self):
        rodape = ttk.Frame(self, padding=(12, 6))
        rodape.pack(fill="x")
        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(rodape, textvariable=self.status, anchor="w",
                  style="Suave.TLabel").pack(side="left", fill="x",
                                             expand=True)
        ttk.Label(rodape, text=tema.ASSINATURA,
                  style="Suave.TLabel").pack(side="right", padx=(8, 12))

    def _rotulo_tema(self):
        return "Modo escuro" if self.tema.modo == "claro" else "Modo claro"

    def alternar_tema(self):
        modo = self.tema.alternar()
        self._estilos_extras()
        self.btn_tema.configure(text=self._rotulo_tema())
        self.cfg["tema"] = modo
        cat.salvar_config(self.cfg)
        for cartao in self.cartoes.values():      # repinta o rótulo colorido
            if not cartao.ocupado:
                cartao.mostrar(cartao.retrato)
        self._status("Modo %s." % modo)

    def _status(self, texto):
        self.status.set(texto)

    # -------------------------------------------------------------- ações
    def instalar(self, app):
        pasta = cat.pasta_do_app(app, self.cfg)
        if os.path.isdir(pasta) and os.listdir(pasta):
            if repos.e_repo(pasta):
                self._enfileirar("olhar", app)
                return
            messagebox.showwarning(
                TITULO,
                "Já existe uma pasta com arquivos aqui:\n\n%s\n\n"
                "A Central não vai mexer nela. Apague-a, ou use "
                "\u201cMais \u25be \u2192 Escolher outra pasta\u201d." % pasta)
            return
        self._enfileirar("clonar", app, texto="instalando...")

    def atualizar(self, app):
        cartao = self.cartoes.get(app.id)
        guardar = False
        if cartao and cartao.retrato.get("sujo"):
            resposta = messagebox.askyesno(
                TITULO,
                "Há arquivos alterados dentro da pasta de \u201c%s\u201d.\n\n"
                "A Central pode guardá-los antes de atualizar (git stash) e "
                "eles continuam recuperáveis depois.\n\nGuardar e atualizar?"
                % app.nome)
            if not resposta:
                return
            guardar = True
        self._enfileirar("atualizar", app, extra=guardar,
                         texto="atualizando...")

    def abrir(self, app):
        pasta = cat.pasta_do_app(app, self.cfg)
        dir_programa = app.pasta_do_programa(pasta)
        entrada = os.path.join(dir_programa, app.entrada)
        if not os.path.exists(entrada):
            messagebox.showerror(
                TITULO,
                "O arquivo que abre \u201c%s\u201d não foi encontrado:\n\n%s"
                "\n\nTalvez a automação tenha mudado de nome no repositório. "
                "Atualize a Central e tente de novo." % (app.nome, entrada))
            return
        try:
            self._lancar(app, dir_programa, entrada)
        except OSError as e:
            messagebox.showerror(TITULO, "Não foi possível abrir \u201c%s\u201d:"
                                         "\n\n%s" % (app.nome, e))
            return
        self._status("%s foi aberto." % app.nome)

    def _lancar(self, app, dir_programa, entrada):
        """Abre cada automação do jeito que ela já abre hoje.

        Quando existe um .bat, é ele quem manda: é lá que estão a escolha do
        Python certo e a instalação das dependências na primeira execução. A
        Central não repete essa lógica — só aperta o mesmo botão.
        """
        if os.name != "nt":
            subprocess.Popen([cat.python_de_terminal(), entrada],
                             cwd=dir_programa)
            return
        if entrada.lower().endswith(".bat"):
            subprocess.Popen(["cmd", "/c", "start", "", entrada],
                             cwd=dir_programa, **repos._sem_janela())
        elif app.tipo == "terminal":
            # ferramenta de linha de comando: o console faz parte dela, e
            # /k mantém a janela aberta para a pessoa ler o resultado
            subprocess.Popen(["cmd", "/k", cat.python_de_terminal(), entrada],
                             cwd=dir_programa,
                             creationflags=0x00000010)   # CREATE_NEW_CONSOLE
        else:
            subprocess.Popen([cat.python_de_janela(), entrada],
                             cwd=dir_programa, **repos._sem_janela())

    def verificar_tudo(self, silencioso=False):
        if not repos.disponivel():
            self._avisar_sem_git()
            return
        self._enfileirar_central("buscar")
        for app in self.apps:
            pasta = cat.pasta_do_app(app, self.cfg)
            acao = "buscar" if repos.e_repo(pasta) else "olhar"
            self._enfileirar(acao, app, texto="verificando...")
        self._status("Perguntando ao GitHub o que há de novo...")

    def _olhar_local(self):
        """Só lê o disco, sem tocar na rede."""
        self._enfileirar_central("olhar")
        for app in self.apps:
            self._enfileirar("olhar", app, texto="verificando...")

    # ------------------------------------------------------ menu do cartão
    def menu_do_cartao(self, cartao):
        app = cartao.app
        pasta = cat.pasta_do_app(app, self.cfg)
        c = self.tema.cor
        menu = tk.Menu(self, tearoff=0, background=c["superficie"],
                       foreground=c["texto"],
                       activebackground=c["selecao"],
                       activeforeground=c["selecao_texto"],
                       borderwidth=1, relief="solid")
        if cartao.retrato.get("novidades"):
            menu.add_command(
                label="Ver o que mudou",
                command=lambda: self.ver_novidades(app.nome, cartao.retrato))
            menu.add_separator()
        menu.add_command(label="Abrir a pasta no Explorer",
                         command=lambda: self.abrir_pasta(pasta),
                         state=("normal" if os.path.isdir(pasta)
                                else "disabled"))
        menu.add_command(label="Escolher outra pasta...",
                         command=lambda: self.escolher_pasta(app))
        if (self.cfg.get("caminhos") or {}).get(app.id):
            menu.add_command(label="Voltar para a pasta padrão",
                             command=lambda: self.voltar_pasta(app))
        menu.add_separator()
        menu.add_command(label="Ver no GitHub",
                         command=lambda: webbrowser.open(app.url_github))
        try:
            menu.tk_popup(cartao.btn["pasta"].winfo_rootx(),
                          cartao.btn["pasta"].winfo_rooty() + 30)
        finally:
            menu.grab_release()

    def ver_novidades(self, nome, retrato):
        janela = tk.Toplevel(self)
        janela.title("O que mudou — %s" % nome)
        janela.geometry("640x420")
        janela.transient(self)
        moldura = ttk.Frame(janela, padding=12)
        moldura.pack(fill="both", expand=True)
        ttk.Label(moldura, wraplength=600, justify="left",
                  text="Estas são as mudanças que ainda não estão nesta "
                       "máquina, da mais nova para a mais antiga:").pack(
                           anchor="w", pady=(0, 8))
        texto = tk.Text(moldura, wrap="word", height=16, borderwidth=1)
        texto.pack(fill="both", expand=True)
        for linha in retrato.get("novidades", []):
            texto.insert("end", "\u2022  %s\n" % linha)
        restantes = retrato.get("atrasado", 0) - len(
            retrato.get("novidades", []))
        if restantes > 0:
            texto.insert("end", "\n... e mais %d.\n" % restantes)
        texto.configure(state="disabled")
        self.tema.registrar(texto, "superficie")
        ttk.Button(moldura, text="Fechar", command=janela.destroy).pack(
            anchor="e", pady=(10, 0))

    def abrir_pasta(self, pasta):
        if os.path.isdir(pasta):
            os.startfile(pasta) if os.name == "nt" else None

    def escolher_pasta(self, app):
        """Aponta a Central para um clone que já existe nesta máquina."""
        escolhida = filedialog.askdirectory(
            title="Onde está \u201c%s\u201d nesta máquina?" % app.nome)
        if not escolhida:
            return
        escolhida = os.path.normpath(escolhida)
        if not repos.e_repo(escolhida):
            if not messagebox.askyesno(
                    TITULO,
                    "Esta pasta não é um clone do git:\n\n%s\n\n"
                    "A Central conseguirá abrir o programa, mas não conseguirá "
                    "atualizá-lo.\n\nUsar assim mesmo?" % escolhida):
                return
        else:
            try:
                repos.conferir_origem(escolhida, app.repo)
            except repos.ErroGit as e:
                messagebox.showerror(TITULO, str(e))
                return
        cat.fixar_pasta(app, self.cfg, escolhida)
        self._enfileirar("olhar", app, texto="verificando...")
        self._status("\u201c%s\u201d agora aponta para %s"
                     % (app.nome, escolhida))

    def voltar_pasta(self, app):
        cat.esquecer_pasta(app, self.cfg)
        self._enfileirar("olhar", app, texto="verificando...")

    # ------------------------------------------------------------- Central
    def menu_da_central(self):
        """Tudo sobre a própria Central — inclusive atualizá-la.

        A faixa do topo só acende quando existe versão nova. Este menu está
        sempre disponível: conferir ou forçar a atualização da Central não
        pode depender de a faixa ter aparecido.
        """
        retrato = self.retrato_central
        c = self.tema.cor
        menu = tk.Menu(self, tearoff=0, background=c["superficie"],
                       foreground=c["texto"],
                       activebackground=c["selecao"],
                       activeforeground=c["selecao_texto"],
                       borderwidth=1, relief="solid")
        if retrato.get("versao"):
            menu.add_command(label="Versão instalada:  %s"
                                   % retrato["versao"], state="disabled")
            menu.add_separator()
        menu.add_command(label="Verificar se há versão nova",
                         command=self.verificar_central)
        menu.add_command(label="Atualizar a Central",
                         command=self.atualizar_central)
        if retrato.get("novidades"):
            menu.add_command(
                label="Ver o que mudou",
                command=lambda: self.ver_novidades("a Central", retrato))
        menu.add_separator()
        menu.add_command(
            label="Abrir a pasta da Central no Explorer",
            command=lambda: self.abrir_pasta(cat.pasta_da_central()))
        menu.add_command(label="Ver no GitHub",
                         command=self.central_no_github,
                         state=("normal" if self.url_central else "disabled"))
        try:
            menu.tk_popup(self.btn_central.winfo_rootx(),
                          self.btn_central.winfo_rooty() + 30)
        finally:
            menu.grab_release()

    def central_no_github(self):
        url = self.url_central
        if url.endswith(".git"):
            url = url[:-4]
        if url:
            webbrowser.open(url)

    def _mostrar_estado_central(self, retrato, avisar=False):
        """Acende (ou apaga) a faixa do topo.

        `avisar` é verdadeiro quando a pessoa pediu a verificação pelo menu:
        aí o resultado precisa aparecer mesmo quando não há nada de novo —
        senão o clique parece não ter feito nada.
        """
        self.retrato_central = retrato or {}
        atrasado = self.retrato_central.get("atrasado", 0)
        if atrasado:
            self._mostrar_faixa(
                "A própria Central tem %d %s no GitHub — pode incluir "
                "automações novas no catálogo."
                % (atrasado, "atualização" if atrasado == 1
                   else "atualizações"),
                "Atualizar a Central", self.atualizar_central)
            if avisar:
                self._status("A Central tem versão nova — o aviso está no "
                             "alto da janela.")
            return
        self._esconder_faixa()
        if not avisar:
            return
        if self.retrato_central.get("erro"):
            self._status("A Central não pôde ser verificada: %s"
                         % self.retrato_central["erro"].split("\n")[0])
        elif not self.retrato_central.get("instalado"):
            self._avisar_central_sem_git()
        else:
            self._status("A Central já está na versão mais nova.")

    def verificar_central(self):
        if not repos.disponivel():
            self._avisar_sem_git()
            return
        if not repos.e_repo(cat.pasta_da_central()):
            self._avisar_central_sem_git()
            return
        self._status("Perguntando ao GitHub se a Central tem versão nova...")
        self._enfileirar_central("buscar", avisar=True)

    def atualizar_central(self):
        if not repos.disponivel():
            self._avisar_sem_git()
            return
        if not repos.e_repo(cat.pasta_da_central()):
            self._avisar_central_sem_git()
            return
        # mesma conversa dos cartões: se há arquivo mexido na pasta da
        # Central (um catalogo.json editado à mão, por exemplo), o git
        # recusaria o pull — então a Central oferece guardar antes.
        guardar = False
        if self.retrato_central.get("sujo"):
            if not messagebox.askyesno(
                    TITULO,
                    "Há arquivos alterados dentro da pasta da Central.\n\n"
                    "Ela pode guardá-los antes de atualizar (git stash) e "
                    "eles continuam recuperáveis depois.\n\nGuardar e "
                    "atualizar?"):
                return
            guardar = True
        self.faixa_botao.state(["disabled"])
        self._status("Atualizando a Central...")
        self._enfileirar_central("atualizar", avisar=True, extra=guardar)

    def _avisar_central_sem_git(self):
        messagebox.showinfo(
            TITULO,
            "Esta cópia da Central não é um clone do git, então ela não "
            "consegue se atualizar sozinha.\n\nA pasta é:\n\n%s\n\n"
            "Para ganhar atualização automática, apague-a e clone o "
            "repositório da Central com o Git para Windows."
            % cat.pasta_da_central())

    def _avisar_sem_git(self):
        self._mostrar_faixa(
            "O git não está instalado nesta máquina. Sem ele a Central abre "
            "as automações que já estão aqui, mas não consegue instalar nem "
            "atualizar nenhuma.",
            "Como instalar",
            lambda: webbrowser.open("https://git-scm.com/download/win"))

    # ------------------------------------------------- fila e thread
    def _enfileirar(self, acao, app, extra=None, texto=None):
        cartao = self.cartoes.get(app.id)
        if cartao:
            cartao.trabalhando(texto or "aguarde...")
        self.pendentes += 1
        self.trabalho.put({
            "acao": acao,
            "id": app.id,
            "nome": app.nome,
            "pasta": cat.pasta_do_app(app, self.cfg),
            "url": app.repo,
            "extra": extra,
        })

    def _enfileirar_central(self, acao, avisar=False, extra=None):
        """`avisar`: a pessoa pediu pelo menu, então quer ver o resultado.

        A verificação de fundo (ao abrir a janela, ou no Verificar tudo) vem
        com avisar=False e fica calada quando não há nada de novo.
        """
        self.trabalho.put({
            "acao": acao,
            "id": ID_CENTRAL,
            "nome": "a Central",
            "pasta": cat.pasta_da_central(),
            "url": "",
            "extra": extra,
            "avisar": avisar,
        })

    def _trabalhar(self):
        """A thread de trabalho. Roda uma tarefa por vez, para sempre."""
        while True:
            tarefa = self.trabalho.get()
            if tarefa is None:
                return
            try:
                self._executar(tarefa)
            except repos.ErroGit as e:
                self.fila.put(("erro", tarefa, str(e)))
            except Exception:
                self.fila.put(("erro", tarefa,
                               traceback.format_exc(limit=2)))

    def _executar(self, tarefa):
        acao, pasta = tarefa["acao"], tarefa["pasta"]
        if acao == "clonar":
            self.fila.put(("status", "Baixando %s do GitHub..."
                           % tarefa["nome"]))
            repos.clonar(tarefa["url"], pasta)
            self.fila.put(("status", "%s foi instalado." % tarefa["nome"]))
        elif acao == "buscar":
            if repos.e_repo(pasta):
                repos.buscar(pasta)
        elif acao == "atualizar":
            veio = repos.atualizar(pasta,
                                   guardar_mudancas=bool(tarefa["extra"]))
            # frase sem gênero: o mesmo texto serve para "a Central" e para
            # "Gestor de Licitações".
            self.fila.put(("status",
                           "%s está na versão nova." % tarefa["nome"] if veio
                           else "%s já estava na versão mais nova."
                           % tarefa["nome"]))
            if tarefa["id"] == ID_CENTRAL and veio:
                self.fila.put(("central-atualizada", tarefa, None))
                return
        self.fila.put(("estado", tarefa, repos.situacao(pasta)))

    def _drenar_fila(self):
        """Esvazia a fila da thread. Só aqui a tela é tocada."""
        try:
            while True:
                tipo, *resto = self.fila.get_nowait()
                if tipo == "status":
                    self._status(resto[0])
                elif tipo == "estado":
                    tarefa, retrato = resto
                    self._aplicar_estado(tarefa, retrato)
                elif tipo == "erro":
                    tarefa, mensagem = resto
                    self._aplicar_erro(tarefa, mensagem)
                elif tipo == "central-atualizada":
                    self._central_atualizada(bool(resto[0].get("extra")))
        except queue.Empty:
            pass
        self.after(120, self._drenar_fila)

    def _aplicar_estado(self, tarefa, retrato):
        if tarefa["id"] == ID_CENTRAL:
            self._mostrar_estado_central(retrato, tarefa.get("avisar"))
            return
        cartao = self.cartoes.get(tarefa["id"])
        if cartao:
            cartao.mostrar(retrato)
        self._baixa_pendente()

    def _aplicar_erro(self, tarefa, mensagem):
        if tarefa["id"] == ID_CENTRAL:
            self.faixa_botao.state(["!disabled"])
            self._status("A Central não pôde ser %s: %s"
                         % ("atualizada" if tarefa["acao"] == "atualizar"
                            else "verificada", mensagem.split("\n")[0]))
            # a atualização foi um clique da pessoa: o erro merece uma
            # caixa, senão ela fica sem saber por que nada aconteceu.
            if tarefa["acao"] == "atualizar":
                messagebox.showerror(
                    TITULO, "A Central não pôde ser atualizada:\n\n%s"
                    % mensagem)
            return
        cartao = self.cartoes.get(tarefa["id"])
        if cartao:
            cartao.mostrar(dict(repos.situacao(tarefa["pasta"]),
                                erro=mensagem))
        # clonar e atualizar são ações que a pessoa pediu: o erro merece
        # uma caixa. Verificação de fundo só acende o rótulo do cartão.
        if tarefa["acao"] in ("clonar", "atualizar"):
            messagebox.showerror(
                TITULO, "%s — %s:\n\n%s"
                % (tarefa["nome"],
                   "instalação" if tarefa["acao"] == "clonar"
                   else "atualização", mensagem))
        self._status("Problema em %s." % tarefa["nome"])
        self._baixa_pendente(resumir=False)

    def _baixa_pendente(self, resumir=True):
        """Uma tarefa de app respondeu. Na última, o rodapé vira o resumo."""
        self.pendentes = max(0, self.pendentes - 1)
        if self.pendentes == 0 and resumir:
            self._resumir()

    def _resumir(self):
        pendentes = sum(1 for c in self.cartoes.values()
                        if c.retrato.get("atrasado"))
        faltando = sum(1 for c in self.cartoes.values()
                       if not c.retrato.get("instalado"))
        partes = []
        if pendentes:
            partes.append("%d com atualização disponível" % pendentes)
        if faltando:
            partes.append("%d não instalada(s)" % faltando)
        self._status("Tudo em dia." if not partes else " | ".join(partes))

    def _central_atualizada(self, guardou=False):
        """O recado do fim. Quando houve stash, ele diz como voltar.

        Sem esta parte a pessoa vê a pasta na versão do GitHub, sem os
        arquivos que ela tinha mexido, e conclui que perdeu o trabalho.
        """
        self._esconder_faixa()
        recado = ("A Central foi atualizada.\n\nFeche e abra de novo "
                  "para a versão nova entrar no lugar — inclusive o "
                  "catálogo, que pode ter automações novas.")
        if guardou:
            recado += ("\n\nOs arquivos que estavam alterados foram "
                       "guardados com o git stash — nada foi perdido. "
                       "Para trazê-los de volta, rode nesta pasta:\n\n"
                       "    git stash pop")
        messagebox.showinfo(TITULO, recado)

    def _fechar(self):
        cat.salvar_config(self.cfg)
        self.destroy()


def main():
    sys.excepthook = registrar_erro
    Central().mainloop()


if __name__ == "__main__":
    main()
