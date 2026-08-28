# -*- coding: utf-8 -*-
"""
Duas listas, e a diferença entre elas é o coração da Central.

    catalogo.json  ..  QUAIS automações existem. Fica dentro deste repositório
                       e vem do GitHub junto com a Central. Acrescentar uma
                       automação nova para todo mundo = uma entrada aqui e um
                       push. Ninguém precisa reinstalar nada.

    config.json    ..  ONDE elas estão NESTA máquina, e o tema escolhido. Fica
                       em %LOCALAPPDATA%\\CR2\\central e NUNCA vai para o git:
                       o caminho da pasta é assunto de cada computador.

É por isso que o caminho de instalação não mora no catálogo. Se morasse, o
push de um mudaria a pasta do outro.
"""

import json
import os
import sys

PASTA_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ_CATALOGO = os.path.join(PASTA_BASE, "catalogo.json")


def _pasta_config():
    """%LOCALAPPDATA%\\CR2\\central — com plano B fora do Windows."""
    raiz = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(raiz, "CR2", "central")


ARQ_CONFIG = os.path.join(_pasta_config(), "config.json")
ARQ_LOG = os.path.join(_pasta_config(), "erros.log")


def pasta_apps_padrao():
    raiz = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(raiz, "CR2", "apps")


# --------------------------------------------------------------------------
# O catálogo
# --------------------------------------------------------------------------
class App(object):
    """Uma automação do catálogo, já com o que a tela precisa saber."""

    def __init__(self, bruto):
        self.id = bruto["id"]
        self.nome = bruto.get("nome", self.id)
        self.descricao = bruto.get("descricao", "")
        self.repo = bruto.get("repo", "")
        self.entrada = bruto.get("entrada", "")
        self.tipo = bruto.get("tipo", "janela")      # janela | terminal
        self.subpasta = bruto.get("subpasta", "")
        self.observacao = bruto.get("observacao", "")
        # Emoji que a Central desenha no cartão. Opcional: sem ele, a Central
        # usa um ícone padrão, e o catálogo antigo continua funcionando.
        self.icone = bruto.get("icone", "")

    @property
    def url_github(self):
        """Endereço para abrir no navegador (sem o .git do fim)."""
        u = self.repo.strip()
        return u[:-4] if u.endswith(".git") else u

    def pasta_do_programa(self, pasta_clone):
        """Onde fica o executável: a raiz do clone, ou uma subpasta dele.

        Repositório com várias ferramentas dentro (uma pasta por script) usa
        subpasta; um repositório de um app só deixa vazio.
        """
        if self.subpasta:
            return os.path.join(pasta_clone, *self.subpasta.split("/"))
        return pasta_clone


def carregar_catalogo(caminho=None):
    """Lê o catalogo.json. Erro de leitura vira exceção com texto claro."""
    caminho = caminho or ARQ_CATALOGO
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        raise RuntimeError("O catálogo não foi encontrado:\n%s" % caminho)
    except ValueError as e:
        raise RuntimeError("O catálogo está com defeito de formatação:\n%s"
                           % e)
    apps, vistos = [], set()
    for bruto in dados.get("apps", []):
        if not bruto.get("id") or not bruto.get("repo"):
            continue
        if bruto["id"] in vistos:       # id repetido: vale o primeiro
            continue
        vistos.add(bruto["id"])
        apps.append(App(bruto))
    return apps


# --------------------------------------------------------------------------
# A configuração desta máquina
# --------------------------------------------------------------------------
PADRAO = {
    "tema": "claro",
    "pasta_apps": "",        # vazio = pasta_apps_padrao()
    "caminhos": {},          # id -> pasta escolhida à mão
    "buscar_ao_abrir": True,
}


def carregar_config():
    cfg = dict(PADRAO)
    cfg["caminhos"] = {}
    try:
        with open(ARQ_CONFIG, encoding="utf-8") as f:
            gravado = json.load(f)
        if isinstance(gravado, dict):
            cfg.update(gravado)
            if not isinstance(cfg.get("caminhos"), dict):
                cfg["caminhos"] = {}
    except (OSError, ValueError):
        # Primeira execução, ou arquivo corrompido: os padrões servem, e
        # insistir num erro aqui só impediria a janela de abrir.
        pass
    return cfg


def salvar_config(cfg):
    try:
        os.makedirs(_pasta_config(), exist_ok=True)
        with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def pasta_do_app(app, cfg):
    """Onde este computador guarda (ou vai guardar) o clone deste app."""
    escolhida = (cfg.get("caminhos") or {}).get(app.id)
    if escolhida:
        return escolhida
    base = cfg.get("pasta_apps") or pasta_apps_padrao()
    return os.path.join(base, app.id)


def fixar_pasta(app, cfg, caminho):
    cfg.setdefault("caminhos", {})[app.id] = os.path.abspath(caminho)
    salvar_config(cfg)


def esquecer_pasta(app, cfg):
    (cfg.get("caminhos") or {}).pop(app.id, None)
    salvar_config(cfg)


# --------------------------------------------------------------------------
# A própria Central
# --------------------------------------------------------------------------
def pasta_da_central():
    """A pasta deste repositório — a Central também se atualiza sozinha."""
    return PASTA_BASE


def python_de_janela():
    """O executável que abre .py sem console preto atrás (pythonw.exe).

    sys.executable já é o pythonw quando a Central foi aberta pelo .bat; o
    replace cobre quem rodou pelo python.exe do terminal.
    """
    exe = sys.executable or "python"
    if os.name == "nt":
        alternativo = exe.replace("python.exe", "pythonw.exe")
        if alternativo != exe and os.path.isfile(alternativo):
            return alternativo
    return exe


def python_de_terminal():
    """O executável com console, para as ferramentas de linha de comando."""
    exe = sys.executable or "python"
    if os.name == "nt":
        alternativo = exe.replace("pythonw.exe", "python.exe")
        if alternativo != exe and os.path.isfile(alternativo):
            return alternativo
    return exe
