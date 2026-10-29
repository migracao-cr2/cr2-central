# Central de Automações CR2

Uma janela só, com todas as automações da CR2 dentro. Instala, abre e
atualiza cada uma direto do GitHub — sem baixar `.rar`, sem copiar pasta.

**Abrir:** dois cliques em `central.bat`.

A janela é em Qt (`src/app_qt.py`, precisa do PySide6). Se o PySide6 não estiver
instalado no computador, o `central.bat` abre a mesma Central em Tkinter
(`src/app.py`): ela nunca deixa de abrir por falta de biblioteca. O PySide6
chega sozinho na primeira vez que a pessoa abre um programa do catálogo que
usa Qt, porque o `.bat` dele instala as dependências.

O `GERAR-EXE.bat` gera um `dist\Central CR2.exe`, que fica **fora do git** e
**não é usado pelo `central.bat`**: o `.exe` é uma cópia congelada, e o
"Atualizar a Central" atualiza o código do git, não o `.exe`.

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

O botão **Verificar tudo** pergunta ao GitHub por todas **ao mesmo tempo** (até
12 de uma vez): com 12 automações instaladas, caiu de ~30 s para ~5 s.

O botão **Tudo ▾** faz de uma vez o que os cartões fazem um por um:

| Opção | O que faz |
|---|---|
| **Atualizar tudo** | atualiza todas as que têm versão nova |
| **Instalar tudo** | instala todas as que ainda não estão neste computador |
| **Instalar e atualizar tudo** | as duas coisas |

O número entre parênteses é quantas há em cada caso, pelo último *Verificar*.
Automação com **arquivo alterado** dentro da pasta não é atualizada em massa: a
Central lista quais são, e o botão **Atualizar** do cartão de cada uma pergunta
se pode guardar os arquivos antes.

## Tela única: os programas abrem dentro da Central

Com a janela Qt, **Abrir** encaixa o programa dentro da Central. Cada programa
continua sendo um processo próprio (um travar não derruba os outros nem a
Central); só a janela dele aparece aqui.

- **← Menu**, no cabeçalho do próprio programa, volta aos cartões. O programa
  **continua rodando**: o cartão dele mostra o andamento (barra e porcentagem,
  lidas da barra de progresso do programa) e o botão vira **Ir para o
  programa**. *Mais ▾ → Fechar o programa* fecha.
- **Sem janela de comandos:** o `.bat` do programa roda escondido. Se ele
  falhar ao abrir, a Central mostra as últimas linhas que ele escreveu e
  oferece abrir do jeito antigo, com a janela de comandos, para ver o erro.
- **Um tema só:** os programas abrem no tema da Central e acompanham quando
  ele muda — inclusive pelo botão de tema de dentro de um programa.
- **Ao fechar a Central** com programas abertos: *Fechar tudo* (quem está
  trabalhando pergunta antes), *Deixar abertos* (cada um vira janela própria,
  do tamanho da Central, e continua) ou *Cancelar*.
- **Notebook:** em tela baixa o `tema_qt.py` entra em modo compacto (cabeçalho
  fino, campos menores); `CR2_COMPACTO=1` força, para testar.

O lado do programa disso tudo está no `tema_qt.py` (classe `Central`): o
programa não precisa fazer nada além de usar o `tq.Cabecalho`.

`CR2_RAIZ` troca a pasta de configuração e de apps (`%LOCALAPPDATA%\CR2`): serve
para rodar uma Central de teste ao lado da de verdade sem tocar em nada dela.

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

### O logo

`logo.ico` (raiz) e `src/logo.png` são o emblema azul da CR2: o `.ico` vai no
atalho e na barra de tarefas, o `.png` no cabeçalho da janela. São um
**substituto** — havendo o logo oficial, troque os dois arquivos e nada no
código muda. `gerar_logo.py` refaz os dois a partir do desenho (só ele precisa
do Pillow, e só quando você quiser regerar).

O `.ico` é multi-tamanho de propósito: abaixo de 32px o "CR2" viraria borrão,
então os tamanhos pequenos levam só a silhueta azul, que é o que se reconhece
num ícone de 16px.

### Os atalhos, na instalação

O `INSTALAR.bat` **pergunta** onde você quer o atalho: área de trabalho, menu
Iniciar, os dois ou nenhum. Enter aceita o padrão (área de trabalho). O atalho
sai com o ícone azul.

**Fixar na barra de tarefas não pode ser automatizado.** O Windows 10 e o 11 não
oferecem isso a nenhum programa — a Microsoft removeu o comando que existia no
7. Dá para forçar mexendo no registro, mas é gambiarra que quebra em atualização
do Windows. Então o instalador cria o atalho no menu Iniciar (que é de onde o
"Fixar na barra de tarefas" funciona), explica o clique com o botão direito e
oferece abrir a pasta do atalho para você já fazer isso.

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
src/app_qt.py      a janela (Qt): cartões, menus, threads de trabalho
src/app.py         a mesma janela em Tkinter, para quem não tem o PySide6
src/repos.py       tudo que fala com o git — e só isso fala
src/catalogo.py    o catálogo e a configuração desta máquina
src/tema.py        cores e modo escuro (o mesmo dos outros programas)
src/tema_qt.py     o visual Qt — a CÓPIA CANÔNICA, copiada igual para cada programa
src/escala.py      a escala da tela (o mesmo dos outros programas)
```

Três regras que explicam o resto do código:

**A janela não trava.** Git é rede, e rede demora. Todo git roda em threads
de trabalho, com uma trava por pasta. Elas devolvem o resultado por um sinal Qt
(no `app.py`, por uma fila que o Tk esvazia a cada 120 ms), e só a thread da
janela toca a tela. As threads são daemon: fechar a janela no meio de um
*Verificar tudo* encerra o programa na hora.

**A janela acompanha a escala da tela.** Notebook com Windows vem de fábrica em
125%, e um programa que não se declara ciente do DPI é esticado pelo Windows por
cima: texto borrado e janela maior do que a que ele pediu. O `src/escala.py`
declara o processo ciente do DPI antes de a janela existir, acerta o
`tk scaling` e converte os pixels escritos na mão. É o mesmo arquivo em todos os
programas do catálogo. Para conferir sem ter um notebook à mão, num monitor
em 100%:

```
set CR2_ESCALA=1.25
central.bat
```

A janela abre exatamente como abriria num notebook em 125%. Serve qualquer fator
(1.25, 1.5, 1.75) e vale para todos os programas do catálogo.

**A Central não engole o código das automações.** Cada uma continua sendo o
repositório dela, com o `.bat` dela, evoluindo sozinha. Juntar tudo num
programa só misturaria dependências (Selenium, Tesseract, Pillow) e quebraria
caminhos que hoje funcionam.

## O visual Qt de todos os programas

`src/tema_qt.py` é o visual dos programas em Qt: cores claro/escuro, folha de
estilo, cabeçalho escuro com a marca, faixa de aviso, painel, campo com
rótulo, a seta das caixas de seleção e a `Tarefa` (trabalho numa thread
daemon, com sinais seguros de volta para a janela). Ele não sabe nada de
licitação, emenda ou PDF.

**Esta é a cópia canônica.** Cada programa do catálogo leva uma cópia igual,
do mesmo jeito que já leva o `escala.py`. Mudou aqui, copie para os outros; não
edite a cópia de um programa só, senão os visuais voltam a divergir. Regra
que só um programa usa vai no `extra` de `tema_qt.estilo(modo, extra)`.

Todo programa com janela Qt mantém a janela Tk como reserva: sem o PySide6,
o `.bat` abre a Tk, e o programa nunca deixa de abrir por falta de biblioteca.

## Quando algo dá errado

| Na tela | O que é |
|---|---|
| "O GitHub recusou o acesso" | falta fazer o login do GitHub nesta máquina |
| "Esta cópia tem commits que não estão no GitHub" | há trabalho local não enviado; a Central não sobrescreve |
| "com arquivos alterados" | há arquivos mexidos na pasta; ao atualizar, a Central oferece guardá-los antes |
| "O git não está instalado" | instale o Git para Windows |

Erros inesperados ficam em `%LOCALAPPDATA%\CR2\central\erros.log`.
