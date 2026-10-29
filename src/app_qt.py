# -*- coding: utf-8 -*-
"""
Central de Automações CR2 — a janela, em Qt.

É a mesma Central do app.py (Tkinter), com outra roupa. O que ela faz de
verdade continua sendo pouco e é isto:

    * saber quais automações existem          (catalogo.json, vem do GitHub)
    * saber onde cada uma está nesta máquina  (config.json, fica na máquina)
    * clonar, comparar com o GitHub e atualizar   (repos.py)
    * abrir o programa do jeito que ele já abre hoje — pelo .bat dele

Nenhuma regra mora aqui: catálogo, configuração e git continuam nos mesmos
módulos da interface antiga. Se o PySide6 faltar nesta máquina, o
central.bat abre o app.py, que faz exatamente o mesmo.

A JANELA NÃO TRAVA: git é rede, e rede demora. O git roda em threads de
trabalho (as mesmas 12 do app.py, com uma trava por pasta), que devolvem o
resultado por um sinal Qt — o Qt entrega o sinal na thread da janela, e só
lá a tela é tocada. As threads são daemon de propósito: fechar a janela no
meio de um "Verificar tudo" encerra o processo na hora, em vez de esperar
o GitHub responder a todas.
"""

import json
import os
import tempfile
import queue
import subprocess
import sys
import threading
import time
import traceback
import webbrowser

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QWindow
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
    QVBoxLayout, QWidget,
)

PASTA_SRC = os.path.dirname(os.path.abspath(__file__))
if PASTA_SRC not in sys.path:
    sys.path.insert(0, PASTA_SRC)

import catalogo as cat                                        # noqa: E402
import repos                                                  # noqa: E402
import tema_qt as tq                                          # noqa: E402

TITULO = "Central de Automações CR2"
ID_CENTRAL = "__central__"
ID_WINDOWS = "CR2.Central.Automacoes"

# Quantas conversas com o GitHub ao mesmo tempo. Medido em 29/10/2026 com 12
# automações instaladas: uma por vez 30,6 s; 6 juntas 10,4 s; 12 juntas 4,8 s.
TRABALHADORES = 12


def caminho_recurso(*partes):
    """Arquivo que vai junto: na pasta da Central ou dentro do .exe."""
    raiz = getattr(sys, "_MEIPASS", os.path.dirname(PASTA_SRC))
    return os.path.join(raiz, *partes)


class Ponte(QObject):
    """Por onde as threads de trabalho falam com a janela.

    O objeto nasce na thread da janela; um sinal emitido de outra thread é
    entregue em fila, na thread da janela. É o papel que a fila + after(120)
    fazem no app.py.
    """
    recado = Signal(object)


# --------------------------------------------------------------------------
# O cartão de uma automação
# --------------------------------------------------------------------------
class Cartao(QFrame):
    """Uma automação na tela. Só desenha e avisa a janela; não decide nada."""

    acao = Signal(str, object)

    # Ícone usado quando o catálogo não traz um. Não deixar sem nada: o cartão
    # sem ícone ao lado de cinco com ícone fica com cara de erro.
    ICONE_PADRAO = "\U0001F4E6"          # caixa

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.retrato = {}
        self.ocupado = False
        self.setObjectName("card")
        self.setMinimumWidth(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Minimum)

        caixa = QVBoxLayout(self)
        caixa.setContentsMargins(20, 18, 20, 16)
        caixa.setSpacing(11)

        topo = QHBoxLayout()
        self.icone = QLabel(app.icone or self.ICONE_PADRAO)
        self.icone.setObjectName("cardIcon")
        self.icone.setFixedWidth(38)
        topo.addWidget(self.icone, 0, Qt.AlignmentFlag.AlignTop)

        titulos = QVBoxLayout()
        titulos.setSpacing(3)
        self.titulo = QLabel(app.nome)
        self.titulo.setObjectName("cardTitle")
        self.titulo.setWordWrap(True)
        self.estado = QLabel("○  Aguardando verificação")
        self.estado.setObjectName("stateMuted")
        self.estado.setWordWrap(True)
        titulos.addWidget(self.titulo)
        titulos.addWidget(self.estado)
        topo.addLayout(titulos, 1)
        caixa.addLayout(topo)

        texto = app.descricao
        if app.observacao:
            texto += "\n\n" + app.observacao
        self.descricao = QLabel(texto)
        self.descricao.setObjectName("description")
        self.descricao.setWordWrap(True)
        self.descricao.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.descricao.setMinimumHeight(64)
        caixa.addWidget(self.descricao, 1)

        rodape = QHBoxLayout()
        rodape.setSpacing(8)
        self.principal = QPushButton("Instalar")
        self.principal.setObjectName("primary")
        self.principal.clicked.connect(self._principal)
        self.atualizar = QPushButton("Atualizar")
        self.atualizar.clicked.connect(
            lambda: self.acao.emit("atualizar", self.app))
        self.mais = QPushButton("Mais  ▾")
        self.mais.clicked.connect(lambda: self.acao.emit("menu", self.app))
        self.versao = QLabel("")
        self.versao.setObjectName("version")
        rodape.addWidget(self.principal)
        rodape.addWidget(self.atualizar)
        rodape.addWidget(self.mais)
        rodape.addStretch(1)
        rodape.addWidget(self.versao)

        # Programa aberto dentro da Central: o andamento dele, aqui no menu.
        self.andamento = QWidget()
        self.andamento.setObjectName("caixa")
        linha_and = QHBoxLayout(self.andamento)
        linha_and.setContentsMargins(0, 0, 0, 0)
        self.andamento_texto = QLabel("")
        self.andamento_texto.setObjectName("stateMuted")
        self.andamento_barra = QProgressBar()
        self.andamento_barra.setFixedWidth(140)
        linha_and.addWidget(self.andamento_texto, 1)
        linha_and.addWidget(self.andamento_barra)
        self.andamento.hide()
        caixa.addWidget(self.andamento)
        caixa.addLayout(rodape)
        self.aberto = False
        self.mostrar({})
        self._estado("○  Aguardando verificação", "stateMuted")

    def _principal(self):
        if self.aberto:
            self.acao.emit("ir", self.app)
            return
        acao = "abrir" if self.retrato.get("instalado") else "instalar"
        self.acao.emit(acao, self.app)

    def mostrar_andamento(self, aberto, ocupado=False, pct=None, texto=""):
        """O programa está aberto na Central? Rodando? Quanto falta?"""
        self.aberto = aberto
        self.andamento.setVisible(aberto)
        if aberto:
            self.principal.setText("Ir para o programa")
            if len(texto) > 70:
                texto = texto[:68].rstrip() + "…"
            if ocupado and pct is not None:
                texto = "%d%%  ·  %s" % (pct, texto or "trabalhando…")
            rotulo = ("⟳  " + (texto or "trabalhando…")) if ocupado \
                else "●  Aberto na Central"
            self.andamento_texto.setText(rotulo)
            self.andamento_barra.setVisible(ocupado)
            if ocupado and pct is not None:
                self.andamento_barra.setRange(0, 100)
                self.andamento_barra.setValue(pct)
                self.andamento_barra.setFormat("%d%%" % pct)
            elif ocupado:
                self.andamento_barra.setRange(0, 0)     # andando, sem total
        else:
            self.principal.setText("Abrir" if self.retrato.get("instalado")
                                   else "Instalar")

    def _estado(self, texto, estilo):
        self.estado.setText(texto)
        self.estado.setObjectName(estilo)
        self.style().unpolish(self.estado)
        self.style().polish(self.estado)

    def trabalhando(self, texto):
        self.ocupado = True
        self._estado("◌  " + texto, "stateMuted")
        self.principal.setEnabled(False)
        self.atualizar.setEnabled(False)
        self.mais.setEnabled(False)

    def mostrar(self, retrato):
        self.ocupado = False
        self.retrato = retrato or {}
        r = self.retrato
        instalado = bool(r.get("instalado"))
        atrasado = int(r.get("atrasado", 0) or 0)
        if r.get("erro"):
            self._estado("✕  " + r["erro"].split("\n")[0], "stateError")
        elif not instalado:
            self._estado("○  Não instalado", "stateMuted")
        elif atrasado:
            self._estado("▲  %d %s no GitHub" % (
                atrasado, "novidade" if atrasado == 1 else "novidades"),
                "stateWarning")
        elif r.get("adiantado"):
            self._estado("▲  Esta cópia tem commits que não estão no GitHub",
                         "stateWarning")
        else:
            self._estado("●  Em dia", "stateOk")
        self.principal.setText("Ir para o programa" if self.aberto else
                               "Abrir" if instalado else "Instalar")
        self.atualizar.setVisible(instalado and atrasado > 0)
        self.atualizar.setText("Atualizar" if atrasado <= 1
                               else "Atualizar (%d)" % atrasado)
        versao = r.get("versao", "")
        if instalado and r.get("sujo"):
            versao = (versao + "  • alterado").strip(" •")
        self.versao.setText(versao)
        self.versao.setToolTip(
            "Há arquivos alterados dentro da pasta desta automação. Ao "
            "atualizar, a Central oferece guardá-los antes (git stash)."
            if instalado and r.get("sujo") else "")
        self.principal.setEnabled(True)
        self.atualizar.setEnabled(True)
        self.mais.setEnabled(True)


# --------------------------------------------------------------------------
# A janela
# --------------------------------------------------------------------------
class CentralQt(QMainWindow):

    def __init__(self):
        super().__init__()
        self.cfg = cat.carregar_config()
        self.modo = self.cfg.get("tema", "claro")
        self.trabalho = queue.Queue()      # tela -> threads de trabalho
        self.ponte = Ponte()               # threads de trabalho -> tela
        self.ponte.recado.connect(self._recado)
        self.cartoes = {}
        self.pendentes = 0                 # tarefas de app ainda sem resposta
        self.filtro = "todos"
        self.colunas = 2
        self.retrato_central = {}
        self.erro_catalogo = ""
        # leitura de arquivo local, não de rede: pode ser feita aqui
        self.url_central = repos.endereco_origem(cat.pasta_da_central())

        try:
            self.apps = cat.carregar_catalogo()
        except RuntimeError as exc:
            self.apps = []
            self.erro_catalogo = str(exc)

        self.setWindowTitle(TITULO)
        self.resize(1180, 820)
        self.setMinimumSize(780, 580)
        for ico in (caminho_recurso("logo.ico"),
                    caminho_recurso("src", "logo.png")):
            if os.path.isfile(ico):
                self.setWindowIcon(QIcon(ico))
                break
        self._abrir_canal()
        self.lancados = {}                 # app_id -> .bat rodando escondido
        self.relogio_lancados = QTimer(self)
        self.relogio_lancados.timeout.connect(self._vigiar_lancados)
        self._montar()
        self._aplicar_tema()

        # Duas tarefas da MESMA pasta nunca correm juntas (ver
        # _trava_da_pasta): git em paralelo na mesma pasta briga pelo lock.
        self._travas = {}
        self._trava_das_travas = threading.Lock()
        for _ in range(TRABALHADORES):
            threading.Thread(target=self._trabalhar, daemon=True).start()

        if self.erro_catalogo:
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                self, TITULO, self.erro_catalogo))
        if not repos.disponivel():
            self._avisar_sem_git()
            self._olhar_local()
        elif self.cfg.get("buscar_ao_abrir", True):
            self.verificar_tudo()
        else:
            self._olhar_local()

    # ------------------------------------------------------------------ UI
    def _montar(self):
        raiz = QWidget()
        geral = QVBoxLayout(raiz)
        geral.setContentsMargins(0, 0, 0, 0)
        geral.setSpacing(0)
        geral.addWidget(self._cabecalho())
        geral.addWidget(self._faixa_central())

        conteudo = QWidget()
        corpo = QVBoxLayout(conteudo)
        corpo.setContentsMargins(24, 22, 24, 14)
        corpo.setSpacing(14)

        linha = QHBoxLayout()
        bloco = QVBoxLayout()
        self.titulo_lista = QLabel("Suas automações")
        self.titulo_lista.setObjectName("pageTitle")
        self.resumo = QLabel("")
        self.resumo.setObjectName("pageSubtitle")
        bloco.addWidget(self.titulo_lista)
        bloco.addWidget(self.resumo)
        linha.addLayout(bloco)
        linha.addStretch(1)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar automação…")
        self.busca.setClearButtonEnabled(True)
        self.busca.setMinimumWidth(290)
        self.busca.textChanged.connect(self._recriar_grade)
        linha.addWidget(self.busca)
        corpo.addLayout(linha)

        filtros = QHBoxLayout()
        self.botoes_filtro = {}
        for chave, texto in (("todos", "Todos"), ("instalados", "Instalados"),
                             ("atualizacoes", "Com atualização")):
            b = QPushButton(texto)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, c=chave: self._mudar_filtro(c))
            filtros.addWidget(b)
            self.botoes_filtro[chave] = b
        filtros.addStretch(1)
        corpo.addLayout(filtros)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.grade_widget = QWidget()
        self.grade = QGridLayout(self.grade_widget)
        self.grade.setContentsMargins(0, 0, 4, 0)
        self.grade.setHorizontalSpacing(14)
        self.grade.setVerticalSpacing(14)
        self.grade.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.grade_widget)
        corpo.addWidget(self.scroll, 1)

        for app in self.apps:
            cartao = Cartao(app)
            cartao.acao.connect(self._acao)
            self.cartoes[app.id] = cartao
        self._mudar_filtro("todos")
        geral.addWidget(conteudo, 1)

        self.status = QLabel("Pronto")
        self.status.setObjectName("statusbar")
        self.status.setContentsMargins(24, 8, 24, 8)
        geral.addWidget(self.status)
        # Tela única: a página 0 é o menu; cada programa aberto vira uma
        # página com a janela dele encaixada (ver _encaixar).
        self.pilha = QStackedWidget()
        self.pilha.addWidget(raiz)
        self.menu_pagina = raiz
        self.setCentralWidget(self.pilha)

    # ------------------------------------------------- tela única
    # Cada programa roda no PRÓPRIO processo (um travar não derruba os
    # outros nem a Central); só a janela dele é encaixada aqui. A conversa é
    # por um canal local (QLocalServer): o programa diz a janela, o "voltar"
    # e o andamento; a Central diz "fechar" e o andamento dos outros. O lado
    # do programa está no tema_qt.py (classe Central).
    def _abrir_canal(self):
        self.sessoes = {}                  # app_id -> sessão (dict)
        self.canal = QLocalServer(self)
        self.nome_canal = "cr2-central-%d" % os.getpid()
        QLocalServer.removeServer(self.nome_canal)
        self.canal.listen(self.nome_canal)
        self.canal.newConnection.connect(self._nova_conexao)

    def _nova_conexao(self):
        while self.canal.hasPendingConnections():
            sock = self.canal.nextPendingConnection()
            sessao = {"sock": sock, "buffer": b"", "app": None,
                      "container": None, "qwin": None, "ocupado": False,
                      "pct": None, "texto": ""}
            sock.readyRead.connect(lambda s=sessao: self._ler_canal(s))
            sock.disconnected.connect(lambda s=sessao: self._programa_fechou(s))

    def _ler_canal(self, sessao):
        sessao["buffer"] += bytes(sessao["sock"].readAll())
        while b"\n" in sessao["buffer"]:
            linha, sessao["buffer"] = sessao["buffer"].split(b"\n", 1)
            try:
                recado = json.loads(linha.decode("utf-8"))
            except ValueError:
                continue
            tipo = recado.get("tipo")
            if tipo == "ola":
                sessao["app"] = recado.get("app")
                sessao["pid"] = recado.get("pid")
                antiga = self.sessoes.get(sessao["app"])
                if antiga is not None and antiga is not sessao:
                    self._soltar(antiga)
                self.sessoes[sessao["app"]] = sessao
                self._mandar(sessao, {"tipo": "tema", "modo": self.modo})
            elif tipo == "janela":
                self._encaixar(sessao, int(recado["hwnd"]))
            elif tipo == "voltar":
                self.mostrar_menu()
            elif tipo == "alternar_tema":
                self.alternar_tema()
            elif tipo == "modo":
                sessao["modo"] = recado.get("modo")
            elif tipo == "progresso":
                sessao.update(ocupado=bool(recado.get("ocupado")),
                              pct=recado.get("pct"),
                              texto=recado.get("texto", ""))
                self._atualizar_andamentos()

    @staticmethod
    def _sem_moldura(hwnd):
        """Tira a barra de título e a borda da janela encaixada."""
        if os.name != "nt":
            return
        try:
            import ctypes
            u = ctypes.windll.user32
            GWL_STYLE = -16
            estilo = u.GetWindowLongW(hwnd, GWL_STYLE)
            estilo &= ~(0x00C00000 | 0x00040000 | 0x00020000 | 0x00010000)
            u.SetWindowLongW(hwnd, GWL_STYLE, estilo)
        except Exception:
            pass

    def _encaixar(self, sessao, hwnd):
        self._sem_moldura(hwnd)
        qwin = QWindow.fromWinId(hwnd)
        container = QWidget.createWindowContainer(qwin, self.pilha)
        container.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        sessao.update(qwin=qwin, container=container)
        self.pilha.addWidget(container)
        self.pilha.setCurrentWidget(container)
        self._atualizar_andamentos()

    def ir_para(self, app):
        sessao = self.sessoes.get(app.id)
        if sessao and sessao["container"] is not None:
            self.pilha.setCurrentWidget(sessao["container"])
            sessao["container"].setFocus()

    def mostrar_menu(self):
        self.pilha.setCurrentWidget(self.menu_pagina)
        self._atualizar_andamentos()

    def _atualizar_andamentos(self):
        for app_id, cartao in self.cartoes.items():
            s = self.sessoes.get(app_id)
            if s and s["container"] is not None:
                cartao.mostrar_andamento(True, s["ocupado"], s["pct"], s["texto"])
            else:
                cartao.mostrar_andamento(False)
        # cada programa aberto vê, no cabeçalho dele, o andamento dos outros
        for app_id, s in self.sessoes.items():
            outros = []
            for outro_id, o in self.sessoes.items():
                if outro_id == app_id or not o["ocupado"]:
                    continue
                nome = self.cartoes[outro_id].app.nome if outro_id in self.cartoes \
                    else outro_id
                nome = nome.split("—")[-1].strip()
                outros.append("⟳ %s%s" % (nome, " %d%%" % o["pct"]
                                           if o["pct"] is not None else ""))
            self._mandar(s, {"tipo": "outros", "texto": "   ".join(outros)})

    @staticmethod
    def _mandar(sessao, recado):
        try:
            sessao["sock"].write((json.dumps(recado, ensure_ascii=False)
                                  + "\n").encode("utf-8"))
            sessao["sock"].flush()
        except Exception:
            pass

    def fechar_programa(self, app):
        sessao = self.sessoes.get(app.id)
        if sessao:
            self.ir_para(app)              # a pergunta dele aparece na frente
            self._mandar(sessao, {"tipo": "fechar"})

    # ------------------------------------------------- abrir sem "cmd"
    # O .bat continua mandando (Python certo, instalar o que falta), mas roda
    # ESCONDIDO: nada de janela preta de comandos. Duas coisas garantem que
    # erro não some junto com a janela:
    #   * a entrada do .bat é vazia (NUL): um "pause" de erro não espera
    #     ninguém, o .bat termina;
    #   * a saída é guardada: se ele terminar sem o programa ter aberto, a
    #     Central mostra as últimas linhas e oferece abrir do jeito antigo,
    #     com a janela de comandos, para ver o problema.
    def _lancar_escondido(self, app, dir_programa, entrada, ambiente):
        # A saída vai para um ARQUIVO, não para um cano lido pela Central:
        # com cano, fechar a Central deixaria o programa escrevendo num cano
        # fechado — e um print a mais o derrubaria.
        saida = tempfile.NamedTemporaryFile(prefix="cr2_abrir_%s_" % app.id,
                                            suffix=".log", delete=False)
        proc = subprocess.Popen(
            ["cmd", "/c", entrada], cwd=dir_programa, env=ambiente,
            stdin=subprocess.DEVNULL, stdout=saida, stderr=subprocess.STDOUT,
            creationflags=0x08000000)                     # SEM JANELA
        saida.close()
        self.lancados[app.id] = {"proc": proc, "saida": saida.name,
                                 "inicio": time.time(), "app": app}
        cartao = self.cartoes.get(app.id)
        if cartao:
            cartao.trabalhando("abrindo…")
        if not self.relogio_lancados.isActive():
            self.relogio_lancados.start(700)

    def _vigiar_lancados(self):
        for app_id, l in list(self.lancados.items()):
            conectou = app_id in self.sessoes
            terminou = l["proc"].poll() is not None
            cartao = self.cartoes.get(app_id)
            if conectou:
                del self.lancados[app_id]
                if cartao:
                    cartao.mostrar(cartao.retrato)
                    self._atualizar_andamentos()
            elif terminou and l["proc"].returncode != 0:
                # o .bat saiu com erro (os .bat dos programas fazem
                # "exit /b 1" depois de explicar o problema)
                del self.lancados[app_id]
                if cartao:
                    cartao.mostrar(cartao.retrato)
                self._falhou_ao_abrir(l["app"], self._ultimas_linhas(l["saida"]))
            elif time.time() - l["inicio"] > 45:
                # 45 s sem falar com a Central e sem erro: é a janela Tk de
                # reserva (sem PySide6), ou um .bat que disparou o programa e
                # saiu. Abre solta, como antes. Está tudo bem.
                del self.lancados[app_id]
                if cartao:
                    cartao.mostrar(cartao.retrato)
        if not self.lancados:
            self.relogio_lancados.stop()

    @staticmethod
    def _ultimas_linhas(caminho, quantas=40):
        try:
            with open(caminho, "rb") as f:
                texto = f.read()[-20000:].decode("cp850", "replace")
            return texto.splitlines()[-quantas:]
        except OSError:
            return []

    def _falhou_ao_abrir(self, app, linhas):
        texto = "\n".join(l for l in linhas if l.strip())[-1500:] or \
            "(o programa não escreveu nada)"
        caixa = QMessageBox(self)
        caixa.setIcon(QMessageBox.Icon.Warning)
        caixa.setWindowTitle(TITULO)
        caixa.setText("\u201c%s\u201d não abriu." % app.nome)
        caixa.setInformativeText("Últimas linhas do que ele escreveu:")
        caixa.setDetailedText(texto)
        ver = caixa.addButton("Abrir com a janela de comandos",
                              QMessageBox.ButtonRole.AcceptRole)
        caixa.addButton("Fechar", QMessageBox.ButtonRole.RejectRole)
        caixa.exec()
        if caixa.clickedButton() is ver:
            self.abrir(app, visivel=True)

    def _nome_da_sessao(self, sessao):
        cartao = self.cartoes.get(sessao.get("app"))
        return cartao.app.nome if cartao else (sessao.get("app") or "?")

    def _fechar_tudo(self, abertos):
        """Pede a cada programa para fechar e fecha a Central quando todos
        tiverem fechado. Quem está trabalhando pergunta antes (o closeEvent
        dele); se a pessoa disser que não, ele fica — e a Central também."""
        self._status("Fechando os programas…")
        ocupados = [s for s in abertos if s["ocupado"]]
        if ocupados and ocupados[0]["container"] is not None:
            self.pilha.setCurrentWidget(ocupados[0]["container"])
        for sessao in abertos:
            self._mandar(sessao, {"tipo": "fechar"})
        estado = {"ultimo": time.time(), "quantos": len(self.sessoes)}

        def olhar():
            vivos = [s for s in self.sessoes.values()
                     if s["container"] is not None]
            if not vivos:
                self._pode_fechar = True
                self.close()
                return
            if len(self.sessoes) != estado["quantos"]:
                estado.update(ultimo=time.time(), quantos=len(self.sessoes))
            if time.time() - estado["ultimo"] > 25:
                # alguém disse "não" na pergunta do programa: fica tudo aberto
                self.pilha.setCurrentWidget(vivos[0]["container"])
                self._status("%s continua aberto — a Central também."
                             % ", ".join(self._nome_da_sessao(s) for s in vivos))
                return
            QTimer.singleShot(300, olhar)
        olhar()

    def _programa_fechou(self, sessao):
        if getattr(self, "_fechando", False):
            return                          # a tela já está sendo desmontada
        app_id = sessao.get("app")
        if self.sessoes.get(app_id) is sessao:
            del self.sessoes[app_id]
        if sessao["container"] is not None:
            if self.pilha.currentWidget() is sessao["container"]:
                self.pilha.setCurrentWidget(self.menu_pagina)
            self.pilha.removeWidget(sessao["container"])
            sessao["container"].deleteLater()
        self._atualizar_andamentos()

    def _soltar(self, sessao):
        """Devolve a janela do programa ao Windows (janela própria de novo)."""
        qwin = sessao.get("qwin")
        if qwin is None:
            return
        try:
            import ctypes
            u = ctypes.windll.user32
            hwnd = int(qwin.winId())
            # tira de dentro da Central primeiro, depois devolve a moldura
            u.SetParent(hwnd, None)
            estilo = u.GetWindowLongW(hwnd, -16)                  # GWL_STYLE
            estilo &= ~0x40000000                                 # WS_CHILD
            estilo |= 0x00CF0000          # WS_OVERLAPPEDWINDOW: título, borda,
            u.SetWindowLongW(hwnd, -16, estilo)   # menu, minimizar, maximizar
            extra = u.GetWindowLongW(hwnd, -20)                   # GWL_EXSTYLE
            u.SetWindowLongW(hwnd, -20, extra | 0x00040000)       # na barra de tarefas
            # FRAMECHANGED: sem ele o Windows não redesenha a moldura e a
            # janela fica sem os botões de fechar/minimizar. O programa solto
            # herda o tamanho da Central: maximizado se ela estava assim.
            g = self.frameGeometry()
            u.SetWindowPos(hwnd, None, g.x(), g.y(), g.width(), g.height(),
                           0x0004 | 0x0020 | 0x0040)
            if self.isMaximized():
                u.ShowWindow(hwnd, 3)                         # SW_MAXIMIZE
        except Exception:
            pass
        self._mandar(sessao, {"tipo": "solto"})

    def _cabecalho(self):
        self.cabecalho = tq.Cabecalho("Central de Automações", "Ecossistema CR2",
                                      logo_png=caminho_recurso("src", "logo.png"))
        self.cabecalho.tema_clicado.connect(self.alternar_tema)
        # A faixa do topo só acende quando existe versão nova da Central.
        # Este botão está sempre aqui: atualizar a própria Central não pode
        # depender de a faixa ter aparecido.
        self.btn_central = self.cabecalho.adicionar(
            tq.botao("A Central  ▾", "headerButton", self.menu_da_central))
        # Instalar ou atualizar tudo de uma vez, pelo mesmo caminho dos
        # botões de cada cartão.
        self.btn_tudo = self.cabecalho.adicionar(
            tq.botao("Tudo  ▾", "headerButton", self.menu_tudo))
        self.btn_verificar = self.cabecalho.adicionar(
            tq.botao("Verificar tudo", "headerPrimary", self.verificar_tudo))
        return self.cabecalho

    def _faixa_central(self):
        """Aviso do topo. Fica escondido enquanto não há o que dizer."""
        self.faixa = tq.Faixa()
        self.faixa_botao = self.faixa.botao
        return self.faixa

    def _mostrar_faixa(self, texto, rotulo_botao=None, comando=None):
        self.faixa.mostrar(texto, rotulo_botao, comando)

    def _esconder_faixa(self):
        self.faixa.hide()

    # Regras que só a Central usa: o cartão de cada automação.
    ESTILO_EXTRA = """
        #card { background: %(superficie)s; border: 1px solid %(borda)s;
                border-radius: 12px; }
        #card QLabel { background: transparent; }
        #cardIcon { color: %(marca)s; font-size: 23pt; }
        #cardTitle { font-size: 12pt; font-weight: 700; }
        #description { color: %(suave)s; }
        #stateOk { color: %(ok)s; font-size: 9pt; }
        #stateWarning { color: %(alerta)s; font-size: 9pt; }
        #stateError { color: %(erro)s; font-size: 9pt; }
        #stateMuted, #version { color: %(suave)s; font-size: 9pt; }
        #primary { min-width: 76px; }
    """

    def _aplicar_tema(self):
        self.setStyleSheet(tq.estilo(self.modo, self.ESTILO_EXTRA))
        self.cabecalho.mostrar_modo(self.modo)

    def alternar_tema(self):
        self.modo = "claro" if self.modo == "escuro" else "escuro"
        self.cfg["tema"] = self.modo
        cat.salvar_config(self.cfg)
        self._aplicar_tema()
        self._status("Modo %s." % self.modo)
        for sessao in self.sessoes.values():
            self._mandar(sessao, {"tipo": "tema", "modo": self.modo})

    def _status(self, texto):
        self.status.setText(texto)

    # ------------------------------------------------------------ a grade
    def resizeEvent(self, evento):
        nova = 1 if self.width() < 900 else 2
        if nova != self.colunas:
            self.colunas = nova
            self._recriar_grade()
        super().resizeEvent(evento)

    def _mudar_filtro(self, chave):
        self.filtro = chave
        for nome, botao in self.botoes_filtro.items():
            botao.setChecked(nome == chave)
        self._recriar_grade()

    def _visivel(self, cartao):
        busca = self.busca.text().strip().casefold()
        if busca and busca not in (cartao.app.nome + " "
                                   + cartao.app.descricao).casefold():
            return False
        instalado = bool(cartao.retrato.get("instalado"))
        if self.filtro == "instalados" and not instalado:
            return False
        if self.filtro == "atualizacoes" and not cartao.retrato.get("atrasado", 0):
            return False
        return True

    def _recriar_grade(self):
        # tira todos da grade e esconde; os visíveis voltam logo abaixo.
        # (setParent(None) faria dos cartões janelas soltas por um instante.)
        while self.grade.count():
            item = self.grade.takeAt(0)
            if item.widget():
                item.widget().hide()
        visiveis = [c for c in self.cartoes.values() if self._visivel(c)]
        for i, cartao in enumerate(visiveis):
            self.grade.addWidget(cartao, i // self.colunas, i % self.colunas)
            cartao.show()
        # zera os pesos antigos: a grade pode ter tido 2 colunas ou mais
        # linhas antes deste filtro.
        for coluna in range(2):
            self.grade.setColumnStretch(
                coluna, 1 if coluna < self.colunas else 0)
        for linha in range(len(self.cartoes) + 1):
            self.grade.setRowStretch(linha, 0)
        instalados = sum(bool(c.retrato.get("instalado"))
                         for c in self.cartoes.values())
        atrasados = sum(bool(c.retrato.get("atrasado", 0))
                        for c in self.cartoes.values())
        partes = ["%d no catálogo" % len(self.cartoes),
                  "%d instaladas" % instalados]
        if atrasados:
            partes.append("%d para atualizar" % atrasados)
        if not visiveis and self.cartoes:
            partes.append("nenhuma com este filtro")
        self.resumo.setText("  •  ".join(partes))

    # --------------------------------------------------------- ações
    def _acao(self, nome, app):
        if nome == "instalar":
            self.instalar(app)
        elif nome == "abrir":
            self.abrir(app)
        elif nome == "atualizar":
            self.atualizar(app)
        elif nome == "menu":
            self.menu_do_cartao(self.cartoes[app.id])
        elif nome == "ir":
            self.ir_para(app)

    def instalar(self, app):
        if not repos.disponivel():
            self._avisar_sem_git()
            return
        pasta = cat.pasta_do_app(app, self.cfg)
        if os.path.isdir(pasta) and os.listdir(pasta):
            if repos.e_repo(pasta):
                self._enfileirar("olhar", app)
                return
            QMessageBox.warning(
                self, TITULO,
                "Já existe uma pasta com arquivos aqui:\n\n%s\n\n"
                "A Central não vai mexer nela. Apague-a, ou use "
                "\u201cMais \u25be \u2192 Escolher outra pasta\u201d." % pasta)
            return
        self._enfileirar("clonar", app, texto="instalando...")

    def atualizar(self, app):
        cartao = self.cartoes.get(app.id)
        guardar = False
        if cartao and cartao.retrato.get("sujo"):
            resposta = QMessageBox.question(
                self, TITULO,
                "Há arquivos alterados dentro da pasta de \u201c%s\u201d.\n\n"
                "A Central pode guardá-los antes de atualizar (git stash) e "
                "eles continuam recuperáveis depois.\n\nGuardar e atualizar?"
                % app.nome)
            if resposta != QMessageBox.StandardButton.Yes:
                return
            guardar = True
        self._enfileirar("atualizar", app, extra=guardar,
                         texto="atualizando...")

    def abrir(self, app, visivel=False):
        if app.id in self.sessoes:          # já aberto: só mostra
            self.ir_para(app)
            return
        if app.id in self.lancados:         # ainda abrindo: não abre outro
            return
        pasta = cat.pasta_do_app(app, self.cfg)
        dir_programa = app.pasta_do_programa(pasta)
        entrada = app.entrada_preferida(pasta)
        if not os.path.exists(entrada):
            QMessageBox.critical(
                self, TITULO,
                "O arquivo que abre \u201c%s\u201d não foi encontrado:\n\n%s"
                "\n\nTalvez a automação tenha mudado de nome no repositório. "
                "Atualize a Central e tente de novo." % (app.nome, entrada))
            return
        try:
            self._lancar(app, dir_programa, entrada, visivel)
        except OSError as e:
            QMessageBox.critical(self, TITULO, "Não foi possível abrir "
                                 "\u201c%s\u201d:\n\n%s" % (app.nome, e))
            return
        self._status("%s foi aberto." % app.nome)

    def _lancar(self, app, dir_programa, entrada, visivel=False):
        """Abre cada automação do jeito que ela já abre hoje.

        Quando existe um .bat, é ele quem manda: é lá que estão a escolha do
        Python certo e a instalação das dependências na primeira execução. A
        Central não repete essa lógica — só aperta o mesmo botão.
        """
        minusculo = entrada.lower()
        # o programa Qt usa isto para se encaixar aqui (tema_qt.Central)
        ambiente = dict(os.environ, CR2_CENTRAL=self.nome_canal,
                        CR2_APP_ID=app.id, CR2_TEMA=self.modo)
        if os.name != "nt":
            subprocess.Popen([cat.python_de_terminal(), entrada],
                             cwd=dir_programa)
        elif minusculo.endswith(".bat") and not visivel:
            self._lancar_escondido(app, dir_programa, entrada, ambiente)
        elif minusculo.endswith(".bat"):
            subprocess.Popen(["cmd", "/c", "start", "", entrada],
                             cwd=dir_programa, env=ambiente,
                             **repos._sem_janela())
        elif minusculo.endswith(".exe"):
            # cwd na pasta do programa, como o .bat faria: há programa que
            # procura os arquivos dele a partir do diretório corrente
            subprocess.Popen([entrada], cwd=dir_programa)
        elif app.tipo == "terminal":
            # ferramenta de linha de comando: o console faz parte dela, e
            # /k mantém a janela aberta para a pessoa ler o resultado
            subprocess.Popen(["cmd", "/k", cat.python_de_terminal(), entrada],
                             cwd=dir_programa,
                             creationflags=0x00000010)   # CREATE_NEW_CONSOLE
        else:
            subprocess.Popen([cat.python_de_janela(), entrada],
                             cwd=dir_programa, env=ambiente,
                             **repos._sem_janela())

    def verificar_tudo(self):
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

    # ------------------------------------------------- tudo de uma vez
    def _situacao_de_cada(self):
        """(a instalar, a atualizar, com arquivo alterado) — pelo que os
        cartões mostram agora, que é o resultado do último Verificar."""
        instalar, atualizar, alterados = [], [], []
        for app in self.apps:
            cartao = self.cartoes.get(app.id)
            retrato = cartao.retrato if cartao else {}
            if not retrato.get("instalado"):
                instalar.append(app)
            elif retrato.get("atrasado"):
                (alterados if retrato.get("sujo") else atualizar).append(app)
        return instalar, atualizar, alterados

    def _popup(self, menu, botao):
        menu.exec(botao.mapToGlobal(botao.rect().bottomLeft()))

    def menu_tudo(self):
        """O menu do botão "Tudo": instalar e/ou atualizar todas de uma vez."""
        instalar, atualizar, alterados = self._situacao_de_cada()
        n_atualizar = len(atualizar) + len(alterados)
        menu = QMenu(self)
        a = menu.addAction("Atualizar tudo  (%d)" % n_atualizar)
        a.setEnabled(bool(n_atualizar))
        a.triggered.connect(lambda: self.fazer_tudo(atualizar=True))
        a = menu.addAction("Instalar tudo  (%d)" % len(instalar))
        a.setEnabled(bool(instalar))
        a.triggered.connect(lambda: self.fazer_tudo(instalar=True))
        a = menu.addAction("Instalar e atualizar tudo")
        a.setEnabled(bool(instalar or n_atualizar))
        a.triggered.connect(
            lambda: self.fazer_tudo(instalar=True, atualizar=True))
        menu.addSeparator()
        menu.addAction("Verificar tudo de novo").triggered.connect(
            self.verificar_tudo)
        self._popup(menu, self.btn_tudo)

    def fazer_tudo(self, instalar=False, atualizar=False):
        """Enfileira tudo de uma vez — os trabalhadores fazem em paralelo.

        Automação com arquivo alterado dentro da pasta NÃO é atualizada em
        massa: o cartão dela pergunta se pode guardar (git stash), e essa
        pergunta é por automação. Ela fica listada no fim.
        """
        if not repos.disponivel():
            self._avisar_sem_git()
            return
        a_instalar, a_atualizar, alterados = self._situacao_de_cada()
        feitos = 0
        if instalar:
            for app in a_instalar:
                pasta = cat.pasta_do_app(app, self.cfg)
                if repos.e_repo(pasta):
                    # já é um clone (o cartão estava velho): só reler
                    self._enfileirar("olhar", app)
                    continue
                if os.path.isdir(pasta) and os.listdir(pasta):
                    continue            # pasta ocupada: o cartão explica
                self._enfileirar("clonar", app, texto="instalando...")
                feitos += 1
        if atualizar:
            for app in a_atualizar:
                self._enfileirar("atualizar", app, extra=False,
                                 texto="atualizando...")
                feitos += 1
        self._status("%d automação(ões) em andamento, várias ao mesmo tempo..."
                     % feitos if feitos else "Nada a fazer.")
        if atualizar and alterados:
            QMessageBox.information(
                self, TITULO,
                "Estas automações têm arquivos alterados dentro da pasta e não "
                "foram atualizadas em massa:\n\n%s\n\nUse o botão Atualizar do "
                "cartão de cada uma: ele pergunta se pode guardar os arquivos "
                "antes." % "\n".join("  • " + a.nome for a in alterados))

    # ------------------------------------------------------ menu do cartão
    def menu_do_cartao(self, cartao):
        app = cartao.app
        pasta = cat.pasta_do_app(app, self.cfg)
        menu = QMenu(self)
        if cartao.retrato.get("novidades"):
            menu.addAction("Ver o que mudou").triggered.connect(
                lambda: self.ver_novidades(app.nome, cartao.retrato))
            menu.addSeparator()
        if app.id in self.sessoes:
            menu.addAction("Fechar o programa").triggered.connect(
                lambda: self.fechar_programa(app))
            menu.addSeparator()
        a = menu.addAction("Abrir a pasta no Explorer")
        a.setEnabled(os.path.isdir(pasta))
        a.triggered.connect(lambda: self.abrir_pasta(pasta))
        menu.addAction("Escolher outra pasta...").triggered.connect(
            lambda: self.escolher_pasta(app))
        if (self.cfg.get("caminhos") or {}).get(app.id):
            menu.addAction("Voltar para a pasta padrão").triggered.connect(
                lambda: self.voltar_pasta(app))
        menu.addSeparator()
        menu.addAction("Ver no GitHub").triggered.connect(
            lambda: webbrowser.open(app.url_github))
        self._popup(menu, cartao.mais)

    def ver_novidades(self, nome, retrato):
        janela = QDialog(self)
        janela.setWindowTitle("O que mudou — %s" % nome)
        janela.resize(640, 420)
        caixa = QVBoxLayout(janela)
        rotulo = QLabel("Estas são as mudanças que ainda não estão nesta "
                        "máquina, da mais nova para a mais antiga:")
        rotulo.setWordWrap(True)
        caixa.addWidget(rotulo)
        texto = QPlainTextEdit()
        texto.setReadOnly(True)
        linhas = ["\u2022  %s" % l for l in retrato.get("novidades", [])]
        restantes = retrato.get("atrasado", 0) - len(
            retrato.get("novidades", []))
        if restantes > 0:
            linhas.append("\n... e mais %d." % restantes)
        texto.setPlainText("\n".join(linhas))
        caixa.addWidget(texto, 1)
        fechar = QPushButton("Fechar")
        fechar.clicked.connect(janela.accept)
        caixa.addWidget(fechar, 0, Qt.AlignmentFlag.AlignRight)
        janela.exec()

    def abrir_pasta(self, pasta):
        if os.path.isdir(pasta) and os.name == "nt":
            os.startfile(pasta)

    def escolher_pasta(self, app):
        """Aponta a Central para um clone que já existe nesta máquina."""
        escolhida = QFileDialog.getExistingDirectory(
            self, "Onde está \u201c%s\u201d nesta máquina?" % app.nome,
            cat.pasta_do_app(app, self.cfg))
        if not escolhida:
            return
        escolhida = os.path.normpath(escolhida)
        if not repos.e_repo(escolhida):
            resposta = QMessageBox.question(
                self, TITULO,
                "Esta pasta não é um clone do git:\n\n%s\n\n"
                "A Central conseguirá abrir o programa, mas não conseguirá "
                "atualizá-lo.\n\nUsar assim mesmo?" % escolhida)
            if resposta != QMessageBox.StandardButton.Yes:
                return
        else:
            try:
                repos.conferir_origem(escolhida, app.repo)
            except repos.ErroGit as e:
                QMessageBox.critical(self, TITULO, str(e))
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
        """Tudo sobre a própria Central — inclusive atualizá-la."""
        retrato = self.retrato_central
        menu = QMenu(self)
        if retrato.get("versao"):
            menu.addAction("Versão instalada:  %s"
                           % retrato["versao"]).setEnabled(False)
            menu.addSeparator()
        menu.addAction("Verificar se há versão nova").triggered.connect(
            self.verificar_central)
        menu.addAction("Atualizar a Central").triggered.connect(
            self.atualizar_central)
        if retrato.get("novidades"):
            menu.addAction("Ver o que mudou").triggered.connect(
                lambda: self.ver_novidades("a Central", retrato))
        menu.addSeparator()
        menu.addAction("Abrir a pasta da Central no Explorer").triggered.connect(
            lambda: self.abrir_pasta(cat.pasta_da_central()))
        a = menu.addAction("Ver no GitHub")
        a.setEnabled(bool(self.url_central))
        a.triggered.connect(self.central_no_github)
        self._popup(menu, self.btn_central)

    def central_no_github(self):
        url = self.url_central
        if url.endswith(".git"):
            url = url[:-4]
        if url:
            webbrowser.open(url)

    def _mostrar_estado_central(self, retrato, avisar=False):
        """Acende (ou apaga) a faixa do topo.

        `avisar` é verdadeiro quando a pessoa pediu a verificação pelo menu:
        aí o resultado precisa aparecer mesmo quando não há nada de novo.
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
        if repos.disponivel():
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
        # se há arquivo mexido na pasta da Central (um catalogo.json editado
        # à mão, por exemplo), o git recusaria o pull — então ela oferece
        # guardar antes.
        guardar = False
        if self.retrato_central.get("sujo"):
            resposta = QMessageBox.question(
                self, TITULO,
                "Há arquivos alterados dentro da pasta da Central.\n\n"
                "Ela pode guardá-los antes de atualizar (git stash) e "
                "eles continuam recuperáveis depois.\n\nGuardar e atualizar?")
            if resposta != QMessageBox.StandardButton.Yes:
                return
            guardar = True
        self.faixa_botao.setEnabled(False)
        self._status("Atualizando a Central...")
        self._enfileirar_central("atualizar", avisar=True, extra=guardar)

    def _avisar_central_sem_git(self):
        QMessageBox.information(
            self, TITULO,
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

    # ------------------------------------------------- fila e threads
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
        """`avisar`: a pessoa pediu pelo menu, então quer ver o resultado."""
        self.trabalho.put({
            "acao": acao,
            "id": ID_CENTRAL,
            "nome": "a Central",
            "pasta": cat.pasta_da_central(),
            "url": "",
            "extra": extra,
            "avisar": avisar,
        })

    def _trava_da_pasta(self, pasta):
        """A trava de uma pasta: uma tarefa por pasta de cada vez."""
        chave = os.path.normcase(os.path.abspath(pasta or ""))
        with self._trava_das_travas:
            return self._travas.setdefault(chave, threading.Lock())

    def _trabalhar(self):
        """Um dos trabalhadores. Roda uma tarefa por vez, para sempre."""
        while True:
            tarefa = self.trabalho.get()
            if tarefa is None:
                return
            try:
                with self._trava_da_pasta(tarefa["pasta"]):
                    self._executar(tarefa)
            except repos.ErroGit as e:
                self._avisar_tela(("erro", tarefa, str(e)))
            except Exception:
                self._avisar_tela(("erro", tarefa,
                                   traceback.format_exc(limit=2)))

    def _avisar_tela(self, recado):
        try:
            self.ponte.recado.emit(recado)
        except RuntimeError:
            pass                        # a janela já foi fechada

    def _executar(self, tarefa):
        """Roda numa thread de trabalho: não toca a tela, só avisa."""
        acao, pasta = tarefa["acao"], tarefa["pasta"]
        if acao == "clonar":
            self._avisar_tela(("status", "Baixando %s do GitHub..."
                               % tarefa["nome"]))
            repos.clonar(tarefa["url"], pasta)
            self._avisar_tela(("status", "%s foi instalado." % tarefa["nome"]))
        elif acao == "buscar":
            if repos.e_repo(pasta):
                repos.buscar(pasta)
        elif acao == "atualizar":
            veio = repos.atualizar(pasta,
                                   guardar_mudancas=bool(tarefa["extra"]))
            self._avisar_tela((
                "status", "%s está na versão nova." % tarefa["nome"] if veio
                else "%s já estava na versão mais nova." % tarefa["nome"]))
            if tarefa["id"] == ID_CENTRAL and veio:
                self._avisar_tela(("central-atualizada", tarefa, None))
                return
        self._avisar_tela(("estado", tarefa, repos.situacao(pasta)))

    def _recado(self, recado):
        """Chega aqui, na thread da janela, tudo o que as threads mandam."""
        tipo, *resto = recado
        if tipo == "status":
            self._status(resto[0])
        elif tipo == "estado":
            self._aplicar_estado(*resto)
        elif tipo == "erro":
            self._aplicar_erro(*resto)
        elif tipo == "central-atualizada":
            self._central_atualizada(bool(resto[0].get("extra")))

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
            self.faixa_botao.setEnabled(True)
            self._status("A Central não pôde ser %s: %s"
                         % ("atualizada" if tarefa["acao"] == "atualizar"
                            else "verificada", mensagem.split("\n")[0]))
            # a atualização foi um clique da pessoa: o erro merece uma
            # caixa, senão ela fica sem saber por que nada aconteceu.
            if tarefa["acao"] == "atualizar":
                QMessageBox.critical(
                    self, TITULO,
                    "A Central não pôde ser atualizada:\n\n%s" % mensagem)
            return
        cartao = self.cartoes.get(tarefa["id"])
        if cartao:
            cartao.mostrar(dict(repos.situacao(tarefa["pasta"]),
                                erro=mensagem))
        # clonar e atualizar são ações que a pessoa pediu: o erro merece
        # uma caixa. Verificação de fundo só acende o rótulo do cartão.
        if tarefa["acao"] in ("clonar", "atualizar"):
            QMessageBox.critical(
                self, TITULO, "%s — %s:\n\n%s"
                % (tarefa["nome"],
                   "instalação" if tarefa["acao"] == "clonar"
                   else "atualização", mensagem))
        self._status("Problema em %s." % tarefa["nome"])
        self._baixa_pendente(resumir=False)

    def _baixa_pendente(self, resumir=True):
        """Uma tarefa de app respondeu. Na última, o rodapé vira o resumo."""
        self.pendentes = max(0, self.pendentes - 1)
        if self.pendentes == 0:
            self._recriar_grade()
            if resumir:
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
        """O recado do fim. Quando houve stash, ele diz como voltar."""
        self._esconder_faixa()
        recado = ("A Central foi atualizada.\n\nFeche e abra de novo "
                  "para a versão nova entrar no lugar — inclusive o "
                  "catálogo, que pode ter automações novas.")
        if guardou:
            recado += ("\n\nOs arquivos que estavam alterados foram "
                       "guardados com o git stash — nada foi perdido. "
                       "Para trazê-los de volta, rode nesta pasta:\n\n"
                       "    git stash pop")
        QMessageBox.information(self, TITULO, recado)

    def closeEvent(self, evento):
        # Fechar a Central NUNCA cancela um programa: os abertos voltam a ser
        # janelas próprias e continuam do ponto em que estavam.
        abertos = [s for s in self.sessoes.values() if s["container"] is not None]
        if abertos and not getattr(self, "_pode_fechar", False):
            rodando = [s for s in abertos if s["ocupado"]]
            nomes = "\n".join("  • %s%s" % (
                self._nome_da_sessao(s), "  (em andamento)" if s["ocupado"] else "")
                for s in abertos)
            caixa = QMessageBox(self)
            caixa.setIcon(QMessageBox.Icon.Question)
            caixa.setWindowTitle(TITULO)
            caixa.setText("Estes programas estão abertos na Central:\n\n" + nomes)
            caixa.setInformativeText(
                "\u201cFechar tudo\u201d fecha os programas e a Central"
                + (" — o que está em andamento pergunta antes" if rodando else "")
                + ".\n\u201cDeixar abertos\u201d fecha só a Central: cada "
                "programa continua na sua janela.")
            tudo = caixa.addButton("Fechar tudo",
                                   QMessageBox.ButtonRole.DestructiveRole)
            soltar = caixa.addButton("Deixar abertos",
                                     QMessageBox.ButtonRole.AcceptRole)
            caixa.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            caixa.setDefaultButton(soltar)
            caixa.exec()
            escolha = caixa.clickedButton()
            if escolha is tudo:
                evento.ignore()
                self._fechar_tudo(abertos)
                return
            if escolha is not soltar:
                evento.ignore()
                return
            for sessao in abertos:
                self._soltar(sessao)
        self._fechando = True
        cat.salvar_config(self.cfg)
        super().closeEvent(evento)


def main():
    app = tq.preparar_aplicacao(ID_WINDOWS)
    app.setApplicationName(TITULO)
    app.setOrganizationName("CR2")
    tq.registrar_erros(cat.ARQ_LOG, TITULO)
    janela = CentralQt()
    # Abre ocupando a tela toda (maximizada, com a barra de tarefas à
    # vista): os programas abrem DENTRO da Central e precisam do espaço.
    janela.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
