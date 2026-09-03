# QualityAI — Etapas 1 e 2

> Documento de concepção da prova de conceito de um sistema autotreinável para inspeção visual de peças industriais.

| Informação | Definição |
| --- | --- |
| Produto | QualityAI |
| Usuário principal | Inspetor de qualidade industrial |
| Dataset inicial | 10 imagens `OK` e 10 imagens `NOK` por projeto |
| Entrada | Upload de arquivo ou captura por câmera/webcam |
| Saída inicial | Classificação binária `OK` ou `NOK` |
| Papel da IA | Apoiar a decisão do inspetor, sem substituir a validação humana |
| Estágio | Prova de conceito |

---

## Etapa 1 — Entendimento do problema e do contexto

### 1. Quem é o usuário?

O usuário principal é o **inspetor de qualidade industrial** responsável por verificar se peças atendem aos critérios definidos pela empresa. Ele conhece o produto e seus padrões de conformidade, mas não precisa dominar programação, visão computacional ou treinamento de modelos de inteligência artificial.

Usuários secundários e pessoas envolvidas no fluxo incluem:

- **Operador de produção:** disponibiliza a peça ou registra a imagem durante o processo produtivo.
- **Engenheiro de qualidade:** define critérios, acompanha indicadores e valida o processo de inspeção.
- **Gestor de produção:** monitora produtividade, rejeições, retrabalho e impactos operacionais.
- **Equipe de TI ou automação:** mantém infraestrutura, dispositivos, acesso e integrações futuras.

### 2. Qual problema o projeto resolve?

A inspeção visual manual pode variar conforme a experiência, o cansaço, a interpretação e as condições de trabalho de cada pessoa. Em operações com diferentes tipos de peça, soluções convencionais de visão computacional também podem exigir configuração técnica e desenvolvimento específico para cada novo cenário.

O QualityAI pretende reduzir essas barreiras por meio de um fluxo no qual o próprio inspetor:

1. cria um projeto para o tipo de peça que deseja inspecionar;
2. fornece exemplos visuais classificados como `OK` e `NOK`;
3. revisa os rótulos e autoriza o treinamento;
4. utiliza o modelo resultante para apoiar novas inspeções;
5. corrige resultados quando necessário e gera versões posteriores do modelo.

O problema central pode ser resumido assim:

> **Como permitir que um profissional de qualidade ensine um sistema a diferenciar peças conformes e não conformes, sem precisar programar, preservando supervisão e rastreabilidade?**

### 3. Quem são os interessados?

| Interessado | Relação com o projeto | Principal expectativa |
| --- | --- | --- |
| Inspetor de qualidade | Usuário principal e revisor humano | Operação simples, resultado compreensível e possibilidade de correção |
| Operador de produção | Participa da obtenção das imagens e da separação das peças | Resposta rápida e instrução clara |
| Engenharia de qualidade | Define padrões e valida o desempenho | Métricas confiáveis, rastreabilidade e controle de versões |
| Gestão de produção | Acompanha os impactos do processo | Menos retrabalho, rejeição indevida e desperdício |
| TI e automação | Sustenta o ambiente tecnológico | Segurança, compatibilidade e facilidade de manutenção |
| Clientes da indústria | Recebem o produto inspecionado | Maior consistência e redução de peças defeituosas |
| Auditores e responsáveis por conformidade | Verificam o processo e suas evidências | Histórico dos dados, modelos e decisões |

### 4. Por que o projeto gera valor?

| Dimensão | Valor esperado |
| --- | --- |
| Qualidade | Apoia uma avaliação mais uniforme entre turnos e profissionais |
| Produtividade | Reduz o tempo gasto em triagens visuais repetitivas |
| Flexibilidade | Possibilita configurar um projeto separado para cada peça |
| Acessibilidade | Esconde a complexidade técnica do treinamento atrás de um fluxo guiado |
| Aprendizado | Permite incorporar correções humanas em versões futuras do dataset |
| Rastreabilidade | Registra qual modelo produziu cada classificação |
| Gestão | Produz dados que podem apoiar análises de rejeição e melhoria do processo |

### Hipótese de valor

Se o inspetor puder ensinar o sistema usando exemplos reais e revisar resultados incertos, então a empresa poderá tornar a inspeção visual mais consistente e rastreável, reduzindo subjetividade sem retirar a responsabilidade do profissional de qualidade.

### Limite do escopo inicial

O primeiro MVP realiza apenas a classificação binária `OK`/`NOK`. Identificar o tipo do defeito, localizar visualmente sua região ou comandar automaticamente equipamentos industriais são evoluções posteriores e não fazem parte desta prova de conceito.

---

## Etapa 2 — Entendimento do usuário e requisitos

### 1. Persona

> **Mariana Alves — Inspetora de Qualidade**
>
> Persona fictícia construída para representar o usuário principal do QualityAI.

| Característica | Descrição |
| --- | --- |
| Função | Inspecionar peças, registrar não conformidades e apoiar a liberação de lotes |
| Contexto | Trabalha próxima à produção, alternando entre computador, câmera e instrumentos de inspeção |
| Conhecimento técnico | Domina critérios de qualidade da peça, mas não desenvolve software nem modelos de IA |
| Objetivo principal | Tomar decisões consistentes e justificáveis com menos esforço repetitivo |
| Motivação | Reduzir erros, retrabalho e divergências de avaliação entre turnos |
| Frustração | Sistemas complexos que exigem suporte técnico para cada nova peça |
| Necessidade | Um fluxo guiado, linguagem direta, feedback visual e controle sobre a decisão final |

#### Objetivos da persona

- Configurar uma nova inspeção sem depender de programação.
- Saber quantas imagens ainda faltam em cada classe.
- Confirmar que os exemplos estão corretamente rotulados antes do treinamento.
- Entender o resultado e reconhecer situações de baixa confiança.
- Corrigir classificações incorretas sem perder o histórico anterior.
- Comprovar qual versão do modelo foi usada em cada resultado.

#### Critérios de sucesso para Mariana

- Concluir o fluxo inicial sem treinamento técnico especializado.
- Receber orientações claras quando uma imagem não puder ser utilizada.
- Nunca confundir uma previsão da IA com uma aprovação humana definitiva.
- Recuperar os projetos e históricos de treinamento já realizados.

### 2. Jornada do usuário

| Etapa | Ação do inspetor | Resposta esperada do sistema |
| --- | --- | --- |
| 1. Criar projeto | Informa nome da peça e uma descrição do padrão de inspeção | Cria um espaço isolado para dataset, modelo e histórico |
| 2. Coletar exemplos | Envia arquivos ou captura imagens pela câmera | Mostra prévia, classe atribuída e contador `OK`/`NOK` |
| 3. Revisar dataset | Confere as 10 imagens de cada classe e corrige rótulos | Sinaliza duplicidades, arquivos inválidos e amostras ausentes |
| 4. Confirmar treinamento | Revisa um resumo e seleciona **Treinar modelo** | Congela uma versão do dataset e inicia o processamento |
| 5. Avaliar resultado | Consulta métricas e avisos da versão treinada | Explica os resultados e mantém o modelo aguardando validação humana |
| 6. Inspecionar peça | Envia ou fotografa uma nova peça | Retorna `OK` ou `NOK`, confiança e versão do modelo utilizada |
| 7. Revisar decisão | Confirma ou corrige o resultado, principalmente quando há baixa confiança | Registra a decisão humana e preserva a previsão original |
| 8. Evoluir o modelo | Seleciona exemplos corrigidos e solicita novo treinamento | Cria outra versão sem apagar dataset, modelo ou métricas anteriores |

### 3. Requisitos funcionais

| ID | Requisito |
| --- | --- |
| RF-01 | O sistema deve permitir criar projetos independentes para diferentes tipos de peça. |
| RF-02 | O sistema deve aceitar imagens por upload e por captura de câmera/webcam. |
| RF-03 | O inspetor deve poder classificar cada amostra como `OK` ou `NOK`. |
| RF-04 | O sistema deve exibir separadamente a quantidade de imagens de cada classe. |
| RF-05 | O sistema deve exigir, na prova de conceito, pelo menos 10 imagens `OK` e 10 imagens `NOK` antes de liberar o treinamento. |
| RF-06 | O sistema deve permitir visualizar, remover e corrigir o rótulo de uma imagem antes do treinamento. |
| RF-07 | O sistema deve rejeitar arquivos corrompidos ou incompatíveis e informar o motivo ao usuário. |
| RF-08 | O treinamento deve começar somente após a confirmação manual do inspetor. |
| RF-09 | O sistema deve informar o andamento e o resultado do treinamento sem bloquear a navegação da interface. |
| RF-10 | Cada treinamento deve gerar uma versão identificável do dataset, do modelo e das métricas. |
| RF-11 | O sistema deve classificar uma nova imagem como `OK` ou `NOK`. |
| RF-12 | O resultado deve apresentar a confiança da previsão e a versão do modelo utilizada. |
| RF-13 | Resultados abaixo do limite de confiança configurado devem ser encaminhados para revisão humana. |
| RF-14 | O inspetor deve poder confirmar ou corrigir uma classificação, preservando a previsão original no histórico. |
| RF-15 | O sistema deve armazenar imagens, rótulos, versões do modelo, métricas e revisões dentro do respectivo projeto. |
| RF-16 | O sistema deve permitir iniciar um retreinamento com os exemplos confirmados, criando uma nova versão sem sobrescrever a anterior. |
| RF-17 | O sistema deve manter um registro auditável de treinamentos, inspeções, previsões e decisões humanas. |

### 4. Requisitos não funcionais

| ID | Categoria | Requisito |
| --- | --- | --- |
| RNF-01 | Usabilidade | O fluxo deve usar linguagem industrial direta, instruções visuais e feedback claro, sem exigir conhecimento de IA. |
| RNF-02 | Desempenho | A classificação deve ter meta inicial de resposta em até 3 segundos nas condições de hardware e rede definidas para o piloto. |
| RNF-03 | Responsividade | A interface deve permanecer utilizável durante upload e treinamento, exibindo progresso e possíveis falhas. |
| RNF-04 | Segurança | Dados em trânsito e armazenados devem ser protegidos; o acesso aos projetos deve respeitar permissões de usuário. |
| RNF-05 | Rastreabilidade | Toda previsão deve ser associada ao projeto, imagem, horário, versão do modelo e decisão humana correspondente. |
| RNF-06 | Reprodutibilidade | Uma versão deve preservar referências ao dataset, configuração de treinamento, métricas e artefato do modelo. |
| RNF-07 | Confiabilidade | Falhas de câmera, upload ou treinamento não devem apagar dados previamente confirmados. |
| RNF-08 | Compatibilidade | O sistema deve suportar formatos de imagem comuns e câmeras acessíveis por navegadores modernos. |
| RNF-09 | Manutenibilidade | Componentes de coleta, treinamento, inferência e auditoria devem permanecer separados para facilitar evolução futura. |
| RNF-10 | Transparência | A interface deve deixar explícito que a saída é uma previsão e que datasets pequenos produzem resultados instáveis. |

### 5. Casos de uso

#### UC-01 — Criar um projeto de inspeção

| Campo | Descrição |
| --- | --- |
| Ator principal | Inspetor de qualidade |
| Pré-condição | Inspetor identificado e autorizado no sistema |
| Fluxo principal | O inspetor cria um projeto, informa o nome da peça e descreve o objetivo da inspeção; o sistema cria o projeto vazio. |
| Exceção | Se já existir um projeto com o mesmo nome, o sistema solicita um nome diferente. |
| Pós-condição | Projeto disponível para receber imagens, sem compartilhar dados com outros tipos de peça. |

#### UC-02 — Montar e revisar o dataset inicial

| Campo | Descrição |
| --- | --- |
| Ator principal | Inspetor de qualidade |
| Pré-condição | Projeto criado |
| Fluxo principal | O inspetor envia ou captura imagens, atribui `OK` ou `NOK`, acompanha os contadores e revisa as 20 amostras. |
| Exceções | Arquivos incompatíveis são recusados; imagens ausentes ou rótulos incompletos mantêm o treinamento bloqueado. |
| Pós-condição | Dataset com no mínimo 10 imagens confirmadas em cada classe. |

#### UC-03 — Treinar e avaliar uma versão do modelo

| Campo | Descrição |
| --- | --- |
| Ator principal | Inspetor de qualidade |
| Pré-condição | Dataset mínimo completo e revisado |
| Fluxo principal | O inspetor confirma o resumo e inicia o treinamento; o sistema versiona o dataset, processa as imagens e apresenta métricas e alertas. |
| Exceção | Em caso de falha, o sistema registra o erro, preserva os dados e permite nova tentativa. |
| Pós-condição | Nova versão do modelo registrada e disponível para validação. |

#### UC-04 — Inspecionar uma nova peça

| Campo | Descrição |
| --- | --- |
| Ator principal | Inspetor de qualidade |
| Pré-condição | Projeto com uma versão de modelo ativa |
| Fluxo principal | O inspetor envia ou captura uma nova imagem; o sistema a processa e apresenta `OK` ou `NOK`, confiança e versão utilizada. |
| Exceção | Imagem inválida gera orientação para uma nova captura; baixa confiança direciona o resultado à revisão manual. |
| Pós-condição | Previsão registrada no histórico, aguardando ou acompanhada da decisão humana. |

#### UC-05 — Revisar ou corrigir um resultado

| Campo | Descrição |
| --- | --- |
| Ator principal | Inspetor de qualidade |
| Pré-condição | Uma previsão foi produzida |
| Fluxo principal | O inspetor compara a imagem com o padrão de qualidade, confirma ou corrige a classe e registra sua decisão. |
| Exceção | Se não for possível decidir pela imagem, o inspetor marca o caso para nova captura ou análise externa. |
| Pós-condição | Previsão original e decisão humana preservadas; exemplo confirmado pode ser candidato ao próximo treinamento. |

#### UC-06 — Retreinar sem perder o histórico

| Campo | Descrição |
| --- | --- |
| Ator principal | Inspetor de qualidade |
| Pré-condição | Existem novos exemplos confirmados e uma versão anterior do modelo |
| Fluxo principal | O inspetor revisa os exemplos adicionais, solicita o retreinamento e compara as métricas da nova versão com a anterior. |
| Exceção | Se os dados não forem válidos, o sistema mantém a versão ativa e explica o que deve ser corrigido. |
| Pós-condição | Nova versão registrada; a anterior continua disponível para auditoria e possível restauração. |

---

## Interface conceitual do sistema

| Operação | Entrada | Saída |
| --- | --- | --- |
| Criar projeto | Nome da peça e descrição | Identificador do projeto |
| Adicionar amostra | Imagem e rótulo `OK`/`NOK` | Amostra validada e contador atualizado |
| Treinar | Projeto, versão confirmada do dataset e autorização do inspetor | Modelo versionado, métricas e avisos |
| Inspecionar | Nova imagem e versão ativa | Classe `OK`/`NOK`, confiança e versão do modelo |
| Revisar | Previsão, decisão humana e observação opcional | Histórico atualizado e exemplo candidato a retreinamento |
| Retreinar | Dataset ampliado e confirmação do inspetor | Nova versão comparável às anteriores |

## Regras de negócio

1. Cada tipo de peça deve possuir seu próprio projeto, dataset e histórico de modelos.
2. O treinamento inicial permanece bloqueado enquanto não houver 10 imagens confirmadas em cada classe.
3. O sistema nunca inicia o treinamento sem confirmação explícita do inspetor.
4. O limite de baixa confiança deve ser definido e validado para cada projeto antes do piloto industrial.
5. Toda classificação deve informar a versão do modelo que a produziu.
6. Uma correção humana só pode integrar um dataset posterior após confirmação do rótulo.
7. Retreinamentos criam novas versões; versões anteriores não são apagadas nem alteradas.
8. O conjunto inicial de 20 imagens não autoriza uso autônomo para liberar ou rejeitar peças em produção.

## Critérios de aceitação da prova de conceito

- O inspetor consegue criar um projeto sem conhecimento de programação.
- O sistema aceita imagens por upload e câmera, exibindo a contagem por classe.
- O treinamento fica indisponível com menos de 10 exemplos `OK` ou 10 exemplos `NOK`.
- Após a revisão das 20 imagens, o inspetor consegue confirmar e iniciar o treinamento.
- Uma nova imagem recebe resultado `OK` ou `NOK`, confiança e versão do modelo.
- Uma previsão de baixa confiança exige revisão e não é apresentada como decisão definitiva.
- A correção humana preserva o resultado original e pode alimentar um novo treinamento.
- Dataset, métricas e modelo permanecem ligados à mesma versão e podem ser auditados.

## Riscos e cuidados

| Risco | Consequência | Tratamento proposto |
| --- | --- | --- |
| Dataset muito pequeno | Modelo pode memorizar exemplos e falhar em imagens novas | Tratar as 20 imagens apenas como demonstração e ampliar o conjunto antes do piloto |
| Iluminação ou enquadramento variável | Previsões inconsistentes | Padronizar captura e incluir variações reais no dataset |
| Classes pouco representativas | Falsa impressão de desempenho | Coletar lotes, turnos, câmeras e condições diferentes |
| Confiança excessiva na automação | Liberação ou rejeição incorreta | Manter revisão humana e comunicar claramente as limitações |
| Mudança no processo ou na peça | Modelo deixa de representar a produção | Monitorar resultados, versionar dados e retreinar quando necessário |

## Próximas etapas sugeridas

1. Validar esta definição com um inspetor e um engenheiro de qualidade.
2. Escolher uma única peça piloto e registrar seus critérios reais de conformidade.
3. Criar o protótipo navegável das telas e testar a jornada com usuários.
4. Implementar coleta, treinamento, classificação, revisão e versionamento.
5. Ampliar o dataset e elaborar um protocolo de validação industrial independente.

---

[← Voltar ao README](../README.md)
