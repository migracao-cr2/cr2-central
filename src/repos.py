# -*- coding: utf-8 -*-
"""
Tudo que a Central sabe sobre git fica aqui — e só aqui.

A Central não reimplementa git: ela conversa com o git da máquina por
subprocess. Isso é de propósito. O Credential Manager do Windows já guarda o
login do GitHub, então repositório privado clona e atualiza sem nenhum token
escrito em arquivo. Na primeira vez numa máquina nova o próprio Credential
Manager abre o navegador pedindo o login; depois disso, nunca mais.

Regras que valem para toda chamada daqui:

  * NENHUMA janela preta pisca. No Windows, todo subprocess leva
    CREATE_NO_WINDOW (ver _sem_janela).
  * GIT_TERMINAL_PROMPT=0. Sem isso, um git sem credencial fica parado para
    sempre esperando alguém digitar num terminal que não existe, e a Central
    congela sem dizer por quê.
  * LC_ALL=C. As mensagens do git vêm em inglês, previsíveis, para a leitura
    não depender do idioma da máquina.
  * Nada aqui toca em Tkinter. Estas funções rodam na thread de trabalho.
"""

import os
import shutil
import subprocess

TEMPO_PADRAO = 180          # segundos; clone grande em rede ruim
MAX_COMMITS_MOSTRADOS = 12


class ErroGit(Exception):
    """Falha numa chamada ao git, já com a mensagem pronta para a tela."""


# --------------------------------------------------------------------------
# Encanamento
# --------------------------------------------------------------------------
def _sem_janela():
    """Opções de subprocess que impedem o console de piscar no Windows."""
    if os.name != "nt":
        return {}
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {"startupinfo": info, "creationflags": 0x08000000}


def _ambiente():
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["LC_ALL"] = "C"
    return env


def caminho_git():
    """Onde está o git.exe, ou None."""
    return shutil.which("git")


def disponivel():
    return caminho_git() is not None


def rodar(args, pasta=None, tempo=TEMPO_PADRAO):
    """Chama o git e devolve a saída. Levanta ErroGit quando dá errado."""
    git = caminho_git()
    if git is None:
        raise ErroGit("O git não está instalado nesta máquina.")
    try:
        p = subprocess.run(
            [git] + list(args),
            cwd=pasta,
            env=_ambiente(),
            capture_output=True,
            timeout=tempo,
            **_sem_janela()
        )
    except subprocess.TimeoutExpired:
        raise ErroGit("O git demorou demais e foi interrompido. "
                      "Verifique a conexão.")
    saida = p.stdout.decode("utf-8", "replace").strip()
    erro = p.stderr.decode("utf-8", "replace").strip()
    if p.returncode != 0:
        raise ErroGit(_traduzir(erro or saida))
    return saida


def _traduzir(mensagem):
    """Deixa em português os poucos erros que a pessoa realmente vai ver."""
    m = (mensagem or "").lower()
    if ("could not read username" in m or "authentication failed" in m
            or "terminal prompts disabled" in m):
        return ("O GitHub recusou o acesso. Este repositório é privado: "
                "faça o login do GitHub uma vez nesta máquina — o Windows "
                "guarda daí em diante.")
    if "repository not found" in m:
        return ("Repositório não encontrado. Ou o endereço está errado, ou "
                "esta conta do GitHub não tem acesso a ele.")
    if "could not resolve host" in m or "unable to access" in m:
        return "Sem conexão com o GitHub."
    if "not possible to fast-forward" in m or "diverging" in m:
        return ("Esta cópia tem commits que não estão no GitHub. Atualizar "
                "automaticamente apagaria esse trabalho, então a Central "
                "parou aqui.")
    if "no upstream" in m or "no such ref" in m:
        return "Esta cópia não está ligada a nenhum branch do GitHub."
    return mensagem or "O git falhou sem dizer por quê."


# --------------------------------------------------------------------------
# Perguntas sobre uma pasta
# --------------------------------------------------------------------------
def e_repo(pasta):
    return bool(pasta) and os.path.isdir(os.path.join(pasta, ".git"))


def situacao(pasta):
    """Retrato da pasta local. Nunca levanta: o erro vem dentro do dicionário.

    instalado  .. a pasta é um clone
    atrasado   .. quantos commits o GitHub tem a mais
    adiantado  .. quantos commits só existem aqui
    novidades  .. mensagens dos commits que faltam, do mais novo ao mais velho
    sujo       .. há arquivo modificado ou novo fora do .gitignore
    versao     .. rótulo curto (tag ou hash) do que está instalado
    erro       .. texto do problema, quando houver
    """
    retrato = {"instalado": False, "atrasado": 0, "adiantado": 0,
               "novidades": [], "sujo": False, "versao": "", "erro": ""}
    if not e_repo(pasta):
        return retrato
    retrato["instalado"] = True
    try:
        retrato["versao"] = rodar(["describe", "--tags", "--always"],
                                  pasta, tempo=20)
        retrato["sujo"] = bool(rodar(["status", "--porcelain"], pasta,
                                     tempo=30))
        # --left-right conta os dois lados de uma vez: atrás <TAB> à frente
        contagem = rodar(["rev-list", "--left-right", "--count",
                          "@{u}...HEAD"], pasta, tempo=30)
        atras, frente = (contagem.split() + ["0", "0"])[:2]
        retrato["atrasado"] = int(atras)
        retrato["adiantado"] = int(frente)
        if retrato["atrasado"]:
            log = rodar(["log", "--no-merges", "--format=%s", "-n",
                         str(MAX_COMMITS_MOSTRADOS), "HEAD..@{u}"],
                        pasta, tempo=30)
            retrato["novidades"] = [x for x in log.splitlines() if x.strip()]
    except ErroGit as e:
        retrato["erro"] = str(e)
    return retrato


# --------------------------------------------------------------------------
# Ações
# --------------------------------------------------------------------------
def clonar(url, destino):
    """Instala do zero. A pasta destino não pode existir com coisa dentro."""
    pai = os.path.dirname(os.path.abspath(destino))
    os.makedirs(pai, exist_ok=True)
    if os.path.isdir(destino) and os.listdir(destino):
        raise ErroGit("A pasta de destino já existe e não está vazia:\n%s"
                      % destino)
    rodar(["clone", url, destino], pai)


def buscar(pasta):
    """Pergunta ao GitHub o que há de novo. Não mexe em arquivo nenhum."""
    rodar(["fetch", "--quiet", "--prune"], pasta, tempo=90)


def atualizar(pasta, guardar_mudancas=False):
    """Traz o que há de novo.

    --ff-only é a trava de segurança: se a cópia local tiver commits próprios,
    o git recusa em vez de inventar um merge que ninguém pediu.
    """
    if guardar_mudancas:
        rodar(["stash", "push", "--include-untracked", "-m",
               "guardado pela Central antes de atualizar"], pasta)
    rodar(["pull", "--ff-only", "--quiet"], pasta, tempo=120)


def conferir_origem(pasta, url):
    """Confere se um clone que já existia é mesmo o repositório do catálogo.

    Serve para a pasta que a pessoa já usava antes da Central existir: em vez
    de baixar tudo de novo, a Central passa a cuidar da que já está lá.
    """
    if not e_repo(pasta):
        raise ErroGit("Esta pasta não é um clone do git:\n%s" % pasta)
    atual = ""
    try:
        atual = rodar(["remote", "get-url", "origin"], pasta, tempo=20)
    except ErroGit:
        pass
    if not _mesmo_repo(atual, url):
        raise ErroGit("Esta pasta é um clone de outro repositório:\n\n%s\n\n"
                      "O catálogo espera:\n\n%s"
                      % (atual or "(sem origin)", url))


def _mesmo_repo(a, b):
    """Compara endereços ignorando o .git do fim, a barra e maiúsculas."""
    def limpa(u):
        u = (u or "").strip().rstrip("/").lower()
        return u[:-4] if u.endswith(".git") else u
    a, b = limpa(a), limpa(b)
    return a != "" and a == b
