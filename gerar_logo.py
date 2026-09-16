# -*- coding: utf-8 -*-
"""
Gera o logo azul da CR2: logo.png (janela) e logo.ico (atalho do Windows).

O desenho é um quadrado de cantos arredondados na cor da marca, com "CR2" em
branco. É um SUBSTITUTO: quando houver o logo oficial, basta trocar os dois
arquivos — nada no código depende deste desenho.

NÃO É USADO EM TEMPO DE EXECUÇÃO. Este arquivo só existe para (re)gerar os dois
logos, e é a única coisa no repositório que precisa do Pillow
(`py -m pip install pillow`). Rodar:

    py gerar_logo.py <pasta_do_png> [pasta_do_ico]

Trocando pelo logo oficial da CR2, este arquivo pode ser apagado: nada depende
dele, só dos dois arquivos que ele produz.

Por que dois formatos: o Tk desenha a janela a partir de PNG, e o atalho do
Windows só aceita .ico. E o .ico tem de ser multi-tamanho, senão o Windows
escala um tamanho só e o ícone sai borrado na barra de tarefas.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# Cor da marca, a mesma de tema.py (COR_MARCA["primaria"]).
AZUL = (31, 78, 121)
AZUL_CLARO = (45, 106, 160)
BRANCO = (255, 255, 255)

FONTE = r"C:\Windows\Fonts\segoeuib.ttf"       # Segoe UI Bold
LADO = 512                                     # tamanho de referência
SUPER = 8                                      # desenha grande e reduz
# Altura que o cabeçalho da janela usa (tema.ALTURA_LOGO).
ALTURA_CABECALHO = 44
# Abaixo disto o emblema usa o desenho miúdo (ver `desenhar`).
MIUDO = 32


def desenhar(lado=LADO, texto="CR2"):
    """O emblema, num quadrado de `lado` pixels, com fundo transparente.

    Sempre desenhado NO TAMANHO FINAL (por cima de uma tela SUPER vezes maior,
    reduzida no fim): reduzir um desenho de 512px até 16px come o texto, e é
    de onde vinha o ícone vazio na barra de tarefas.

    Abaixo de MIUDO o desenho muda, porque nesses tamanhos não há pixel de
    sobra: a margem e o respiro das laterais encolhem, para o "CR2" ocupar
    quase toda a face, e o brilho do topo sai — em 16px ele não se lê como
    brilho, vira uma emenda no meio do quadrado.
    """
    miudo = lado < MIUDO
    lente = lado * SUPER
    img = Image.new("RGBA", (lente, lente), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Quadrado arredondado. Os fatores são proporcionais, então a silhueta é a
    # mesma em qualquer tamanho dentro de cada um dos dois desenhos.
    margem = int(lente * (0.0 if miudo else 0.045))
    raio = int(lente * 0.20)
    d.rounded_rectangle([margem, margem, lente - margem, lente - margem],
                        radius=raio, fill=AZUL)

    # Um brilho sutil no topo, para o emblema não ficar um bloco morto.
    if not miudo:
        brilho = Image.new("RGBA", (lente, lente), (0, 0, 0, 0))
        ImageDraw.Draw(brilho).rounded_rectangle(
            [margem, margem, lente - margem, int(lente * 0.52)],
            radius=raio, fill=AZUL_CLARO + (70,))
        img = Image.alpha_composite(img, brilho)

    d = ImageDraw.Draw(img)
    # Acha o maior corpo de fonte que caiba na área útil, em largura e altura.
    respiro = int(lente * (0.04 if miudo else 0.16))
    util = lente - 2 * margem - respiro
    corpo = int(lente * 0.62)
    passo = max(1, lente // 200)
    fonte = None
    while corpo > 8:
        try:
            fonte = ImageFont.truetype(FONTE, corpo)
        except OSError:
            fonte = ImageFont.load_default()
            break
        caixa = d.textbbox((0, 0), texto, font=fonte)
        if (caixa[2] - caixa[0]) <= util and (caixa[3] - caixa[1]) <= util:
            break
        corpo -= passo

    caixa = d.textbbox((0, 0), texto, font=fonte)
    x = (lente - (caixa[2] - caixa[0])) / 2 - caixa[0]
    y = (lente - (caixa[3] - caixa[1])) / 2 - caixa[1]
    d.text((x, y), texto, font=fonte, fill=BRANCO)
    return img.resize((lado, lado), Image.LANCZOS)


def gerar(pasta_png, pasta_ico=None):
    """Grava logo.png e logo.ico. Devolve os caminhos."""
    pasta_ico = pasta_ico or pasta_png

    # PNG para o cabeçalho da janela.
    #
    # O tamanho não é livre: tema.py reduz a imagem por SUBSAMPLE de fator
    # inteiro (de propósito, para não depender de Pillow em tempo de execução),
    # e subsample não suaviza. Emitindo o PNG num múltiplo exato de
    # ALTURA_LOGO, a redução cai num fator inteiro redondo e a imagem que o Tk
    # desenha vem de um LANCZOS feito aqui — não de um descarte de pixels.
    caminho_png = os.path.join(pasta_png, "logo.png")
    desenhar(ALTURA_CABECALHO * 2).save(caminho_png)

    # ICO multi-tamanho, cada quadro DESENHADO no seu tamanho (é `desenhar`
    # que cuida do "CR2" continuar legível em 16px).
    #
    # CUIDADO: o Pillow só usa um quadro pronto quando ele vem em
    # `append_images` COM O TAMANHO EXATO da entrada. Passar `sizes` e uma
    # imagem grande faz ele reescalar a base e ignorar os quadros — foi assim
    # que a primeira versão saiu com "CR2" borrado em 16px.
    tamanhos = (256, 128, 64, 48, 32, 24, 20, 16)
    quadros = [desenhar(t) for t in tamanhos]

    caminho_ico = os.path.join(pasta_ico, "logo.ico")
    quadros[0].save(caminho_ico, format="ICO",
                    sizes=[(t, t) for t in tamanhos],
                    append_images=quadros[1:])
    return caminho_png, caminho_ico


if __name__ == "__main__":
    destino_png = sys.argv[1]
    destino_ico = sys.argv[2] if len(sys.argv) > 2 else destino_png
    png, ico = gerar(destino_png, destino_ico)
    for c in (png, ico):
        print("  %-14s %6d bytes" % (os.path.basename(c), os.path.getsize(c)))
    # amostra visual: os quadros lidos DE DENTRO do .ico, ampliados sem
    # suavizar, para dar para ver o que o Windows vai desenhar.
    lido = Image.open(ico)
    mostrar = (256, 48, 32, 24, 16)
    tira = Image.new("RGBA", (len(mostrar) * 106, 116), (245, 246, 249, 255))
    x = 0
    for t in mostrar:
        q = lido.ico.getimage((t, t)).convert("RGBA")
        tira.paste(q.resize((96, 96), Image.NEAREST), (x + 5, 10))
        x += 106
    tira.save(os.path.join(destino_png, "_amostra.png"))
    print("  quadros no ico:", sorted(lido.ico.sizes()))
    print("  amostra:", os.path.join(destino_png, "_amostra.png"))
