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

E não é preciso esperar a faixa acender: o botão **A Central ▾**, no alto da
janela, está sempre lá.

| No menu **A Central ▾** | O que faz |
|---|---|
| *Versão instalada* | a etiqueta ou o hash do que está nesta máquina |
| **Verificar se há versão nova** | pergunta ao GitHub e responde no rodapé, mesmo quando não há nada de novo |
| **Atualizar a Central** | traz a versão nova na hora |
| **Ver o que mudou** | a lista dos commits que ainda não estão aqui |
| **Abrir a pasta da Central no Explorer** | às vezes só se quer o caminho |
| **Ver no GitHub** | abre o repositório no navegador |

Se houver arquivo mexido na pasta da Central, ela oferece guardá-lo
(`git stash`) antes de atualizar, como já faz com as automações. Depois de
atualizar, feche e abra a janela: é nesse momento que a versão nova — e o
catálogo novo — entra no lugar.

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

Primeiro pegue o instalador. Como este repositório é público, não precisa
de login nem de git para isso — vale qualquer um dos dois:

- abra [INSTALAR.bat](https://github.com/migracao-cr2/cr2-central/blob/main/INSTALAR.bat)
  no GitHub e clique em **Download raw file**;
- ou cole isto num Prompt de Comando (o `curl` já vem no Windows):

```
curl -L -o "%USERPROFILE%\Downloads\INSTALAR.bat" https://raw.githubusercontent.com/migracao-cr2/cr2-central/main/INSTALAR.bat
```

**Depois, dois cliques em `INSTALAR.bat`.** Ele confere o que falta, instala pelo
`winget` (que já vem no Windows), baixa a Central, põe o atalho *Central CR2*
na área de trabalho e abre a janela. Rodar de novo não estraga nada: quando a
Central já está instalada, ele só atualiza e abre.

Se preferir fazer à mão, são três passos:

1. Instale o [Python](https://www.python.org/downloads/) marcando
   **"Add python.exe to PATH"** e **"tcl/tk and IDLE"** — as duas vêm
   desmarcadas, e sem elas nada funciona.
2. Instale o [Git para Windows](https://git-scm.com/download/win).
3. Clone a Central e dê dois cliques em `central.bat`:

```
git clone https://github.com/migracao-cr2/cr2-central.git
```

**Este repositório é público, então o clone não pede login nenhum.** As
automações do catálogo é que são privadas: o `INSTALAR.bat` faz esse login no
fim, e ele é uma vez por máquina. Se você instalou à mão, a janela do login
aparece no primeiro clique em **Instalar**. **Nenhuma senha fica escrita em
arquivo** — quem guarda é o Credential Manager do Windows.

> **Clone, não ZIP.** Baixar o `.zip` do GitHub, ou receber a pasta por pen
> drive, entrega uma pasta que **não é um clone do git**: a Central abre e
> abre as automações, mas não consegue se atualizar nem receber automações
> novas do catálogo. Ela avisa quando é esse o caso.

Quem não trabalha na CR2 consegue clonar e abrir a Central, mas os cartões
não instalam: os repositórios das automações continuam privados e o GitHub
responde *"Repositório não encontrado"*.

### O que o INSTALAR.bat resolve que não é óbvio

- **`PrependPath=1` não é opcional.** A Central sobreviveria sem o Python no
  PATH, porque o `central.bat` procura o launcher `py` primeiro e o `py` fica
  numa pasta que está sempre no PATH. Mas os `.bat` das automações chamam
  `python` puro — inclusive o `python -m pip install` que instala as
  dependências delas. Sem PATH, a Central abriria bonita e **nenhuma
  automação rodaria**. O `winget install` silencioso não marca isso sozinho.
- **O PATH da janela aberta é o antigo.** O `cmd` lê o PATH uma vez, ao abrir.
  Depois de instalar algo, o instalador procura nos lugares de sempre; se não
  achar, pede para fechar e rodar de novo, em vez de dizer que falhou.
- **O login no lugar certo.** O `git ls-remote` do fim faz o login do GitHub
  num console de verdade. Se ele acontecesse no primeiro **Instalar**, seria
  dentro da Central, que roda o git com `CREATE_NO_WINDOW` — e um pedido de
  senha invisível pareceria uma janela travada.
- **A área de trabalho não é `%USERPROFILE%\Desktop`.** Com o OneDrive ligado
  ela é redirecionada, e o atalho iria para uma pasta que ninguém vê. O
  caminho sai do PowerShell.

## Acrescentar uma automação ao catálogo

Uma entrada em `catalogo.json` e um push. Só isso.

```json
{
  "id": "nome-do-repositorio",
  "nome": "Nome que aparece na tela",
  "descricao": "Uma linha explicando para que serve.",
  "icone": "📦",
  "repo": "https://github.com/migracao-cr2/nome-do-repositorio.git",
  "entrada": "programa.bat",
  "tipo": "janela"
}
```

O campo **`icone`** é opcional: é o emoji que a Central desenha no cartão daquela automação. Sem ele, o cartão usa uma caixa (📦). Prefira emoji simples — a Central desenha em monocromático, e desenho muito detalhado vira borrão no tamanho do cartão.

- `entrada` — o arquivo que abre o programa. Quando é um `.bat`, é ele quem
  manda: a Central não repete a lógica de achar o Python nem de instalar
  dependências, só aperta o mesmo botão que a pessoa apertaria.
- `tipo` — `janela` para programa com interface, `terminal` para ferramenta
  de linha de comando (a Central abre um console e o deixa aberto).
- `subpasta` *(opcional)* — quando várias ferramentas dividem um repositório,
  a pasta de cada uma dentro dele.

## Como está organizado

```
INSTALAR.bat       instala tudo numa maquina nova
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
