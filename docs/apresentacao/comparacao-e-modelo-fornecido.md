# Banner baseado no modelo UNA fornecido pelo autor

Arquivo de referência: `Modelo_Banner_ExpoUNA_2026_65_Anos_90x120cm.pptx`, fornecido em 25/11/2026. O PDF usa a primeira página do modelo. A segunda página contém orientações e não faz parte do banner impresso.

Foram preservados o cabeçalho vermelho, a imagem original da marca UNA 65 anos, as seções e a tipografia Arial. As caixas de resultados e conclusão foram redimensionadas para acomodar o gráfico e uma captura de teste. O rodapé foi omitido conforme solicitação anterior. O arquivo PPTX original permanece intacto. A entrega desta revisão é o PDF.

## Comparação empírica de latência

Não existe um tempo único que represente toda a IA do mercado. A referência adotada é uma ResNet18 pré-treinada e congelada, associada a um classificador linear ajustado às mesmas 20 imagens locais. O QualityAI usa seu modelo MobileNetV3-Small com regressão logística. A comparação mede tempo de inspeção de uma imagem, não tempo de treinamento.

| Solução | Mediana | Percentil 95 |
| --- | ---: | ---: |
| Referência convencional com ResNet18 | 64,93 ms | 112,76 ms |
| QualityAI com MobileNetV3-Small | 26,06 ms | 57,91 ms |

A razão das medianas foi de 2,49. A redução de tempo foi de aproximadamente 59,9% nesse ensaio. Isso não comprova melhoria de precisão e não deve ser generalizado a todas as soluções comerciais.

Protocolo: notebook Intel Core i5-1135G7, CPU, quatro fluxos do PyTorch, entrada de 224 × 224 pixels, 20 imagens distintas, 10 aquecimentos e 200 medições por modelo. A ordem das soluções alternou entre cinco rodadas. Inclui região de interesse, filtros, transformação, extração de atributos, normalização e classificação. Exclui câmera, disco e carregamento dos modelos. O programa de comparação é `tools/comparar_inferencia.py`. Os resultados e as 400 medições individuais estão em `comparacao-inferencia.json`.

A captura do sistema é demonstrativa. Seus valores de confiança não constituem resultado de validação de precisão. Seu uso é ilustrar a interface e a região de interesse.

## Impressão

O PDF tem uma página, 90 cm de largura por 120 cm de altura, fontes incorporadas e gráfico vetorial. Imprimir em tamanho real, sem ajustar ao papel. O QR code foi decodificado após a renderização do PDF e aponta para o repositório QualityAI. A fonte dos tempos, unidades, referência de comparação e condições do experimento aparecem na própria arte.

Arquivo: [banner em PDF](../../output/apresentacao/banner-qualityai-modelo-UNA-90x120.pdf).
