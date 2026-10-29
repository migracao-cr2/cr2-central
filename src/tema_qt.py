# -*- coding: utf-8 -*-
"""
O visual Qt dos programas CR2 — o MESMO arquivo em todos eles.

Como o escala.py e o tema.py da versão Tk: este arquivo é copiado igual para
cada programa do catálogo. A cópia canônica mora na Central
(cr2-central/src/tema_qt.py). Mudou aqui, copie para os outros; não edite a
cópia de um programa só, senão os visuais voltam a divergir.

O que mora aqui, e só isto:

    * as cores (claro e escuro) e a folha de estilo de toda a janela
    * o cabeçalho escuro com a marca e o botão de tema
    * o painel (cartão branco de bordas redondas) e o campo com rótulo
    * a seta das caixas de seleção
    * a Tarefa: trabalho fora da janela, com sinais seguros de volta
    * a preparação da aplicação e o registro de erros inesperados

Regra de negócio NÃO mora aqui. Este arquivo não sabe o que é licitação,
emenda ou PDF.

Uso típico:

    import tema_qt as tq
    app = tq.preparar_aplicacao("CR2.TCE-RS")
    tq.registrar_erros(caminho_do_log, "Licitações — TCE-RS")
    janela.setStyleSheet(tq.estilo(modo))
    cab = tq.Cabecalho("Licitações e Contratos", "TCE-RS · LicitaCon")
    cab.tema_clicado.connect(trocar_tema); cab.mostrar_modo(modo)
"""

import json
import os
import sys
import tempfile
import threading
import traceback

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton,
    QVBoxLayout,
)

# Assinatura padrão do rodapé. Programa que tem outro autor passa a dele: o
# rodapé Qt mostra a MESMA assinatura que o tema.py (Tk) daquele programa.
ASSINATURA = "Desenvolvido por Mauricio"


# --------------------------------------------------------------------------
# Cores
# --------------------------------------------------------------------------
CLARO = {
    "fundo": "#F5F7FA", "superficie": "#FFFFFF", "superficie2": "#F8FAFC",
    "borda": "#D9E0E8", "texto": "#172033", "suave": "#64748B",
    "marca": "#175CD3", "marca_hover": "#004EEB", "marca_suave": "#EAF2FF",
    "marca_texto": "#FFFFFF",
    "cabecalho": "#0B1220", "cabecalho_texto": "#FFFFFF",
    "cabecalho_suave": "#AAB6C7", "cabecalho_borda": "#344054",
    "cabecalho_hover": "#1C2533",
    "ok": "#16803C", "alerta": "#B54708", "erro": "#B42318",
    "ok_fundo": "#EAF8EF", "alerta_fundo": "#FFF4E5", "erro_fundo": "#FDECEC",
    "faixa": "#FEF0C7", "faixa_texto": "#7A2E0E",
}

ESCURO = {
    "fundo": "#0F141C", "superficie": "#171E29", "superficie2": "#1C2532",
    "borda": "#2C394B", "texto": "#F1F5F9", "suave": "#9BA9BC",
    "marca": "#63A4FF", "marca_hover": "#86B9FF", "marca_suave": "#1A3152",
    # texto ESCURO sobre o azul claro do modo escuro: branco ali não se lê
    "marca_texto": "#0B1220",
    "cabecalho": "#090D14", "cabecalho_texto": "#FFFFFF",
    "cabecalho_suave": "#AAB6C7", "cabecalho_borda": "#344054",
    "cabecalho_hover": "#1C2533",
    "ok": "#58D68D", "alerta": "#F5B85C", "erro": "#FF8278",
    "ok_fundo": "#153525", "alerta_fundo": "#362817", "erro_fundo": "#3C2022",
    "faixa": "#3A2A0C", "faixa_texto": "#FCD9A0",
}


def paleta(modo):
    """As cores do modo ("claro" ou "escuro"). Qualquer outro valor = claro."""
    return ESCURO if modo == "escuro" else CLARO


def cor(modo, nome):
    """Uma cor como QColor — para pintar linha de tabela, por exemplo."""
    return QColor(paleta(modo)[nome])


def _icone(nome, svg):
    """Grava um SVG pequeno na pasta temporária e devolve o caminho para o QSS.

    O Qt só aceita imagem em algumas partes dos controles (a seta da caixa
    de seleção, o visto da caixa de marcar). Um arquivo por desenho e cor.
    """
    caminho = os.path.join(tempfile.gettempdir(), "cr2_%s.svg" % nome)
    if not os.path.isfile(caminho):
        try:
            with open(caminho, "w", encoding="ascii") as f:
                f.write(svg)
        except OSError:
            return ""
    return caminho.replace("\\", "/")


def seta(cor_hex):
    """A seta das caixas de seleção (o triângulo com bordas vira retângulo)."""
    return _icone("seta_%s" % cor_hex.strip("#").lower(),
                  '<svg xmlns="http://www.w3.org/2000/svg" width="10" '
                  'height="6" viewBox="0 0 10 6"><path d="M0 0h10L5 6z" '
                  'fill="%s"/></svg>' % cor_hex)


def visto(cor_hex="#FFFFFF"):
    """O visto da caixa de marcar. Sem ele, a caixa marcada fica lisa."""
    return _icone("visto_%s" % cor_hex.strip("#").lower(),
                  '<svg xmlns="http://www.w3.org/2000/svg" width="12" '
                  'height="12" viewBox="0 0 12 12"><path d="M2.5 6.2l2.4 2.4 '
                  '4.6-5" fill="none" stroke="%s" stroke-width="1.8" '
                  'stroke-linecap="round" stroke-linejoin="round"/></svg>'
                  % cor_hex)


# --------------------------------------------------------------------------
# A folha de estilo
# --------------------------------------------------------------------------
# Nomes de objeto (setObjectName) que a folha conhece:
#   header, logo, brandTitle, brandSubtitle, headerButton, headerPrimary
#   banner, bannerText                      faixa de aviso abaixo do cabeçalho
#   panel, sectionTitle, sectionSubtitle    o cartão branco e seus títulos
#   pageTitle, pageSubtitle                 título grande da página
#   fieldLabel, hint, status, signature     textos pequenos e apagados
#   primary, danger, discreto, small        variações de botão
#   link, headerLink                        botão com cara de link (no corpo / no cabeçalho)
#   textOk, textWarning, textError          texto colorido de situação
#   statusbar                               a linha do rodapé
#   mono, log                               texto de largura fixa (log, ajuda)
#   caixa                                   QWidget só de agrupar (fica transparente)
#   flat                                    tabela/lista sem borda (ocupa um painel)
#
# Para notebook: tela_baixa(), caber_na_tela(janela, l, a), rolagem().
_ESTILO = """
* { font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow, QDialog, QWidget { background: %(fundo)s; color: %(texto)s; }
QLabel { background: transparent; border: none; }
QToolTip { background: %(superficie)s; color: %(texto)s; border: 1px solid %(borda)s;
        padding: 6px; }

#header { background: %(cabecalho)s; border: none; }
#header QLabel { background: transparent; }
#header QLabel#logo, #logo { background: %(marca)s; color: %(marca_texto)s; border-radius: 10px;
        font-size: 14pt; font-weight: 800; }
#brandTitle { color: %(cabecalho_texto)s; font-size: 13pt; font-weight: 700; }
#brandSubtitle { color: %(cabecalho_suave)s; font-size: 9pt; }
#headerButton, #headerPrimary { background: transparent; color: white;
        border: 1px solid %(cabecalho_borda)s; border-radius: 8px; padding: 9px 14px; }
#headerButton:hover { background: %(cabecalho_hover)s; }
#headerButton:disabled, #headerPrimary:disabled { color: #7D8BA0; }
#headerPrimary { background: %(marca)s; border-color: %(marca)s; color: %(marca_texto)s;
        font-weight: 600; }
#headerPrimary:hover { background: %(marca_hover)s; }

#banner { background: %(faixa)s; border: none; }
#bannerText { color: %(faixa_texto)s; font-weight: 600; }

#panel { background: %(superficie)s; border: 1px solid %(borda)s; border-radius: 12px; }
#panel QLabel, #panel QCheckBox, #panel QRadioButton { background: transparent; }
#sectionTitle { font-size: 11pt; font-weight: 700; }
#sectionSubtitle, #hint, #status, #signature { color: %(suave)s; font-size: 9pt; }
#pageTitle { font-size: 20pt; font-weight: 750; }
#pageSubtitle { color: %(suave)s; }
#fieldLabel { color: %(suave)s; font-size: 9pt; font-weight: 600; }
#textOk { color: %(ok)s; } #textWarning { color: %(alerta)s; } #textError { color: %(erro)s; }
#statusbar { color: %(suave)s; border-top: 1px solid %(borda)s; }
#caixa { background: transparent; }
#mono, #log { font-family: Consolas, 'Courier New', monospace; font-size: 9pt; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit, QPlainTextEdit {
        background: %(superficie)s; color: %(texto)s; border: 1px solid %(borda)s;
        border-radius: 8px; padding: 8px 10px;
        selection-background-color: %(marca)s; selection-color: %(marca_texto)s; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus,
QTextEdit:focus, QPlainTextEdit:focus { border: 2px solid %(marca)s; padding: 7px 9px; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { color: %(suave)s;
        background: %(superficie2)s; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QLineEdit { border: none; padding: 0 2px; background: transparent; }
QComboBox::down-arrow { image: url(%(seta)s); width: 10px; height: 6px; margin-right: 8px; }
QComboBox QAbstractItemView { background: %(superficie)s; color: %(texto)s;
        border: 1px solid %(borda)s; selection-background-color: %(marca_suave)s;
        selection-color: %(marca)s; outline: none; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button,
QDoubleSpinBox::down-button { width: 0; border: none; }

QPushButton { background: %(superficie)s; color: %(texto)s; border: 1px solid %(borda)s;
        border-radius: 8px; padding: 8px 13px; }
QPushButton:hover { background: %(superficie2)s; border-color: %(marca)s; }
QPushButton:checked { background: %(marca_suave)s; color: %(marca)s;
        border-color: %(marca)s; font-weight: 600; }
QPushButton:disabled { color: %(suave)s; background: %(superficie2)s; border-color: %(borda)s; }
QPushButton::menu-indicator { width: 0; }
#primary { background: %(marca)s; color: %(marca_texto)s; border-color: %(marca)s; font-weight: 650; }
#primary:hover { background: %(marca_hover)s; }
#primary:disabled { background: %(borda)s; border-color: %(borda)s; color: %(suave)s; }
#danger { color: %(erro)s; border-color: %(erro)s; }
#danger:hover { background: %(erro_fundo)s; border-color: %(erro)s; }
#danger:disabled { color: %(suave)s; border-color: %(borda)s; background: %(superficie2)s; }
#discreto, #small { padding: 4px 9px; font-size: 9pt; }
#discreto { color: %(suave)s; }
#link, #headerLink { background: transparent; border: none; padding: 2px 4px;
        text-decoration: underline; }
#link { color: %(marca)s; }
#headerLink { color: %(cabecalho_suave)s; }
#link:hover { color: %(marca_hover)s; background: transparent; }
#headerLink:hover { color: white; background: transparent; }

QCheckBox, QRadioButton { spacing: 7px; background: transparent; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px;
        background: %(superficie)s; border: 1px solid %(suave)s; }
QCheckBox::indicator { border-radius: 4px; }
QRadioButton::indicator { border-radius: 9px; }
QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: %(marca)s; }
QCheckBox::indicator:checked { background: %(marca)s; border-color: %(marca)s;
        image: url(%(visto)s); }
QRadioButton::indicator:checked { background: %(superficie)s; border: 5px solid %(marca)s;
        width: 8px; height: 8px; }
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
        background: %(superficie2)s; border-color: %(borda)s; }
QCheckBox::indicator:checked:disabled { background: %(borda)s; }
QCheckBox:disabled, QRadioButton:disabled, QLabel:disabled { color: %(suave)s; }

QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; color: %(suave)s; padding: 10px 18px;
        border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: %(marca)s; border-bottom-color: %(marca)s; font-weight: 650; }
QTabBar::tab:hover { color: %(texto)s; }

QTableWidget, QTableView, QTreeWidget, QTreeView, QListWidget, QListView {
        background: %(superficie)s; alternate-background-color: %(superficie2)s;
        border: 1px solid %(borda)s; border-radius: 10px; gridline-color: %(borda)s;
        selection-background-color: %(marca)s; selection-color: %(marca_texto)s; outline: none; }
#flat { border: none; border-radius: 0; }
QTableWidget::item, QTableView::item, QTreeWidget::item, QTreeView::item,
QListWidget::item, QListView::item { padding: 5px; }
QTableWidget::item:selected, QTableView::item:selected, QTreeWidget::item:selected,
QTreeView::item:selected, QListWidget::item:selected, QListView::item:selected {
        background: %(marca)s; color: %(marca_texto)s; }
QHeaderView::section { background: %(marca_suave)s; color: %(texto)s; padding: 8px 6px;
        border: none; border-bottom: 1px solid %(borda)s; font-weight: 650; }
QTableCornerButton::section { background: %(marca_suave)s; border: none; }

QScrollArea { border: none; background: transparent; }
#panel QScrollArea, #panel QScrollArea > QWidget > QWidget { background: %(superficie)s; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar:horizontal { height: 10px; background: transparent; margin: 2px; }
QScrollBar::handle { background: %(borda)s; border-radius: 4px; }
QScrollBar::handle:hover { background: %(suave)s; }
QScrollBar::handle:vertical { min-height: 40px; }
QScrollBar::handle:horizontal { min-width: 40px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QProgressBar { background: %(marca_suave)s; border: none; border-radius: 4px;
        max-height: 8px; text-align: center; color: transparent; }
QProgressBar::chunk { background: %(marca)s; border-radius: 4px; }

QMenu { background: %(superficie)s; color: %(texto)s; border: 1px solid %(borda)s; padding: 6px; }
QMenu::item { padding: 8px 22px; border-radius: 6px; }
QMenu::item:selected { background: %(marca_suave)s; color: %(marca)s; }
QMenu::item:disabled { color: %(suave)s; }
QMenu::separator { height: 1px; background: %(borda)s; margin: 4px 8px; }

QGroupBox { border: 1px solid %(borda)s; border-radius: 10px; margin-top: 14px;
        padding: 12px 10px 10px 10px; font-weight: 650; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
QSplitter::handle { background: transparent; }
"""


# Notebook com tela pequena (1366x768 em 125% deixa ~1090x610 úteis): menos
# respiro em campo, botão e cabeçalho. O resto da janela é do programa.
_ESTILO_COMPACTO = """
* { font-size: 9pt; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit, QPlainTextEdit {
        padding: 5px 8px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus,
QTextEdit:focus, QPlainTextEdit:focus { padding: 4px 7px; }
QPushButton { padding: 5px 10px; }
#headerButton, #headerPrimary { padding: 5px 10px; }
#brandTitle { font-size: 11pt; }
#header QLabel#logo, #logo { font-size: 10pt; border-radius: 7px; }
#sectionTitle { font-size: 10pt; }
#pageTitle { font-size: 15pt; }
QTabBar::tab { padding: 6px 14px; }
QHeaderView::section { padding: 5px 5px; }
QTableWidget::item, QTableView::item, QTreeWidget::item, QTreeView::item { padding: 2px; }
"""


def tela_baixa():
    """A tela útil é baixa (notebook)? CR2_COMPACTO=1/0 força, para testar."""
    forcado = os.environ.get("CR2_COMPACTO")
    if forcado in ("0", "1"):
        return forcado == "1"
    tela = QGuiApplication.primaryScreen()
    return bool(tela) and tela.availableGeometry().height() < 760


def estilo(modo, extra=""):
    """A folha de estilo da janela inteira.

    `extra` é QSS do próprio programa (regras que só ele usa). Pode citar as
    cores do mesmo jeito: %(marca)s, %(borda)s... Prefira os nomes de objeto
    da lista acima a inventar regra nova: é o que mantém tudo parecido.
    """
    c = dict(paleta(modo), seta=seta(paleta(modo)["suave"]),
             visto=visto(paleta(modo)["marca_texto"]))
    if tela_baixa():
        extra = _ESTILO_COMPACTO + extra
    return (_ESTILO + extra) % c


# --------------------------------------------------------------------------
# Peças da janela
# --------------------------------------------------------------------------
class Cabecalho(QFrame):
    """A faixa escura do alto: marca, título, subtítulo e botão de tema.

    Botões próprios do programa entram com `adicionar(widget)`, à esquerda
    do botão de tema.
    """

    tema_clicado = Signal()

    def __init__(self, titulo, subtitulo="", logo_png=None):
        super().__init__()
        self.setObjectName("header")
        compacto = tela_baixa()
        self.linha = QHBoxLayout(self)
        self.linha.setContentsMargins(*((16, 6, 16, 6) if compacto
                                        else (24, 14, 24, 14)))
        self.linha.setSpacing(8 if compacto else 12)
        self._avisou_central = False

        # Aberto pela Central: o "← Menu" vem primeiro, e a janela inteira
        # é entregue para ser encaixada nela (ver a classe Central).
        self.botao_menu = None
        if Central.ligada():
            self.botao_menu = QPushButton("←  Menu")
            self.botao_menu.setObjectName("headerButton")
            self.botao_menu.setToolTip(
                "Volta ao menu da Central. O que estiver rodando aqui continua.")
            self.botao_menu.clicked.connect(lambda: Central.enviar(tipo="voltar"))
            self.linha.addWidget(self.botao_menu)

        logo = QLabel()
        imagem = QPixmap(logo_png) if logo_png and os.path.isfile(logo_png) \
            else QPixmap()
        alto = 30 if compacto else 42
        if not imagem.isNull():
            logo.setPixmap(imagem.scaledToHeight(
                alto, Qt.TransformationMode.SmoothTransformation))
        else:
            logo.setText("CR2")
            logo.setObjectName("logo")
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setFixedSize(int(alto * 8 / 7), alto)
        self.linha.addWidget(logo)

        textos = QVBoxLayout()
        textos.setSpacing(1)
        self.titulo = QLabel(titulo)
        self.titulo.setObjectName("brandTitle")
        textos.addWidget(self.titulo)
        self.subtitulo = QLabel(subtitulo)
        self.subtitulo.setObjectName("brandSubtitle")
        # em tela baixa o subtítulo sai: é a linha que mais custa altura
        self.subtitulo.setVisible(bool(subtitulo) and not compacto)
        textos.addWidget(self.subtitulo)
        self.linha.addLayout(textos)
        self.linha.addStretch(1)

        # Na Central: o andamento dos OUTROS programas abertos, discreto.
        self.outros = QLabel("")
        self.outros.setObjectName("brandSubtitle")
        self.outros.setVisible(False)
        self.linha.addWidget(self.outros)
        if Central.ligada():
            Central.instancia().outros.connect(self._mostrar_outros)

        self.modo = None
        self.botao_tema = QPushButton("☾  Modo escuro")
        self.botao_tema.setObjectName("headerButton")
        # na Central o tema é UM só: o botão pede à Central, que troca o
        # dela e o de todos os programas abertos (ver _seguir_tema). Solto
        # (sem Central, ou depois que ela fechou), o tema volta a ser dele.
        self.botao_tema.clicked.connect(self._clicou_tema)
        if Central.ligada():
            Central.instancia().tema.connect(self._seguir_tema)
            Central.instancia().solto.connect(self._ficou_solto)
        self.linha.addWidget(self.botao_tema)

    def adicionar(self, widget):
        """Um botão (ou outro widget) do programa, antes do botão de tema."""
        self.linha.insertWidget(self.linha.indexOf(self.botao_tema), widget)
        return widget

    def mostrar_modo(self, modo):
        """O botão diz para onde vai, como na janela Tk."""
        self.modo = modo
        self.botao_tema.setText("☀  Modo claro" if modo == "escuro"
                                else "☾  Modo escuro")
        if Central.ligada():
            Central.enviar(tipo="modo", modo=modo)
            desejado = Central.instancia().modo_desejado
            if desejado and desejado != modo:
                QTimer.singleShot(0, lambda: self._seguir_tema(desejado))

    def _clicou_tema(self):
        if Central.ligada() and not Central.instancia().esta_solto:
            Central.enviar(tipo="alternar_tema")
        else:
            self.tema_clicado.emit()

    def _ficou_solto(self):
        """A Central fechou e deixou o programa aberto: o "← Menu" não leva
        mais a lugar nenhum."""
        if self.botao_menu is not None:
            self.botao_menu.hide()
        self.outros.hide()

    def _seguir_tema(self, modo):
        """A Central mandou este tema: troca pelo caminho do próprio programa
        (o mesmo do botão), que aplica a folha e grava a config dele."""
        if self.modo is not None and self.modo != modo:
            self.tema_clicado.emit()

    def _mostrar_outros(self, texto):
        self.outros.setText(texto)
        self.outros.setVisible(bool(texto))

    def showEvent(self, evento):
        # O showEvent do cabeçalho chega ANTES de a janela aparecer na tela:
        # é a hora de entregá-la à Central sem ela piscar solta no monitor.
        if Central.ligada() and not self._avisou_central                 and Central.instancia().janela is None:
            self._avisou_central = True
            Central.instancia().entregar(self.window(), self.titulo.text())
        super().showEvent(evento)


class Faixa(QFrame):
    """Aviso amarelo abaixo do cabeçalho. Escondido enquanto não há aviso."""

    def __init__(self):
        super().__init__()
        self.setObjectName("banner")
        linha = QHBoxLayout(self)
        linha.setContentsMargins(24, 10, 24, 10)
        self.texto = QLabel("")
        self.texto.setObjectName("bannerText")
        self.texto.setWordWrap(True)
        linha.addWidget(self.texto, 1)
        self.botao = QPushButton("")
        self.botao.setObjectName("primary")
        linha.addWidget(self.botao)
        self._comando = None
        self.botao.clicked.connect(lambda: self._comando and self._comando())
        self.hide()

    def mostrar(self, texto, rotulo_botao=None, comando=None):
        self.texto.setText(texto)
        self._comando = comando
        self.botao.setVisible(bool(rotulo_botao and comando))
        if rotulo_botao:
            self.botao.setText(rotulo_botao)
            self.botao.setEnabled(True)
        self.show()


class Painel(QFrame):
    """O cartão de bordas redondas. Ponha o conteúdo em `painel.conteudo`."""

    def __init__(self, titulo="", subtitulo=""):
        super().__init__()
        self.setObjectName("panel")
        self.conteudo = QVBoxLayout(self)
        # notebook: menos respiro dentro do cartão
        if tela_baixa():
            self.conteudo.setContentsMargins(12, 9, 12, 9)
            self.conteudo.setSpacing(6)
        else:
            self.conteudo.setContentsMargins(18, 16, 18, 16)
            self.conteudo.setSpacing(10)
        if titulo:
            rotulo = QLabel(titulo)
            rotulo.setObjectName("sectionTitle")
            self.conteudo.addWidget(rotulo)
        if subtitulo:
            rotulo = QLabel(subtitulo)
            rotulo.setObjectName("sectionSubtitle")
            rotulo.setWordWrap(True)
            self.conteudo.addWidget(rotulo)


def caber_na_tela(janela, largura, altura, minimo=None):
    """Dá à janela o tamanho pedido, sem passar da área útil da tela.

    Desconta a barra de título e a moldura (o que resize() não conta). Em
    tela baixa o mínimo cai para `minimo` (padrão 960x520): um mínimo fixo
    maior que o notebook é o que espremia os painéis.
    """
    tela = janela.screen() or QGuiApplication.primaryScreen()
    if tela is not None:
        area = tela.availableGeometry()
        largura = min(largura, area.width() - 16)
        altura = min(altura, area.height() - 40)
    if tela_baixa():
        ml, ma = minimo or (960, 520)
        janela.setMinimumSize(min(ml, largura), min(ma, altura))
    janela.resize(largura, altura)


def rolagem(conteudo_layout=None):
    """Uma área com rolagem vertical para um painel que pode não caber.

    Devolve (area, layout_do_miolo). O miolo se chama "caixa" (a folha o
    deixa transparente, com a cor do cartão em volta).
    """
    from PySide6.QtWidgets import QScrollArea, QWidget
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    miolo = QWidget()
    miolo.setObjectName("caixa")
    layout = conteudo_layout or QVBoxLayout()
    layout.setContentsMargins(0, 0, 4, 0)
    miolo.setLayout(layout)
    area.setWidget(miolo)
    return area, layout


def campo(titulo, widget):
    """Rótulo pequeno em cima, campo embaixo — o par de todo formulário."""
    caixa = QVBoxLayout()
    caixa.setSpacing(5)
    rotulo = QLabel(titulo)
    rotulo.setObjectName("fieldLabel")
    rotulo.setBuddy(widget)
    caixa.addWidget(rotulo)
    caixa.addWidget(widget)
    return caixa


def botao(texto, objeto=None, ao_clicar=None, dica=None):
    """Botão com nome de objeto da folha (primary, danger, discreto...)."""
    b = QPushButton(texto)
    if objeto:
        b.setObjectName(objeto)
    if ao_clicar:
        b.clicked.connect(ao_clicar)
    if dica:
        b.setToolTip(dica)
    return b


def repolir(widget, objeto):
    """Troca o nome de objeto e faz o estilo novo valer na hora."""
    widget.setObjectName(objeto)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# --------------------------------------------------------------------------
# Rodando dentro da Central (tela única)
# --------------------------------------------------------------------------
class Central(QObject):
    """A conversa do programa com a Central, quando foi ela que o abriu.

    A Central passa, no ambiente, o nome de um canal local (CR2_CENTRAL) e o
    id do programa (CR2_APP_ID). Por esse canal vão, uma linha JSON cada:

        programa -> Central   ola, janela (o HWND, para encaixar), voltar,
                              progresso (ocupado, pct, texto)
        Central -> programa   fechar, outros (andamento dos outros abertos)

    O progresso não pede nada ao programa: a cada segundo olha-se a barra de
    progresso (QProgressBar) e a linha de status da própria janela.
    Fora da Central (sem CR2_CENTRAL) nada disto liga: o programa é igual.
    """

    outros = Signal(str)
    tema = Signal(str)
    solto = Signal()
    _unica = None
    # Lido uma vez e TIRADO do ambiente: um processo que o programa abrir
    # (um segundo programa, um navegador) não herda o canal e não tenta se
    # encaixar no lugar dele.
    _canal = os.environ.pop("CR2_CENTRAL", "")
    _app = os.environ.pop("CR2_APP_ID", "")
    _tema = os.environ.pop("CR2_TEMA", "")

    @classmethod
    def ligada(cls):
        return bool(cls._canal)

    @classmethod
    def instancia(cls):
        if cls._unica is None:
            cls._unica = cls()
        return cls._unica

    @classmethod
    def enviar(cls, **recado):
        if cls.ligada():
            cls.instancia()._enviar(recado)

    def __init__(self):
        super().__init__()
        from PySide6.QtNetwork import QLocalSocket
        self.janela = None
        self.esta_solto = False
        self.modo_desejado = self._tema
        self._ultimo = None
        self._buffer = b""
        self.sock = QLocalSocket(self)
        self.sock.readyRead.connect(self._ler)
        self.sock.disconnected.connect(self._soltou)
        self.sock.connectToServer(self._canal)
        self.sock.waitForConnected(2000)
        self._enviar({"tipo": "ola", "app": self._app, "pid": os.getpid()})
        self.relogio = QTimer(self)
        self.relogio.timeout.connect(self._olhar_progresso)

    def _enviar(self, recado):
        try:
            self.sock.write((json.dumps(recado, ensure_ascii=False) + "\n")
                            .encode("utf-8"))
            self.sock.flush()
        except Exception:
            pass

    def entregar(self, janela, titulo):
        # Só a PRIMEIRA janela do programa vai para a Central. Uma segunda
        # (o "Somente contratos" do Gestor, por exemplo) abre solta, como
        # sempre abriu.
        if self.janela is not None:
            return
        self.janela = janela
        # fora da tela até a Central encaixar: nada de piscar solta
        janela.move(-32000, -32000)
        self._enviar({"tipo": "janela", "hwnd": int(janela.winId()),
                      "titulo": titulo})
        self.relogio.start(1000)

    def _ler(self):
        self._buffer += bytes(self.sock.readAll())
        while b"\n" in self._buffer:
            linha, self._buffer = self._buffer.split(b"\n", 1)
            try:
                recado = json.loads(linha.decode("utf-8"))
            except ValueError:
                continue
            if recado.get("tipo") == "fechar" and self.janela is not None:
                self.janela.close()         # o closeEvent do programa decide
            elif recado.get("tipo") == "outros":
                self.outros.emit(recado.get("texto", ""))
            elif recado.get("tipo") == "solto":
                self._soltou()
            elif recado.get("tipo") == "tema":
                self.modo_desejado = recado.get("modo", "")
                self.tema.emit(self.modo_desejado)

    def _soltou(self):
        if not self.esta_solto:
            self.esta_solto = True
            self.relogio.stop()
            self.solto.emit()

    def _olhar_progresso(self):
        if self.janela is None:
            return
        ocupado, pct = False, None
        for barra in self.janela.findChildren(QProgressBar):
            if not barra.isVisibleTo(self.janela):
                continue
            if barra.maximum() == 0 and barra.minimum() == 0:
                ocupado = True              # barra "andando", sem total
            elif barra.maximum() > barra.minimum() and \
                    barra.minimum() < barra.value() < barra.maximum():
                ocupado = True
                pct = int(100 * (barra.value() - barra.minimum())
                          / (barra.maximum() - barra.minimum()))
        texto = ""
        for nome in ("status", "statusbar"):
            rotulo = self.janela.findChild(QLabel, nome)
            if rotulo is not None and rotulo.text().strip():
                texto = rotulo.text().strip().split("\n")[0][:120]
                break
        recado = {"tipo": "progresso", "ocupado": ocupado, "pct": pct,
                  "texto": texto}
        if recado != self._ultimo:
            self._ultimo = recado
            self._enviar(recado)


# --------------------------------------------------------------------------
# Trabalho fora da janela
# --------------------------------------------------------------------------
class SinaisTarefa(QObject):
    status = Signal(str)
    progresso = Signal(int, int, str)      # feitos, total, texto
    evento = Signal(object)                # recado livre do programa
    sucesso = Signal(object)
    erro = Signal(object, str)             # a exceção e o traceback (texto)
    fim = Signal()


def emitir(sinal, *args):
    """Emite sem quebrar quando a janela já foi fechada."""
    try:
        sinal.emit(*args)
    except RuntimeError:
        pass                                # o objeto Qt já foi destruído


class Tarefa(object):
    """Roda `funcao(sinais)` numa thread e devolve o resultado por sinais.

    A thread é daemon e do Python, não do QThreadPool, de propósito: o pool
    global do Qt segura o processo aberto até a última tarefa acabar, e uma
    coleta pode levar minutos — fechar a janela tem de fechar o programa.

    Os sinais nascem aqui, na thread da janela; o Qt entrega na thread da
    janela o que a função emitir de dentro da thread de trabalho. A função
    NUNCA toca widget: ela recebe os valores já lidos e fala por `sinais`.

        t = Tarefa(lambda s: coletar(cfg, avisar=s.status.emit))
        t.sinais.sucesso.connect(self._terminou)
        t.sinais.erro.connect(self._falhou)
        t.sinais.fim.connect(self._liberar)
        t.iniciar()
        self.tarefa = t        # guarde a referência enquanto ela roda
    """

    def __init__(self, funcao, nome="cr2-tarefa"):
        self.funcao = funcao
        self.nome = nome
        self.sinais = SinaisTarefa()
        self.thread = None
        self.detalhe = ""                  # o traceback, se a função falhou

    def iniciar(self):
        self.thread = threading.Thread(target=self._rodar, name=self.nome,
                                       daemon=True)
        self.thread.start()
        return self

    def rodando(self):
        return self.thread is not None and self.thread.is_alive()

    def _rodar(self):
        try:
            emitir(self.sinais.sucesso, self.funcao(self.sinais))
        except Exception as exc:            # noqa: BLE001 — a janela traduz
            self.detalhe = traceback.format_exc()
            emitir(self.sinais.erro, exc, self.detalhe)
        finally:
            emitir(self.sinais.fim)


# --------------------------------------------------------------------------
# A aplicação
# --------------------------------------------------------------------------
def preparar_aplicacao(id_windows=None):
    """Cria (ou devolve) a QApplication com a cara CR2.

    `id_windows` faz a barra de tarefas tratar a janela como do programa, e
    não como "um Python" — é o que deixa o ícone e o atalho fixado certos.
    """
    if id_windows:
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                id_windows)
        except Exception:
            pass
    app = QApplication.instance() or QApplication(sys.argv)
    _traduzir_qt(app)
    # o ícone da barra de tarefas: o "CR2" azul, em todos os programas (o
    # programa que tiver ícone próprio troca depois com setWindowIcon)
    app.setWindowIcon(icone_cr2())
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    return app


def icone_cr2():
    """O emblema CR2 (quadrado azul com "CR2"), desenhado aqui mesmo: assim
    nenhum programa precisa carregar um .ico para ter ícone na barra."""
    from PySide6.QtGui import QIcon, QPainter
    icone = QIcon()
    for lado in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        imagem = QPixmap(lado, lado)
        imagem.fill(Qt.GlobalColor.transparent)
        p = QPainter(imagem)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(CLARO["marca"]))
        p.drawRoundedRect(0, 0, lado, lado, lado * 0.22, lado * 0.22)
        p.setPen(QColor("white"))
        fonte = QFont("Segoe UI")
        fonte.setBold(True)
        # abaixo de 24px "CR2" vira borrão: fica só o "C"
        texto = "CR2" if lado >= 24 else "C"
        fonte.setPixelSize(int(lado * (0.40 if lado >= 24 else 0.72)))
        p.setFont(fonte)
        p.drawText(imagem.rect(), Qt.AlignmentFlag.AlignCenter, texto)
        p.end()
        icone.addPixmap(imagem)
    return icone


def _traduzir_qt(app):
    """Botões e caixas padrão do Qt em português ("Sim", "Não", "Cancelar",
    "Abrir"...). A tradução vem junto com o PySide6; sem ela, segue em inglês."""
    if getattr(app, "_cr2_traducao", None) is not None:
        return
    try:
        from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
        tradutor = QTranslator(app)
        pasta = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if tradutor.load(QLocale(QLocale.Language.Portuguese,
                                 QLocale.Country.Brazil), "qtbase", "_", pasta):
            app.installTranslator(tradutor)
            app._cr2_traducao = tradutor
    except Exception:
        pass


def registrar_erros(arquivo_log, titulo, limpar=None):
    """Erro inesperado vai para o arquivo e para uma caixa, sem derrubar.

    Sem isto, uma exceção dentro de um clique some: o PySide só a imprime
    num console que, no .pyw e no .exe, não existe.

    `limpar(texto) -> texto` passa o traceback por um filtro antes de gravar
    (para o programa que tira dado pessoal ou chave do log).
    """
    def gancho(tipo, valor, tb):
        texto = "".join(traceback.format_exception(tipo, valor, tb))
        if limpar is not None:
            try:
                texto = limpar(texto)
            except Exception:
                pass
        try:
            os.makedirs(os.path.dirname(arquivo_log), exist_ok=True)
            with open(arquivo_log, "a", encoding="utf-8") as f:
                f.write(texto + "\n" + "-" * 70 + "\n")
        except Exception:
            pass
        try:
            QMessageBox.critical(
                None, titulo,
                "Ocorreu um erro inesperado:\n\n%s\n\nDetalhes gravados em:\n%s"
                % (valor or tipo.__name__, arquivo_log))
        except Exception:
            pass
    sys.excepthook = gancho
    return gancho
