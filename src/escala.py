# -*- coding: utf-8 -*-
"""
Escala da janela em tela de notebook — o Windows em 125%, 150%, 175%.

O PROBLEMA
Notebook com Windows vem de fábrica com "Escala e layout" em 125%. Um programa
que não se declara ciente do DPI recebe do Windows uma tela mentirosa — ele
"vê" 1536x864 onde existem 1920x1080 — e a janela pronta é esticada por cima,
como uma imagem ampliada. Dá nos dois sintomas juntos: texto borrado, e janela
que pede 1320 de largura ocupando 1650 da tela, com o rodapé e os botões
sobrando para fora. Em 100% nada disso aparece, e por isso o bug passa
despercebido em computador de mesa.

O CONSERTO, em duas partes:

1. preparar(), ANTES de criar o tk.Tk(). O processo se declara ciente do DPI,
   o Windows para de esticar e passa a entregar a tela de verdade.

2. medir(raiz), LOGO DEPOIS de criar o tk.Tk(). Descobre o DPI e ajusta o
   `tk scaling` do Tk, que é o número que faz "12 pontos" virar 20 pixels em
   125% e 16 pixels em 100%. Daí para a frente toda fonte em ponto acompanha
   o Windows sozinha.

O que NÃO acompanha sozinho é pixel escrito na mão: o "1320x780" da janela, a
altura da linha da tabela, o wraplength do rótulo. Para esses existe px(), que
converte um pixel pensado em 100% para o pixel da tela de agora.

CIENTE DO SISTEMA, E NÃO DO MONITOR  (SetProcessDpiAwareness(1), não o (2))
O Tk 8.6 não sabe reagir ao WM_DPICHANGED, o aviso que o Windows manda quando
a janela passa para um monitor de DPI diferente. Declarado "por monitor", o
programa ficaria responsável por redesenhar tudo nessa hora — e, como não faz
isso, a janela arrastada para o segundo monitor ficaria do tamanho errado sem
conserto. Declarado "do sistema", esse caso volta a ser esticado pelo Windows:
borrado, porém do tamanho certo. Para notebook de tela única, que é o caso
deste bug, os dois são idênticos.

PARA TESTAR SEM UM NOTEBOOK À MÃO
    set CR2_ESCALA=1.25
e abrir o programa: a janela fica exatamente como ficaria num notebook em 125%,
mesmo num monitor em 100%. Serve qualquer fator (1.25, 1.5, 1.75).
"""

import ctypes
import os
import sys

# O DPI em que os números de pixel destes programas foram pensados: 96 é o
# 100% do Windows. Um valor em px() é multiplicado por DPI_da_tela / 96.
DPI_BASE = 96.0

# Preenchido por medir(). Fica em 1.0 enquanto ninguém mediu, de modo que px()
# devolve o número que recebeu e nada quebra se alguém esquecer a chamada.
FATOR = 1.0

_WINDOWS = sys.platform.startswith("win")


# --------------------------------------------------------------------------
# 1) Antes do tk.Tk()
# --------------------------------------------------------------------------
def preparar():
    """Declara o processo ciente do DPI. Chame antes de criar a janela.

    Depois que a primeira janela existe o Windows não deixa mais mudar isso, e
    é por essa razão que a chamada tem de vir antes do tk.Tk().

    Devolve True se o processo ficou ciente do DPI. Não levanta erro nunca: num
    Windows antigo demais, ou fora do Windows, o programa continua abrindo
    exatamente como abria antes.
    """
    if not _WINDOWS:
        return False

    # Windows 8.1 em diante. 1 = PROCESS_SYSTEM_DPI_AWARE.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return True
    except AttributeError:
        pass            # shcore.dll não existe (Windows 7)
    except OSError:
        # E_ACCESSDENIED: já estava definido, por manifesto ou por outra
        # chamada. Já é o que se queria.
        return True

    # Windows Vista/7.
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return True
    except (AttributeError, OSError):
        return False


# --------------------------------------------------------------------------
# 2) Depois do tk.Tk()
# --------------------------------------------------------------------------
def medir(raiz):
    """Descobre a escala da tela, ajusta o Tk e devolve o fator.

    Chame uma vez, logo depois de criar a janela principal e antes de montar os
    widgets — o `tk scaling` precisa estar certo enquanto o Tk calcula o
    tamanho de cada texto.
    """
    global FATOR
    FATOR = _fator_forcado() or (_dpi(raiz) / DPI_BASE)

    # O Tk conta em pontos tipográficos: 1 ponto = 1/72 de polegada. O scaling
    # é quantos pixels tem um ponto, e é ele que dá tamanho à fonte.
    try:
        raiz.tk.call("tk", "scaling", FATOR * DPI_BASE / 72.0)
    except Exception:
        pass
    return FATOR


def _fator_forcado():
    """Fator vindo do CR2_ESCALA, para testar 125% num monitor em 100%."""
    texto = os.environ.get("CR2_ESCALA", "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        valor = float(texto)
    except ValueError:
        return None
    # 125 e 1.25 querem dizer a mesma coisa. Abaixo de 0.5 ou acima de 4 é
    # engano de digitação, e janela ilegível não ajuda ninguém.
    if valor > 4:
        valor = valor / 100.0
    return valor if 0.5 <= valor <= 4.0 else None


def _dpi(raiz):
    """DPI da tela em que a janela está. 96 quando não dá para saber."""
    if _WINDOWS:
        u32 = ctypes.windll.user32
        # GetDpiForWindow é o valor exato da janela (Windows 10 1607+).
        try:
            raiz.update_idletasks()
            valor = u32.GetDpiForWindow(raiz.winfo_id())
            if valor:
                return float(valor)
        except Exception:
            pass
        # GetDpiForSystem: o DPI do monitor principal (Windows 10 1607+).
        try:
            valor = u32.GetDpiForSystem()
            if valor:
                return float(valor)
        except Exception:
            pass
    # Último recurso: o que o próprio Tk acha que é uma polegada.
    try:
        valor = float(raiz.winfo_fpixels("1i"))
        if valor:
            return valor
    except Exception:
        pass
    return DPI_BASE


# --------------------------------------------------------------------------
# Converter os pixels escritos na mão
# --------------------------------------------------------------------------
def px(valor):
    """Pixel pensado em 100% -> pixel desta tela. px(24) = 30 em 125%."""
    return int(round(valor * FATOR))


def area_util(raiz):
    """(x, y, largura, altura) da tela sem a barra de tarefas, em px de verdade.

    É onde uma janela cabe sem nascer por baixo da barra de tarefas nem com o
    rodapé fora da tela — o outro jeito de um programa aparecer "fora de
    escala" num notebook, que costuma ter tela menor que a do escritório.
    """
    if _WINDOWS:
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        r = RECT()
        try:
            # 0x0030 = SPI_GETWORKAREA
            if ctypes.windll.user32.SystemParametersInfoW(
                    0x0030, 0, ctypes.byref(r), 0):
                return (r.left, r.top, r.right - r.left, r.bottom - r.top)
        except Exception:
            pass
    try:
        # Sem a barra de tarefas de verdade, desconta uma barra típica.
        return (0, 0, raiz.winfo_screenwidth(),
                max(360, raiz.winfo_screenheight() - px(56)))
    except Exception:
        return (0, 0, 1024, 700)


def tamanho(raiz, largura, altura):
    """Largura e altura já escaladas e já limitadas ao que cabe na tela."""
    _, _, larg_tela, alt_tela = area_util(raiz)
    return (min(px(largura), larg_tela), min(px(altura), alt_tela))


def geometria(janela, largura, altura, centralizar=True):
    """Aplica geometry() com o tamanho escalado, cabendo e centralizado.

    largura e altura são os números de sempre, pensados em 100%.
    """
    x0, y0, larg_tela, alt_tela = area_util(janela)
    larg = min(px(largura), larg_tela)
    alt = min(px(altura), alt_tela)
    if centralizar:
        x = x0 + max(0, (larg_tela - larg) // 2)
        y = y0 + max(0, (alt_tela - alt) // 2)
        janela.geometry("%dx%d+%d+%d" % (larg, alt, x, y))
    else:
        janela.geometry("%dx%d" % (larg, alt))
    return larg, alt


def minimo(janela, largura, altura):
    """minsize() escalado, sem jamais exigir mais do que a tela tem."""
    larg, alt = tamanho(janela, largura, altura)
    janela.minsize(larg, alt)
    return larg, alt
