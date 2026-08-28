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
LADO = 512                                     # desenha grande e reduz
# Altura que o cabeçalho da janela usa (tema.ALTURA_LOGO).
ALTURA_CABECALHO = 44


def desenhar(lado=LADO, texto="CR2", com_texto=True):
    """O emblema, num quadrado de `lado` pixels, com fundo transparente."""
    img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Quadrado arredondado. O raio proporcional mantém a mesma silhueta em
    # qualquer tamanho.
    margem = int(lado * 0.045)
    raio = int(lado * 0.20)
    d.rounded_rectangle([margem, margem, lado - margem, lado - margem],
                        radius=raio, fill=AZUL)

    # Um brilho sutil no topo, para o emblema não ficar um bloco morto.
    brilho = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    ImageDraw.Draw(brilho).rounded_rectangle(
        [margem, margem, lado - margem, int(lado * 0.52)],
        radius=raio, fill=AZUL_CLARO + (70,))
    img = Image.alpha_composite(img, brilho)

    if not com_texto:
        return img

    d = ImageDraw.Draw(img)
    # Acha o maior corpo de fonte que caiba na largura útil.
    util = lado - 2 * margem - int(lado * 0.16)
    corpo = int(lado * 0.42)
    fonte = None
    while corpo > 8:
        try:
            fonte = ImageFont.truetype(FONTE, corpo)
        except OSError:
            fonte = ImageFont.load_default()
            break
        caixa = d.textbbox((0, 0), texto, font=fonte)
        if (caixa[2] - caixa[0]) <= util:
            break
        corpo -= 2

    caixa = d.textbbox((0, 0), texto, font=fonte)
    x = (lado - (caixa[2] - caixa[0])) / 2 - caixa[0]
    y = (lado - (caixa[3] - caixa[1])) / 2 - caixa[1]
    d.text((x, y), texto, font=fonte, fill=BRANCO)
    return img


def gerar(pasta_png, pasta_ico=None):
    """Grava logo.png e logo.ico. Devolve os caminhos."""
    pasta_ico = pasta_ico or pasta_png
    grande = desenhar()

    # PNG para o cabeçalho da janela.
    #
    # O tamanho não é livre: tema.py reduz a imagem por SUBSAMPLE de fator
    # inteiro (de propósito, para não depender de Pillow em tempo de execução),
    # e subsample não suaviza. Emitindo o PNG num múltiplo exato de
    # ALTURA_LOGO, a redução cai num fator inteiro redondo e a imagem que o Tk
    # desenha vem de um LANCZOS feito aqui — não de um descarte de pixels.
    caminho_png = os.path.join(pasta_png, "logo.png")
    grande.resize((ALTURA_CABECALHO * 2,) * 2, Image.LANCZOS).save(caminho_png)

    # ICO multi-tamanho. Nos tamanhos pequenos o "CR2" vira borrão, então
    # abaixo de 32px o emblema vai SEM texto: só a silhueta azul, que é o que
    # se reconhece num ícone de 16px.
    #
    # CUIDADO: o Pillow só usa um quadro pronto quando ele vem em
    # `append_images` COM O TAMANHO EXATO da entrada. Passar `sizes` e uma
    # imagem grande faz ele reescalar a base e ignorar os quadros — foi assim
    # que a primeira versão saiu com "CR2" borrado em 16px.
    tamanhos = (256, 128, 64, 48, 32, 24, 20, 16)
    sem_texto = desenhar(com_texto=False)
    quadros = []
    for t in tamanhos:
        origem = grande if t >= 32 else sem_texto
        quadros.append(origem.resize((t, t), Image.LANCZOS))

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
