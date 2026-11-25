# Protótipo desktop do QualityAI

O protótipo foi projetado para funcionar integralmente em um notebook Windows com câmera USB. Nenhuma imagem é enviada para serviços externos.

## Fluxo de uso

1. Conecte a webcam ou câmera USB.
2. Abra **Dataset e câmera**, crie ou selecione a receita da peça e escolha o dispositivo.
3. Use a prévia espelhada como referência e arraste o mouse sobre o vídeo para delimitar a região de interesse (ROI).
4. Ajuste os filtros e capture pelo menos 10 imagens `OK` e 10 imagens `NOK`.
5. Abra **Treinamento leve** e gere uma versão do modelo para a receita ativa.
6. Em **Inspeção**, capture uma nova imagem ou importe um arquivo.
7. Confirme manualmente resultados com baixa confiança.
8. Corrija previsões incorretas; a imagem revisada entra no dataset da receita ativa.

## Receitas e datasets

Uma receita representa uma aplicação de inspeção específica, como uma peça, linha ou condição de processo. Ela contém nome, tipo de peça, descrição do objetivo do modelo, imagens `OK/NOK`, ROI, filtros, histórico e modelo próprios. A caixa de seleção permite trocar de receita sem misturar amostras de produtos diferentes.

O comando **Apagar todas** remove apenas as imagens da receita selecionada, preservando as demais receitas e os registros de inspeção. Como o modelo deixaria de representar o dataset, ele é desativado e movido para a pasta local de modelos arquivados. A operação exige confirmação e não pode ser desfeita para as imagens.

## Interface e identidade visual

A aplicação utiliza o logo oficial do QualityAI, a fonte geométrica Poppins e uma paleta derivada diretamente da marca: azul-marinho, azul, ciano e verde. Os recursos visuais e as fontes ficam incorporados ao programa, mantendo a mesma apresentação mesmo em notebooks sem a fonte instalada.

A imagem recebida da câmera é espelhada horizontalmente uma única vez, antes de qualquer interação. Por isso a prévia, a seleção da ROI, a captura gravada, o treinamento e a inspeção usam a mesma orientação. Imagens importadas do disco não são alteradas.

## ROI e filtros

As imagens originais são preservadas no dataset. A configuração abaixo é aplicada durante o treinamento e salva dentro do modelo, garantindo que a inspeção repita o mesmo processamento:

| Recurso | Finalidade |
| --- | --- |
| ROI ajustável | Remove fundo e áreas que não pertencem à inspeção |
| CLAHE | Compensa diferenças locais de iluminação e contraste |
| Tons de cinza | Reduz influência de cor quando ela não representa qualidade |
| Redução de ruído | Suaviza variações pequenas do sensor |
| Nitidez | Realça bordas e detalhes superficiais |
| Brilho e contraste | Permite adaptação controlada às condições da bancada |

Filtros devem ser usados com cuidado: alterações excessivas podem apagar defeitos ou criar artefatos. O ajuste escolhido deve permanecer estável durante a coleta e a operação.

O sistema também compara uma nova captura com as últimas amostras da mesma classe. Quando a similaridade ultrapassa 98,5%, ele alerta que a foto pode ser quase duplicada. As 10 imagens precisam representar variações reais de posição, iluminação e exemplar; dez quadros consecutivos praticamente idênticos não equivalem a dez evidências independentes.

## Diferencial do treinamento

O script original congelava uma ResNet18 e treinava sua última camada, mas calculava a precisão sobre as mesmas imagens usadas no ajuste. Além disso, o script de teste utilizava o Anomalib e não carregava o artefato salvo pelo treinamento supervisionado.

O novo pipeline resolve esses pontos:

- usa a MobileNetV3-Small, mais compacta que a ResNet18;
- mantém o extrator visual completamente congelado;
- converte cada imagem em uma assinatura numérica de 576 atributos;
- treina somente uma regressão logística balanceada;
- avalia o modelo com validação cruzada estratificada de até cinco divisões;
- treina a versão final com todas as imagens após calcular as métricas;
- salva pesos, normalização, classificador, ROI, filtros e métricas em um único arquivo;
- preserva versões anteriores do modelo e registra capturas, inspeções e revisões em histórico local;
- usa exatamente o mesmo carregador na interface e no teste de linha de comando.

Essa abordagem reduz consumo de memória e CPU, evita ciclos longos de épocas e produz métricas menos otimistas. Ainda assim, 20 imagens constituem apenas uma prova de conceito e não validam uso industrial autônomo.

### Benchmark no notebook do projeto

Medição realizada no Intel Core i5-1135G7, usando CPU, após o download inicial dos pesos:

| Medida | Resultado observado |
| --- | ---: |
| Imagens do conjunto antigo | 157 |
| Tempo total de treinamento | 10,4 segundos |
| Tamanho do modelo salvo | 3,67 MB |
| Inferência com o modelo já carregado | 15,8 ms por imagem |
| Acurácia balanceada em 5 folds | 98,1% |
| Matriz de confusão `[NOK, OK]` | `[[97, 2], [1, 57]]` |

Esse resultado demonstra eficiência computacional, mas não substitui validação com peças, lotes, iluminação e defeitos independentes. Um experimento separado com apenas 20 quadros sequenciais apresentou métrica interna alta e falhou em imagens posteriores; por isso o sistema alerta sobre amostras quase duplicadas e recomenda capturas variadas.

## Execução para desenvolvimento

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Os dados são gravados em `%LOCALAPPDATA%\QualityAI\projects\<receita>` e não são versionados no Git.

## Ferramentas de linha de comando

Treinamento:

```powershell
.\.venv\Scripts\python.exe tools\train.py --dataset "C:\caminho\dataset" --output "models\qualityai_model.pt"
```

Inferência:

```powershell
.\.venv\Scripts\python.exe tools\test.py --model "models\qualityai_model.pt" --image "C:\caminho\peca.jpg"
```

O dataset deve conter as subpastas `ok` e `nok`.
