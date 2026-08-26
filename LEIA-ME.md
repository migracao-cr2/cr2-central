# Central de Automações CR2

Uma janela só, com todas as automações da CR2 dentro. Instala, abre e
atualiza cada uma direto do GitHub — sem baixar `.rar`, sem copiar pasta.

**Abrir:** dois cliques em `central.bat`.

---

## O que ela faz

Cada automação vira um cartão com três botões:

| Botão | O que faz |
|---|---|
| **Instalar** | baixa a automação do GitHub para esta máquina |
| **Abrir** | abre o programa, do mesmo jeito que o `.bat` dele já abria |
| **Atualizar** | traz a versão nova quando existe uma |

O cartão avisa sozinho quando há novidade: *"3 novidades no GitHub"*. Em
**Mais ▾ → Ver o que mudou** aparece a lista do que mudou, escrita nos
próprios commits.

O botão **Verificar tudo** pergunta ao GitHub de uma vez por todas.

## A Central se atualiza sozinha

Quando a própria Central tem versão nova, aparece uma faixa no topo com o
botão **Atualizar a Central**. Isso importa porque é junto com ela que chega
o `catalogo.json`: **automação nova entra na tela de todo mundo sem ninguém
reinstalar nada.**

## Onde as coisas ficam

```
%LOCALAPPDATA%\CR2\apps\<automação>   as automações instaladas
%LOCALAPPDATA%\CR2\central\config.json  o tema e os caminhos DESTA máquina
```

Já tem a automação numa pasta sua, com seus dados dentro? Não precisa baixar
de novo: **Mais ▾ → Escolher outra pasta...** e a Central passa a cuidar da
que já está lá. Ela confere se a pasta é mesmo daquele repositório antes de
aceitar.

## Numa máquina nova

1. Instale o [Python](https://www.python.org/downloads/) marcando
   **"Add python.exe to PATH"** e **"tcl/tk and IDLE"**.
2. Instale o [Git para Windows](https://git-scm.com/download/win).
3. Baixe a Central e dê dois cliques em `central.bat`.

Na primeira instalação de uma automação, o Windows abre uma janela pedindo o
login do GitHub (os repositórios são privados). É uma vez só: o Credential
Manager guarda daí em diante. **Nenhuma senha fica escrita em arquivo.**

## Acrescentar uma automação ao catálogo

Uma entrada em `catalogo.json` e um push. Só isso.

```json
{
  "id": "nome-do-repositorio",
  "nome": "Nome que aparece na tela",
  "descricao": "Uma linha explicando para que serve.",
  "repo": "https://github.com/migracao-cr2/nome-do-repositorio.git",
  "entrada": "programa.bat",
  "tipo": "janela"
}
```

- `entrada` — o arquivo que abre o programa. Quando é um `.bat`, é ele quem
  manda: a Central não repete a lógica de achar o Python nem de instalar
  dependências, só aperta o mesmo botão que a pessoa apertaria.
- `tipo` — `janela` para programa com interface, `terminal` para ferramenta
  de linha de comando (a Central abre um console e o deixa aberto).
- `subpasta` *(opcional)* — quando várias ferramentas dividem um repositório,
  a pasta de cada uma dentro dele.

## Como está organizado

```
central.bat        abre a janela
catalogo.json      QUAIS automações existem (vem do GitHub, é versionado)
src/app.py         a janela: cartões, menus, thread de trabalho
src/repos.py       tudo que fala com o git — e só isso fala
src/catalogo.py    o catálogo e a configuração desta máquina
src/tema.py        cores e modo escuro (o mesmo dos outros programas)
```

Duas regras que explicam o resto do código:

**A janela não trava.** Git é rede, e rede demora. Todo git roda numa thread
de trabalho que devolve o resultado por uma fila; o Tk esvazia essa fila a
cada 120 ms. É o mesmo mecanismo do Gestor de Licitações.

**A Central não engole o código das automações.** Cada uma continua sendo o
repositório dela, com o `.bat` dela, evoluindo sozinha. Juntar tudo num
programa só misturaria dependências (Selenium, Tesseract, Pillow) e quebraria
caminhos que hoje funcionam.

## Quando algo dá errado

| Na tela | O que é |
|---|---|
| "O GitHub recusou o acesso" | falta fazer o login do GitHub nesta máquina |
| "Esta cópia tem commits que não estão no GitHub" | há trabalho local não enviado; a Central não sobrescreve |
| "com arquivos alterados" | há arquivos mexidos na pasta; ao atualizar, a Central oferece guardá-los antes |
| "O git não está instalado" | instale o Git para Windows |

Erros inesperados ficam em `%LOCALAPPDATA%\CR2\central\erros.log`.
