# Entrega para apresentação na EXPOUNA - UNA Barreiro

## Software e validação

A aplicação funciona como protótipo desktop local: receitas isoladas, imagens de câmera USB, região de interesse, filtros, classificação, revisão humana e persistência SQLite. A limpeza do conjunto agora é bloqueada durante o treinamento. Os identificadores de modelos recebem sufixos aleatórios para evitar colisões entre receitas treinadas no mesmo segundo.

O treinamento ganhou reutilização de características em arquivos NumPy por conteúdo da imagem e configuração do processamento. Mudanças na imagem, região ou filtros invalidam automaticamente a assinatura. Os pesos da rede ficam explicitamente congelados.

O classificador seleciona entre três intensidades de regularização (0,01; 0,1; 1) com três divisões internas. Cinco divisões externas produzem as métricas sem usar os exemplos externos na seleção. A rede não é reajustada. A probabilidade da regressão logística permanece uma estimativa do modelo, não garantia de acerto nem probabilidade calibrada de qualidade industrial.

Experimento executado em 25/11/2026 com 10 imagens por classe do conjunto local antigo:

| Medida | Valor |
| --- | ---: |
| Primeiro treinamento | 2,65 s |
| Segundo treinamento, com características reutilizadas | 1,00 s |
| Acurácia balanceada externa | 70% |
| Sensibilidade da classe conforme | 90% |
| Matriz de confusão (não conforme, conforme) | `[[5, 5], [1, 9]]` |

Não foi realizada comparação pareada com a versão anterior; portanto não se afirma melhora de precisão. O recorte não é um ensaio industrial independente. Arquivos e pesos reais ficam fora do Git.

## Infográficos

- [Análise de requisitos](../output/apresentacao/analise-de-requisitos.pdf)
- [Entidade-relacionamento simplificado](../output/apresentacao/entidade-relacionamento.pdf)

Os nomes e descrições apresentados nos infográficos estão em português. Os nomes técnicos das tabelas existentes foram preservados para manter compatibilidade. O desenho é uma simplificação lógica; o esquema SQL contém os campos e vínculos completos, inclusive auditoria e configurações.

## Banner

O banner é um PDF vetorial de 90 cm de largura por 120 cm de altura, com fontes Arial incorporadas, margens laterais de 3 cm e corpo de 44 pontos. A imagem de interface é demonstrativa, não evidência de precisão. O cabeçalho usa a marca original do QualityAI e a marca oficial comemorativa de 65 anos da UNA, disponível no site institucional em 2026. A composição inclui a identificação da Barreiro e os três integrantes cadastrados no repositório.

Referência institucional efetivamente consultada: modelo da III EXPOUNA, Una Itumbiara, 2023, disponível em:

- https://www.even3.com.br/e/3expouna-415630
- https://docs.google.com/presentation/d/14mI5AOv7qROzD3Rezd85oRFEyWNg-DwA/htmlpresent

A base anterior foi adaptada à unidade Barreiro conforme solicitação do autor. Não foi encontrado edital público atual da EXPOUNA Barreiro que certifique esta composição. A estrutura foi orientada pela apresentação acadêmica de pôsteres; não há declaração de conformidade integral com a ABNT sem revisão do texto completo da norma e dos dados autorais.

Os nomes foram recuperados do README remoto: Luan Gabriel Vidal da Silva, Marcio Alves e Thiago Mendes. Curso, orientador e e-mail não foram fornecidos; esses dados foram omitidos da arte em vez de inventados. Confirmar com a orientação se são exigidos antes da impressão. O rodapé de revisão foi removido a pedido do autor.

Arquivos: [PDF em tamanho real](../output/apresentacao/banner-qualityai-90x120.pdf) e [prévia em imagem](../output/apresentacao/banner-qualityai-90x120.png).

Recursos oficiais da UNA, consultados em 25/11/2026:

- https://www.una.br/ (fonte institucional)
- https://estaticos.animaeducacao.com.br/None/Logo_Una.png (marca comemorativa usada no banner)
- https://www.una.br/assets/img/logo-una.svg (marca principal preservada como recurso vetorial)

Os arquivos da UNA são marcas de terceiros, utilizados para identificação institucional do trabalho. Não constituem concessão de direitos sobre a marca.

Para regenerar a apresentação no Windows: instalar `requirements.txt` e `requirements-apresentacao.txt` e executar `python tools/gerar_apresentacao.py`. O gerador utiliza as fontes Arial do Windows.

O arquivo tem tamanho físico real, texto vetorial e cores RGB. A gráfica deve imprimir a 100%, sem ajustar ao papel, e confirmar acabamento, eventual sangria e perfil de cor. Não foi simulado um perfil CMYK desconhecido. O logo fornecido é uma imagem, com resolução limitada pelo original.

## Limites ainda abertos

Não foram implementados nesta entrega autenticação e perfis de acesso, aprovação de modelo por engenharia ou instalador executável independente de Python. Esses itens previstos na concepção permanecem fora do protótipo demonstrável. O fluxo atual ativa o modelo concluído automaticamente. Validação industrial independente e homologação em bancada continuam pendentes.

O envio ao repositório foi autorizado pelo autor após a revisão inicial.
