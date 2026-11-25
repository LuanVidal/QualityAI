"""Gera os infográficos em português e o pôster vetorial 90 x 120 cm."""
from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import pymupdf
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'apresentacao'
OUT.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialNegrito', r'C:\Windows\Fonts\arialbd.ttf'))
NAVY, BLUE, TEAL = '#0B1D31', '#075EAB', '#008D80'
INK, MUTED, PALE = '#132D43', '#415B6E', '#EDF6FA'

def rect(c, x, y, w, h, color, radius=0):
    c.setFillColor(HexColor(color))
    c.setStrokeColor(HexColor(color))
    c.roundRect(x, y, w, h, radius, stroke=0, fill=1)

def text(c, value, x, y, size=20, color=INK, bold=False):
    c.setFillColor(HexColor(color))
    c.setFont('ArialNegrito' if bold else 'Arial', size)
    c.drawString(x, y, value)

def paragraph(c, value, x, top, width, size=44, color=INK, align=4):
    style = ParagraphStyle('p', fontName='Arial', fontSize=size, leading=size*1.22,
                           textColor=HexColor(color), alignment=align)
    p = Paragraph(value, style)
    _, height = p.wrap(width, 5000)
    p.drawOn(c, x, top-height)
    return top-height

def section(c, title, value, x, top, width):
    rect(c, x, top-11, 12, 51, TEAL, 4)
    text(c, title.upper(), x+28, top, 49, BLUE, True)
    return paragraph(c, value, x, top-37, width)-55

def render(path, width=1500):
    with pymupdf.open(path) as doc:
        page = doc[0]
        page.get_pixmap(matrix=pymupdf.Matrix(width/page.rect.width, width/page.rect.width),
                        alpha=False).save(str(path.with_suffix('.png')))

def box(c, x, y, w, title, lines):
    height=64+len(lines)*25
    rect(c, x, y-height, w, height, PALE, 10)
    rect(c, x, y-42, w, 42, BLUE, 8)
    text(c, title, x+16, y-28, 17, '#FFFFFF', True)
    for i, line in enumerate(lines):
        text(c, line, x+16, y-67-i*25, 14)
    return height

def relation(c, x1, y1, x2, y2, label):
    c.setStrokeColor(HexColor(TEAL)); c.setLineWidth(2)
    c.line(x1,y1,x2,y2)
    text(c,label,(x1+x2)/2+8,(y1+y2)/2+8,13,TEAL,True)

def diagrams():
    path=OUT/'entidade-relacionamento.pdf'
    c=canvas.Canvas(str(path),pagesize=(1400,1000))
    text(c,'QualityAI | Modelo entidade-relacionamento',55,942,32,BLUE,True)
    text(c,'Visão lógica simplificada do banco SQLite implementado',55,908,18,MUTED)
    relation(c,710,690,250,620,'1 : N'); relation(c,710,690,710,620,'1 : N')
    relation(c,710,690,1160,620,'1 : N'); relation(c,250,425,250,335,'1 : N')
    relation(c,430,520,525,520,'1 : N'); relation(c,895,520,975,520,'1 : N')
    relation(c,1160,425,1160,335,'1 : N'); relation(c,975,230,895,230,'1 : N')
    relation(c,430,230,525,230,'0..1 : N')
    box(c,525,850,370,'RECEITA',['Identificador (chave primária)','Nome e tipo da peça','Descrição do modelo','Região de interesse e filtros'])
    box(c,65,620,365,'VERSÃO DO CONJUNTO',['Identificador e receita (referência)','Número da versão','Situação: ativa ou arquivada','Data de criação e fechamento'])
    box(c,525,620,370,'TREINAMENTO',['Identificador e receita (referência)','Versão do conjunto (referência)','Quantidade de imagens e divisões','Métricas e data de conclusão'])
    box(c,975,620,365,'MODELO',['Identificador e receita (referência)','Treinamento e conjunto (referências)','Caminho do arquivo e limite','Versão ativa e métricas'])
    box(c,65,335,365,'IMAGEM',['Identificador e conjunto (referência)','Classe: conforme ou não conforme','Arquivo, origem e resumo digital','Captura e exclusão registrada'])
    box(c,525,335,370,'REVISÃO HUMANA',['Identificador e inspeção (referência)','Classe confirmada pelo inspetor','Correção e imagem adicionada','Data da revisão'])
    box(c,975,335,365,'INSPEÇÃO',['Identificador, receita e modelo','Arquivo da peça inspecionada','Classe prevista e confiança','Necessidade de revisão e data'])
    text(c,'AUDITORIA: registra ações de todas as receitas. CONFIGURAÇÕES: guarda a receita ativa.',65,66,17,MUTED)
    text(c,'As imagens e os pesos permanecem em arquivos; o banco guarda referências e histórico.',65,37,17,MUTED)
    c.save(); render(path)

    path=OUT/'analise-de-requisitos.pdf'
    c=canvas.Canvas(str(path),pagesize=(1400,1000))
    text(c,'QualityAI | Análise de requisitos',55,940,34,BLUE,True)
    text(c,'Pessoa usuária: inspetor de qualidade | Objetivo: apoiar a classificação visual de peças',55,900,20,MUTED)
    groups=[('01  ORGANIZAR', ['Criar e trocar receitas de peças','Descrever a aplicação de inspeção','Isolar imagens, ajustes e modelos']),
            ('02  PREPARAR', ['Selecionar câmera USB e capturar','Delimitar a região de interesse','Ajustar filtros e revisar as classes']),
            ('03  APRENDER', ['Exigir ao menos 10 imagens por classe','Extrair características com rede fixa','Validar e salvar o classificador leve']),
            ('04  INSPECIONAR', ['Classificar peça conforme ou não','Exibir confiança e versão do modelo','Revisar erros e adicionar exemplos'])]
    for i,(title,lines) in enumerate(groups):
        x=60+(i%2)*670; y=820-(i//2)*265
        box(c,x,y,610,title,lines)
    box(c,60,265,610,'REQUISITOS DE QUALIDADE',['Execução local em notebook, sem servidor','Interface responsiva durante treinamento','Dados persistentes e histórico auditável','Mesmo processamento ao treinar e inspecionar'])
    box(c,730,265,610,'CRITÉRIOS DE ACEITAÇÃO',['Trocar receita sem misturar os conjuntos','Impedir treinamento sem amostras mínimas','Solicitar revisão abaixo de 70% de confiança','Preservar banco e modelos após reiniciar'])
    c.save(); render(path)

def banner():
    cm=72/2.54; W,H=90*cm,120*cm
    path=OUT/'banner-qualityai-90x120.pdf'
    c=canvas.Canvas(str(path),pagesize=(W,H), pageCompression=1)
    c.setTitle('QualityAI - EXPOUNA - UNA Barreiro')
    margin=3*cm; gap=2*cm; col=(W-2*margin-gap)/2
    rect(c,0,H-740,W,740,NAVY)
    rect(c,0,H-180,W,180,'#FFFFFF')
    c.drawImage(str(ROOT/'docs/apresentacao/recursos/logo-una.png'),margin,H-160,
                width=420,height=140,preserveAspectRatio=True,anchor='c',mask='auto')
    rect(c,0,H-754,W,14,TEAL)
    text(c,'EXPOUNA 2026',W-margin-800,H-85,49,'#E52635',True)
    text(c,'UNA BARREIRO · BELO HORIZONTE',W-margin-800,H-140,32,INK)
    logo=ROOT/'qualityai/assets/qualityai-logo.png'
    rect(c,W-margin-400,H-470,400,265,'#FFFFFF',20)
    c.drawImage(ImageReader(str(logo)),W-margin-385,H-455,width=370,height=235,
                preserveAspectRatio=True,anchor='c',mask='auto')
    text(c,'QUALITYAI',margin,H-305,94,'#FFFFFF',True)
    text(c,'INSPEÇÃO VISUAL INDUSTRIAL',margin,H-390,66,'#FFFFFF',True)
    text(c,'COM INTELIGÊNCIA ARTIFICIAL LEVE',margin,H-470,66,'#FFFFFF',True)
    paragraph(c,'Uma câmera USB. Um notebook. Exemplos reais da peça.<br/>Aprendizado compacto para apoiar decisões de qualidade.',margin,H-515,W-2*margin,42,'#C6E8EF',0)
    text(c,'Luan Gabriel Vidal da Silva · Marcio Alves · Thiago Mendes',margin,H-665,40,'#FFFFFF')
    text(c,'Centro Universitário UNA · Unidade Barreiro',margin,H-715,32,'#C6E8EF')
    x=margin; y=H-860
    y=section(c,'Introdução e objetivo',
        'Inspeções manuais podem variar com a experiência do operador e as condições da bancada. '
        'O QualityAI foi desenvolvido para apoiar a classificação de peças conformes e não conformes '
        'com baixo custo computacional. O objetivo é permitir que um inspetor configure, treine e '
        'utilize a aplicação no próprio notebook, com supervisão humana.',x,y,col)
    y=section(c,'Metodologia',
        'A câmera USB fornece a imagem. O inspetor delimita a região de interesse, ajusta filtros e '
        'organiza exemplos em receitas específicas para cada peça. A rede MobileNetV3-Small, '
        'pré-treinada e congelada, transforma cada imagem em 576 características. Somente um '
        'classificador linear aprende a distinguir as duas classes.',x,y,col)
    for i,(a,b) in enumerate([('CAPTURAR','Câmera USB e região de interesse'),('PREPARAR','Revisão de classes e filtros'),('TREINAR','Rede fixa + classificador pequeno'),('INSPECIONAR','Resultado, confiança e revisão')]):
        rect(c,x,y-110,col,110,PALE,12)
        text(c,f'{i+1:02d}',x+25,y-65,42,TEAL,True)
        text(c,a,x+110,y-43,32,BLUE,True)
        text(c,b,x+110,y-85,28,MUTED)
        y-=130
    y-=30
    y=section(c,'Por que o treinamento é leve?',
        'Os pesos da rede visual não são atualizados. O ajuste ocorre apenas em um classificador '
        'com 577 parâmetros. As características já calculadas são reutilizadas em novos treinamentos. '
        'A aplicação opera em CPU, sem exigir placa de vídeo dedicada ou servidor.',x,y,col)
    y=section(c,'Validação e limites',
        'A avaliação externa usa cinco divisões estratificadas. A regularização é selecionada em '
        'divisões internas, sem consultar os exemplos de avaliação. Vinte imagens demonstram o fluxo, '
        'mas não comprovam desempenho industrial. Confiança abaixo de 70% encaminha a decisão ao inspetor.',x,y,col)
    right=margin+col+gap; ry=H-860
    ry=section(c,'Resultados do protótipo',
        'O sistema reúne captura manual, região de interesse, filtros, receitas independentes, '
        'treinamento e inspeção. O SQLite relaciona imagens, modelos, resultados e revisões humanas. '
        'Correções do inspetor tornam-se novos exemplos para treinamentos posteriores.',right,ry,col)
    for value,label in [('576','características visuais por imagem'),('577','parâmetros no classificador final'),('CPU','processamento local no notebook')]:
        rect(c,right,ry-150,col,150,PALE,12)
        text(c,value,right+26,ry-66,56,TEAL,True)
        text(c,label,right+26,ry-118,32,INK)
        ry-=174
    screenshot=ROOT/'docs/apresentacao/recursos/interface-inspecao.png'
    if screenshot.exists():
        from PIL import Image
        im=Image.open(screenshot); sh=col*im.height/im.width
        c.drawImage(str(screenshot),right,ry-sh,width=col,height=sh)
        ry-=sh+18
        ry=paragraph(c,'Figura 1 - Interface demonstrativa de inspeção. Fonte: elaboração própria.',right,ry,col,26,MUTED,0)-70
    ry=section(c,'Conclusão',
        'A transferência de aprendizado permite adaptar a inspeção a diferentes peças com menor '
        'esforço computacional, preservando a rastreabilidade e a decisão humana. A próxima etapa '
        'é validar lotes independentes e condições reais de iluminação e posicionamento.',right,ry,col)
    text(c,'REFERÊNCIAS',right,ry,49,BLUE,True)
    ry=paragraph(c,
        'HOWARD, A. et al. Searching for MobileNetV3. In: ICCV, 2019.<br/><br/>'
        'PEDREGOSA, F. et al. Scikit-learn: machine learning in Python. Journal of Machine Learning Research, v. 12, 2011.<br/><br/>'
        'ABNT. NBR 15437: pôsteres técnicos e científicos - apresentação. Rio de Janeiro: ABNT, 2023.',right,ry-38,col,30)
    qr_code=qr.QrCodeWidget('https://github.com/LuanVidal/QualityAI')
    bounds=qr_code.getBounds(); qr_size=170
    drawing=Drawing(qr_size,qr_size,transform=[qr_size/(bounds[2]-bounds[0]),0,0,qr_size/(bounds[3]-bounds[1]),0,0])
    drawing.add(qr_code)
    renderPDF.draw(drawing,c,margin,85)
    text(c,'CONHEÇA O PROJETO',margin+200,205,32,BLUE,True)
    text(c,'Código, documentação e diagramas',margin+200,157,30,MUTED)
    text(c,'github.com/LuanVidal/QualityAI',margin+200,111,28,MUTED)
    if min(y,ry)<115: raise RuntimeError(f'Conteúdo invadiu rodapé: {y}, {ry}')
    c.save(); render(path,1600)

if __name__=='__main__':
    diagrams(); banner()
    print(OUT)
