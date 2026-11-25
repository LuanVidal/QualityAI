"""Adapta a geometria do modelo fornecido ao PDF final, mantendo o original."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import xml.etree.ElementTree as E
import json
import math
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/apresentacao'
N={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
CM=72/2.54
W,H=90*CM,120*CM
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialNegrito',r'C:\Windows\Fonts\arialbd.ttf'))

COPY={
 'poster-title':'QUALITYAI: INSPEÇÃO VISUAL INDUSTRIAL<br/>COM INTELIGÊNCIA ARTIFICIAL LEVE',
 'authors':'Luan Gabriel Vidal da Silva · Marcio Alves · Thiago Mendes',
 'affiliation':'Centro Universitário UNA · Unidade Barreiro · Belo Horizonte',
 'intro-body':'A inspeção visual de peças pode variar com a experiência do operador e as condições de iluminação. O QualityAI apoia essa atividade com uma aplicação local que aprende a partir de exemplos de peças conformes e não conformes. A proposta surgiu da necessidade de adaptar a inspeção a diferentes produtos sem depender de servidores, placa de vídeo dedicada ou programação pelo inspetor. Cada receita mantém suas imagens, região de interesse, filtros e modelo separados. A classificação automatizada fornece uma indicação de qualidade, enquanto a revisão humana mantém a responsabilidade pela decisão.',
 'objectives-body':'Desenvolver uma ferramenta de inspeção visual que funcione no notebook do inspetor.<br/><br/>Reduzir o esforço computacional para adaptar o modelo a novas peças, mantendo rastreabilidade e revisão humana.',
 'method-body':'<b>Coleta e preparação</b><br/>A câmera USB captura a peça. O inspetor delimita a região de interesse e ajusta os filtros. A demonstração começa com 10 imagens conformes e 10 não conformes.<br/><br/><b>Aprendizado leve</b><br/>A MobileNetV3-Small pré-treinada permanece congelada. Ela extrai 576 características por imagem. Somente uma regressão logística aprende a separar as classes, ajustando 577 parâmetros. Características já calculadas são reutilizadas em novos treinamentos.<br/><br/><b>Avaliação e operação</b><br/>Cinco divisões estratificadas avaliam o classificador. A regularização é selecionada em divisões internas. Na inspeção, o sistema repete a região e os filtros salvos com o modelo. Resultados abaixo de 70% de confiança exigem revisão humana.<br/><br/><b>Persistência local</b><br/>O SQLite relaciona receitas, imagens, treinamentos, modelos e inspeções. Correções do inspetor alimentam os próximos treinamentos.',
 'conclusion-body':'O protótipo permite configurar receitas e inspecionar peças com processamento local. A comparação mede a latência de duas arquiteturas na mesma bancada e não representa uma média do mercado. Menor tempo de análise não comprova maior precisão. O conjunto inicial de 20 imagens demonstra o fluxo, mas a aplicação ainda precisa de validação com lotes independentes, diferentes defeitos e condições reais de captura. A liberação de peças permanece sob responsabilidade humana.',
 'references-body':'HOWARD, A. et al. Searching for MobileNetV3. In: ICCV, 2019.<br/><br/>HE, K. et al. Deep Residual Learning for Image Recognition. In: CVPR, 2016.<br/><br/>PEDREGOSA, F. et al. Scikit-learn: machine learning in Python. Journal of Machine Learning Research, v. 12, 2011.<br/><br/>Fonte dos tempos: experimento local dos autores em 25 nov. 2026. Protocolo e medições disponíveis no repositório pelo QR code.',
 'qr-title':'CÓDIGO E DOCUMENTAÇÃO',
}

def name(sp):
    node=sp.find('.//p:cNvPr',N)
    return node.get('name','') if node is not None else ''

def geom(sp,cx,cy):
    xfrm=sp.find('p:spPr/a:xfrm',N)
    if xfrm is None:return None
    off=xfrm.find('a:off',N); ext=xfrm.find('a:ext',N)
    return (int(off.get('x'))*W/cx,int(off.get('y'))*H/cy,
            int(ext.get('cx'))*W/cx,int(ext.get('cy'))*H/cy)

def para(c,html,x,top,width,size=25.5,color='#262626',bold=False,align=0,maxheight=None):
    style=ParagraphStyle('texto',fontName='ArialNegrito' if bold else 'Arial',
                         fontSize=size,leading=size*1.24,textColor=HexColor(color),alignment=align)
    p=Paragraph(html,style);_,height=p.wrap(width,10000)
    if maxheight is not None and height>maxheight:
        raise ValueError(f'Texto não cabe ({height:.1f}>{maxheight:.1f}): {html[:50]}')
    p.drawOn(c,x,top-height)
    return top-height

def chart(c,g,data):
    x,y,w,h=g; top=H-y
    top=para(c,'Tempo de análise por imagem',x,top,w,33,bold=True)-20
    top=para(c,'Comparação medida na CPU do mesmo notebook',x,top,w,23,color='#555555')-48
    values=[data['tempos_ms']['resnet18']['mediana'],data['tempos_ms']['qualityai']['mediana']]
    maxvalue=math.ceil(max(values)/5)*5
    axisx=x+36; axisw=w-150; base=top-415
    for i in range(5):
        tx=axisx+axisw*i/4
        c.setStrokeColor(HexColor('#DDDDDD'));c.setLineWidth(1)
        c.line(tx,base,tx,top+5)
        para(c,f'{maxvalue*i/4:.1f}'.replace('.',','),tx-24,base-15,100,22)
    for i,(label,value,color) in enumerate(zip(['Referência convencional: ResNet18','QualityAI: MobileNetV3-Small'],values,['#777777','#EC0016'])):
        by=top-100-i*210
        para(c,label,axisx,by+83,axisw,26,bold=True)
        c.setFillColor(HexColor(color));c.rect(axisx,by,axisw*value/maxvalue,48,stroke=0,fill=1)
        para(c,f'{value:.2f} ms'.replace('.',','),axisx+axisw*value/maxvalue+14,by+43,150,27,bold=True)
    end=para(c,'Tempo em milissegundos (menor é melhor)',axisx,base-60,axisw,24)-35
    ratio=data['razao_mediana']
    ratio_text=f'{ratio:.2f}'.replace('.',',')
    end=para(c,f'<b>Análise {ratio_text} vezes mais rápida</b><br/>na comparação local das medianas.',x,end,w,30,color='#EC0016')-42
    end=para(c,'<b>Condições de medição</b><br/>Intel Core i5-1135G7, CPU com 4 fluxos de execução. 20 imagens, 200 medições por modelo após 10 aquecimentos. Entrada de 224 × 224 pixels. Ambos usam extrator pré-treinado congelado e classificador linear. O tempo inclui preparação, extração e classificação, com a imagem em memória. Exclui câmera, disco e carregamento dos modelos.',x,end,w,24)-30
    end=para(c,'Figura 1 - Mediana da latência por imagem. Fonte: elaboração própria, 25 nov. 2026. A referência ResNet18 não representa um tempo padrão do mercado. A comparação não avalia precisão.',x,end,w,21,color='#555555')-28
    screenshot=ROOT/'docs/apresentacao/recursos/interface-inspecao.png'
    from PIL import Image
    with Image.open(screenshot) as im:
        imagew=700
        imageh=imagew*im.height/im.width
    c.drawImage(str(screenshot),x+(w-imagew)/2,end-imageh,width=imagew,height=imageh)
    para(c,'Figura 2 - Tela de teste da inspeção, com região de interesse e valores demonstrativos. Fonte: elaboração própria. A confiança exibida na captura não é uma medida da precisão do sistema.',x,end-imageh-14,w,21,color='#555555')

def render(path):
    with pymupdf.open(path) as d:
        d[0].get_pixmap(matrix=pymupdf.Matrix(1600/W,1600/W),alpha=False).save(str(path.with_suffix('.png')))

def main(source):
    OUT.mkdir(parents=True,exist_ok=True)
    with ZipFile(source) as z:
        pres=E.fromstring(z.read('ppt/presentation.xml')); size=pres.find('p:sldSz',N)
        cx,cy=int(size.get('cx')),int(size.get('cy'))
        slide=E.fromstring(z.read('ppt/slides/slide1.xml'))
        shapes=list(slide.find('p:cSld/p:spTree',N))
        rels=E.fromstring(z.read('ppt/slides/_rels/slide1.xml.rels'))
        targets={r.get('Id'):r.get('Target').lstrip('/') for r in rels}
        for original in [False]:
            path=(ROOT/'_tmp/modelo-original.pdf') if original else OUT/'banner-qualityai-modelo-UNA-90x120.pdf'
            c=canvas.Canvas(str(path),pagesize=(W,H),pageCompression=1)
            c.setTitle('QualityAI - EXPOUNA 2026.2 - UNA Barreiro')
            c.setAuthor('Luan Gabriel Vidal da Silva; Marcio Alves; Thiago Mendes')
            c.setFillColor(HexColor('#FFFFFF'));c.rect(0,0,W,H,stroke=0,fill=1)
            for sp in shapes:
                g=geom(sp,cx,cy)
                if g is None:continue
                key=name(sp);x,y,w,h=g
                if not original and key.startswith('footer-'):continue
                if not original and key=='references-box':w=13811250*W/cx
                if not original and key in ('references-title','references-body'):w=12763500*W/cx
                if not original and key=='results-box':h=59.5*CM
                if not original and key=='conclusion-box':y,h=86.5*CM,14.5*CM
                if not original and key in ('conclusion-title','conclusion-rule','conclusion-body'):
                    y+=(86.5*CM-26003250*H/cy)
                if not original and key in ('qr-box','qr-title','qr-placeholder'):
                    if key=='qr-box': x,y,w,h=16002000*W/cx,102*CM,14763750*W/cx,13.5*CM
                    elif key=='qr-title': x,y,w,h=16525875*W/cx,103*CM,13716000*W/cx,700000*H/cy
                    else:x,y,w,h=16525875*W/cx,106*CM,13716000*W/cx,3400000*H/cy
                if not original and key=='results-visual-placeholder':
                    data=json.loads((ROOT/'docs/apresentacao/comparacao-inferencia.json').read_text(encoding='utf-8'))
                    chart(c,(x,y,w,h),data);continue
                if not original and key=='qr-placeholder':
                    widget=qr.QrCodeWidget('https://github.com/LuanVidal/QualityAI')
                    b=widget.getBounds();s=220
                    drawing=Drawing(s,s,transform=[s/(b[2]-b[0]),0,0,s/(b[3]-b[1]),0,0]);drawing.add(widget)
                    renderPDF.draw(drawing,c,x+(w-s)/2,H-y-s)
                    para(c,'github.com/LuanVidal/QualityAI',x,H-y-s-12,w,22,align=1)
                    continue
                if sp.tag.endswith('pic'):
                    blip=sp.find('.//a:blip',N)
                    rid=blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    c.drawImage(ImageReader(BytesIO(z.read(targets[rid]))),x,H-y-h,w,h,mask='auto')
                    continue
                properties=sp.find('p:spPr',N)
                if properties is not None:
                    fill=properties.find('a:solidFill/a:srgbClr',N)
                    line=properties.find('a:ln',N)
                    stroke=line.find('a:solidFill/a:srgbClr',N) if line is not None else None
                    hasstroke=stroke is not None and int(line.get('w','0'))>0
                    if fill is not None or hasstroke:
                        if fill is not None:c.setFillColor(HexColor('#'+fill.get('val')))
                        if hasstroke:
                            c.setStrokeColor(HexColor('#'+stroke.get('val')));c.setLineWidth(int(line.get('w'))/12700)
                        rounded=properties.find('a:prstGeom',N)
                        c.roundRect(x,H-y-h,w,h,12 if rounded is not None and rounded.get('prst')=='roundRect' else 0,
                                    stroke=int(hasstroke),fill=int(fill is not None))
                body=sp.find('p:txBody',N)
                if body is None:continue
                value='<br/>'.join(''.join(t.text or '' for t in p.findall('.//a:t',N)) for p in body.findall('a:p',N))
                if not original:value=COPY.get(key,value)
                rpr=body.find('.//a:rPr',N)
                fs=float(rpr.get('sz','2550'))/100 if rpr is not None else 25.5
                bold=rpr is not None and rpr.get('b')=='1'
                color=rpr.find('a:solidFill/a:srgbClr',N) if rpr is not None else None
                col='#'+color.get('val') if color is not None else '#262626'
                ppr=body.find('.//a:pPr',N);align={'ctr':1,'r':2}.get(ppr.get('algn') if ppr is not None else '',0)
                if not original and key=='references-body':fs=22
                if not original and key=='poster-title':fs=50
                if not original and key=='authors':fs=28
                if not original and key.endswith('-body'):align=0
                padding=3 if key=='authors' else 7
                para(c,value,x+padding,H-y-padding,w-2*padding,fs,col,bold,align,None if original else h-2*padding)
            c.save();render(path)
    print(OUT/'banner-qualityai-modelo-UNA-90x120.pdf')

if __name__=='__main__':main(Path(sys.argv[1]))
