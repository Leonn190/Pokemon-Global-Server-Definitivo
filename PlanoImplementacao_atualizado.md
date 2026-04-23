# PlanoImplementação

**Projeto:** Pokemon Global Server  
**Escopo:** implementação do **novo modelo de batalha**  
**Base de verdade principal:** `DiretrizesBatalha.md`  
**Base complementar:** `ArquiteturaBatalha.md`  
**Lista inicial de golpes de teste:** `Pokemon Global Server - Ataques.csv`  
**Observação fechada:** neste plano, a mecânica de **nível do ataque é totalmente ignorada**. Toda implementação e todo teste usam **apenas a leitura equivalente ao nível 1** dos ataques.  

---

## 1. Objetivo deste documento

Este arquivo define **como o novo modelo de batalha será implementado na prática**, em uma sequência de **9 fases**, com uso controlado do Codex, arquivos de teste por fase e validação prática contínua dentro de um simulador de batalha separado do jogo principal.

A intenção aqui não é apenas listar fases bonitas.  
A intenção é fechar um **guia operacional real** de implementação, revisão, teste, correção e avanço.

Este plano existe para garantir cinco coisas ao mesmo tempo:

1. o novo modelo seja implementado **sem virar remendo do legado**;
2. cada fase deixe algo **realmente testável**;
3. o Codex seja usado com estratégia, e não com prompts soltos e desatualizados;
4. a migração preserve um fluxo claro de revisão humana entre os patches;
5. os ataques novos e antigos da lista atual já entrem como **casos concretos de validação** ao longo das fases.

---

## 2. Princípios do processo de implementação

### 2.1. Diretrizes acima da arquitetura

A arquitetura serve como mapa de arquivos, classes e responsabilidades.  
Mas, em caso de conflito, a referência mais autoritária é sempre o documento de **diretrizes**.

### 2.2. Implementação por fatias testáveis

As fases não serão organizadas apenas por “tema técnico”, e sim por **fatias que possam ser testadas** logo após o patch.

Ou seja: uma fase só é considerada concluída quando:

- o patch foi revisado;
- o arquivo de teste da fase passou;
- o `BatalhaTeste.py` não quebrou;
- a parte implementada pode ser observada de maneira prática.

### 2.3. O legado não some de uma vez

Arquivos legados como `LeitorJogadas.py`, `SistemaBatalha.py`, `ControladorFluxos.py` e `LeitorFluxos.py` não devem ser destruídos cedo demais se ainda forem necessários para manter a capacidade de teste durante a migração.

A remoção real do núcleo legado acontece apenas nas fases finais.

### 2.4. Nada de prompt gigante definitivo do Codex

O projeto **não** deve começar com 9 prompts completos e fechados do Codex.  
O correto é:

- fechar agora o **roteiro mestre**;
- depois gerar o **prompt detalhado do Codex fase a fase**;
- revisar cada patch antes de abrir a próxima fase;
- permitir subfases de correção como `5.1`, `5.2`, `7.1` etc.

Isso evita que prompts futuros fiquem desatualizados quando o código real mudar no caminho.

### 2.5. Teste técnico + teste prático

Cada fase terá dois tipos de validação:

#### A. Teste técnico da fase
Arquivo dedicado, executável, com saída legível no terminal.

Padrão esperado:

- nome do caso;
- entrada;
- saída esperada;
- saída obtida;
- resultado: `OK` ou `FALHOU`.

#### B. Teste prático visual/real
Feito no `Codigo/Outros/BatalhaTeste.py`, que funciona como um simulador de batalha desacoplado do fluxo normal do jogo.

---

## 3. Estratégia oficial de uso do Codex

## 3.1. Fluxo por fase

Cada fase seguirá este fluxo:

### X.0 — análise humana pré-patch
Antes do prompt do Codex, é feita uma análise do que a fase precisa e do que **não** pode ser quebrado.

### X.1 — prompt principal do Codex
É criado o prompt do Codex apenas daquela fase.

Esse prompt precisa fechar:

- objetivo da fase;
- arquivos que pode criar;
- arquivos que pode editar;
- arquivos que não deve tocar;
- testes obrigatórios;
- regras de compatibilidade;
- critério de aceite.

### X.2 — patch do Codex
O Codex produz o patch da fase.

### X.3 — revisão do patch
O patch é lido criticamente.

Nesta etapa pode acontecer:

- aprovação;
- correções pequenas;
- abertura de subfase, como `X.1`, `X.2` ou `X.a`.

### X.4 — execução do teste técnico da fase
Roda o arquivo `TesteFaseXX.py`.

### X.5 — execução do `BatalhaTeste.py`
É feita a validação prática real do que a fase adicionou.

---

## 4. Base de testes do projeto

## 4.1. `Codigo/Outros/BatalhaTeste.py`

### Papel
Arquivo de uso contínuo durante toda a migração.

### Objetivo
Permitir abrir uma batalha **sem entrar pelo fluxo normal do jogo**, apenas para acelerar o teste da nova batalha.

### Regras fechadas para este arquivo
- deve criar um contexto falso de teste;
- deve usar os **recursos normais do jogo**;
- deve materializar os pokémons do jeito convencional;
- deve criar uma batalha **6v6 realista**;
- deve manter o comportamento normal de geração dos pokémons;
- os ataques dos pokémons continuam sendo escolhidos do jeito normal/aleatório do jogo;
- a arena pode ser mais simples e sem cenário elaborado;
- o objetivo dele é testar a batalha, não o fluxo completo do jogo.

### Observação importante
O fato de este arquivo continuar gerando pokémons normalmente, com ataques normais/aleatórios, **não substitui** os testes dirigidos por fase.

Logo:
- `BatalhaTeste.py` é a validação prática contínua;
- `TesteFaseXX.py` é a validação técnica dirigida.

## 4.2. Pasta de testes por fase

Estrutura recomendada:

```text
Codigo/
└── Outros/
    ├── BatalhaTeste.py
    └── TestesBatalha/
        ├── UtilTesteBatalha.py
        ├── TesteFase01.py
        ├── TesteFase02.py
        ├── TesteFase03.py
        ├── TesteFase04.py
        ├── TesteFase05.py
        ├── TesteFase06.py
        ├── TesteFase07.py
        ├── TesteFase08.py
        └── TesteFase09.py
```

### `UtilTesteBatalha.py`
Arquivo opcional, mas recomendado, para evitar repetição.  
Pode concentrar helpers como:

- formatar saída;
- comparar esperado vs obtido;
- imprimir cabeçalhos;
- validar estruturas;
- marcar sucesso/falha.

---

## 5. Ataques de teste já incorporados ao plano

### 5.1. Observação geral
A lista atual de ataques já deve ser usada como **roteiro de validação da implementação**, e não só como conteúdo futuro.

Para este plano:
- considera-se apenas a descrição equivalente ao **nível 1**;
- os nomes e estilos atuais são usados como referência prática de teste;
- ataques com dependências ainda não fechadas entram mais tarde, em fases compatíveis com sua complexidade.

### 5.2. Ataques atualmente listados para validação

#### Já presentes na lista atual
- Investida
- Biscoito
- Enraivecer
- Provocar
- Proteger
- Arranhar
- Recarga
- Energia
- Hiper Raio
- Guilhotina
- Disparo
- Chifrada
- Resetar
- Tankar
- Estocada
- Bola Climática
- Hiper Presa
- Investida Selvagem

#### Novos ataques adicionados para esta rodada de testes
- Dança da chuva
- Bomba de lama
- Parede

### 5.3. Ataques que exigem atenção especial

#### Enraivecer
Hoje menciona um efeito legado (`Aprimorado`) e um efeito atual (`Amplificado`).  
No plano de implementação, esse ataque deve entrar como caso controlado e **só deve ser fechado quando a regra final desse mapeamento estiver resolvida**.

#### Recarga
Depende diretamente da mecânica de recuperação de energia e da regra de excedente após Energizado.  
Por isso entra depois da base de energia estar estável.

#### Bola Climática
É um dos melhores ataques para validar:
- tipo adaptado ao clima;
- aumento de dano por clima;
- uso conjunto de execute principal, execute de estado e executes periféricos quando necessário.

#### Bomba de lama
É um ótimo caso para validar:
- estilo zona;
- aplicação de efeito de tile;
- persistência na arena;
- leitura de tile na `Verifica()`.

#### Parede
É um ótimo caso para validar:
- ataque irregular;
- criação de objeto fixo;
- colisão com parede;
- interação com projétil, dash e impulso.

---

## 6. Mapa dos ataques por fase

A tabela abaixo define **em que fase cada ataque entra como caso de implementação real**.

| Ataque | Estilo atual | Fase principal de implementação | Motivo |
|---|---|---:|---|
| Proteger | alvo | 5 | alvo simples, proteção aplicada no alvo |
| Resetar | alvo | 5 | alvo simples, remoção de variações |
| Hiper Presa | alvo | 5 | alvo ofensivo simples com regra condicional |
| Provocar | status | 5 | status simples com efeito claro |
| Tankar | status | 5 | status de barreira/defesa |
| Arranhar | area | 5 | área simples em cone |
| Estocada | area | 5 | área com condição de “primeiro ataque do turno” |
| Guilhotina | area | 5 | área com execução por limiar de vida |
| Biscoito | tiro | 6 | projétil com cura e lógica de alvo |
| Energia | tiro | 6 | projétil especial simples |
| Disparo | tiro | 6 | projétil com ricochete |
| Bola Climática | tiro | 8 | projétil dependente de clima e lógica avançada |
| Bomba de lama | zona | 8 | zona + efeito de tile persistente |
| Hiper Raio | laser | 7 | valida ação contínua por ticks |
| Chifrada | dash | 7 | valida dash ofensivo |
| Investida | impulso | 7 | valida impulso ofensivo |
| Investida Selvagem | impulso | 7 | impulso com dano de retorno/erro |
| Dança da chuva | status | 8 | clima |
| Parede | irregular | 7 | cria objeto fixo irregular |
| Recarga | status | 8 | energia/excedente pós-Energizado |
| Enraivecer | status | 8 | depende de acerto final dos efeitos envolvidos |

### 6.1. Observação sobre as fases 2 e 4
Mesmo quando um ataque ainda não está implementado de verdade no servidor, ele pode aparecer parcialmente antes:

- na **fase 2**, como preview/indicador;
- na **fase 4**, como referência de ordenação, intervalo ou custo quando isso já for útil.

---

# 7. Plano de implementação em 9 fases

---

## Fase 1 — Contratos, dados-base e estrutura de teste

### Objetivo
Fechar a base contratual do novo modelo e criar o ambiente de teste contínuo.

### Arquivos a criar
- `Dados/Pokemon Global Server - PropriedadesAtaque.json`
- `SimuladorServerJogo/Batalha/EstadosPartida.py`
- `Codigo/Outros/BatalhaTeste.py`
- `Codigo/Outros/TestesBatalha/TesteFase01.py`

### Arquivos a editar
- `Dados/Pokemon Global Server - Ataques.csv`
- pontos de entrada de batalha no client/server
- `Codigo/ModulosBatalha/ControladorBatalha.py`
- `Codigo/Cenas/CenaCombate.py`

### O que deve ser entregue nesta fase
1. estrutura base do JSON técnico de ataques, já incluindo os campos de execute principal, execute de estado e executes periféricos;
2. enum/constantes dos estados macro da partida;
3. contrato inicial de:
   - payload de jogada;
   - histórico do turno;
   - diff final;
4. criação do `BatalhaTeste.py`;
5. primeira leitura dos ataques da lista atual para o JSON técnico.

### Ataques que já entram aqui
Nesta fase, os ataques não entram pela lógica real ainda.  
Eles entram pela **catalogação técnica inicial** no `PropriedadesAtaque.json`.

Prioridade imediata de cadastro técnico:
- Proteger
- Arranhar
- Energia
- Hiper Raio
- Chifrada
- Investida
- Dança da chuva
- Bomba de lama
- Parede

Esses ataques cobrem cedo vários estilos que o sistema terá de suportar.

### Teste técnico da fase
`TesteFase01.py`

Casos mínimos:
- schema mínimo do JSON técnico;
- ids válidos;
- estilos válidos;
- estados macro válidos;
- payload base de jogada válido;
- histórico base válido;
- diff base válido.

### Teste prático no `BatalhaTeste.py`
- abrir batalha fake;
- carregar times 6v6;
- materializar pokémons;
- exibir arena simples;
- permitir inicialização sem entrar no fluxo inteiro do jogo.

### Critério de aceite
- a batalha fake abre;
- os contratos básicos existem;
- os ataques priorizados já existem no JSON técnico inicial.

---

## Fase 2 — Montagem de jogadas e indicadores visuais

### Objetivo
Implementar a camada visual de preparação de jogadas, previews e indicadores.

### Arquivos a criar
- `Codigo/ModulosBatalha/IndicadoresAcoes.py`
- `Codigo/Paineis/PainelAcoes.py`
- `Codigo/Outros/TestesBatalha/TesteFase02.py`

### Arquivos a editar
- `Codigo/ModulosBatalha/MontadorJogada.py`
- `Codigo/ModulosBatalha/ControladorBatalha.py`
- `Codigo/ModulosBatalha/ElementosHudBatalha.py`
- `Codigo/Paineis/FichaPokemonBatalha.py`
- `Codigo/ModulosBatalha/PlayerBatalha.py`
- `Codigo/ModulosBatalha/PlayerControleBat.py`
- `Codigo/Paineis/PainelJogada.py` (se for reaproveitado como base)

### O que deve ser entregue nesta fase
1. preview imediato ao selecionar ataque;
2. indicador “preparando”;
3. indicador “preparado”;
4. posição fantasma;
5. painel lateral de ações;
6. remoção de ação com recalculo do resto;
7. energia visual reservada;
8. botão de pronto;
9. ausência de botão separado de “preparar”;
10. início da absorção do legado de `ControladorFluxos.py`.

### Ataques usados como caso visual nesta fase
- Proteger — preview de alvo
- Arranhar — preview de área
- Bomba de lama — preview de zona
- Energia — preview de projétil
- Hiper Raio — preview de laser
- Chifrada — preview de dash
- Investida — preview de impulso
- Provocar / Tankar — preview de status autouso

### Teste técnico da fase
`TesteFase02.py`

Casos mínimos:
- limite por lado;
- limite por pokémon;
- proibição de repetir ação idêntica no turno;
- ordem local das ações;
- recalculo da posição fantasma;
- estrutura de indicador gerada por estilo.

### Teste prático no `BatalhaTeste.py`
- selecionar pokémon;
- escolher ataque;
- ver preview;
- preparar duas ações válidas;
- apagar uma;
- ver painel e previews recalcularem.

### Critério de aceite
- a montagem do turno já funciona visualmente com o novo modelo;
- o preview deixa de depender do fluxo velho como centro do sistema.

---

## Fase 3 — Server estrutural autoritativo

### Objetivo
Criar a casca real do servidor novo, com `Partida` como dona do estado.

### Arquivos a criar
- `SimuladorServerJogo/Batalha/GerenciadorPartidas.py`
- `SimuladorServerJogo/Batalha/Partida.py`
- `SimuladorServerJogo/Batalha/InicializadorPartida.py`
- `SimuladorServerJogo/Batalha/LogBatalha.py`
- `Codigo/Outros/TestesBatalha/TesteFase03.py`

### Arquivos a editar
- `SimuladorServerJogo/Batalha/GerenciadorBatalhas.py`
- `SimuladorServerJogo/Batalha/SistemaBatalha.py` como ponte temporária

### O que deve ser entregue nesta fase
1. criação formal da partida;
2. snapshot inicial autoritativo;
3. ativos e reservas;
4. arena e clima iniciais;
5. estado macro da partida;
6. fechamento básico de turno;
7. log geral inicial.

### Ataques usados como caso nesta fase
Ainda não entram pela lógica real.  
Aqui o foco é garantir que a partida consiga existir e receber referências de ataques de forma consistente.

### Teste técnico da fase
`TesteFase03.py`

Casos mínimos:
- criar partida;
- criar snapshot;
- receber turno vazio;
- fechar turno vazio;
- atualizar `TickGlobal`;
- transicionar estados corretamente.

### Teste prático no `BatalhaTeste.py`
- abrir batalha fake já usando a nova `Partida`;
- confirmar que a batalha inicia sem depender do motor velho para existir.

### Critério de aceite
- existe um dono claro do estado da batalha;
- o server novo já consegue abrir e fechar turnos vazios.

---

## Fase 4 — Rodador mínimo: movimento, troca e ordem do turno

### Objetivo
Colocar o novo rodador para funcionar com a menor fatia jogável possível.

### Arquivos a criar
- `SimuladorServerJogo/Batalha/ColetorJogadas.py`
- `SimuladorServerJogo/Batalha/ExecutorTurnos.py`
- `SimuladorServerJogo/Batalha/ConstrutorAcao.py`
- `SimuladorServerJogo/Batalha/FisicaBatalha.py`
- `Codigo/Outros/TestesBatalha/TesteFase04.py`

### Arquivos a editar
- `SimuladorServerJogo/Batalha/ObjetoBatalha.py`
- `SimuladorServerJogo/Batalha/PokemonBatalha.py`
- `SimuladorServerJogo/Batalha/DetectorColisoes.py`

### O que deve ser entregue nesta fase
1. ordenação por inteligência;
2. empate por velocidade;
3. início/fim/cancelamento de ação;
4. movimento normal;
5. custo por tile;
6. troca de 5 ticks;
7. segunda ação começar 1 tick após a primeira terminar;
8. log básico de movimento/troca;
9. condição de parada do turno.

### Ataques/casos usados nesta fase
Aqui o foco é deslocamento e troca.  
Não entra ataque real ainda.

Mas os seguintes “estilos de referência” ajudam na validação:
- movimento normal
- troca
- posição fantasma do preview já refletindo a timeline real

### Teste técnico da fase
`TesteFase04.py`

Casos mínimos:
- movimento simples;
- dois movimentos simultâneos;
- troca normal;
- troca cancelada por morte;
- segunda ação após primeira;
- cobrança correta por deslocamento real.

### Teste prático no `BatalhaTeste.py`
- mover pokémon;
- preparar troca;
- validar posição final e troca concluída no tempo certo.

### Critério de aceite
- já existe um turno jogável básico no motor novo.

---

## Fase 5 — Ataques simples: alvo, status, área e zona instantânea

### Objetivo
Implementar a primeira camada de ataque real sem objeto persistente.

### Arquivos a criar
- `SimuladorServerJogo/Batalha/ConstrutorAtaque.py`
- `SimuladorServerJogo/Batalha/MotorAcoes.py`
- `SimuladorServerJogo/Logica/Executes/ExecuteAtaques.py`
- `Codigo/Outros/TestesBatalha/TesteFase05.py`

### Arquivos a editar
- `SimuladorServerJogo/Batalha/PokemonBatalha.py`
- `SimuladorServerJogo/Batalha/FraquezasResistencias.py`
- `SimuladorServerJogo/Batalha/ConstrutorAcao.py`
- `SimuladorServerJogo/Batalha/LogBatalha.py`

### O que deve ser entregue nesta fase
1. construção de ataque por estilo simples;
2. resolve alvo válido;
3. resolve autouso;
4. resolve área instantânea;
5. resolve zona instantânea;
6. dano;
7. cura;
8. barreira;
9. aplicação de efeito;
10. falha por alvo fora de alcance/morto;
11. primeiro fluxo real de execute → método do pokémon.

### Ataques implementados/testados aqui
- Proteger
- Resetar
- Hiper Presa
- Provocar
- Tankar
- Arranhar
- Estocada
- Guilhotina

### Observações por ataque
#### Proteger
Valida alvo, status positivo e proteção.

#### Resetar
Valida ataque de alvo sem dano, alterando estado/variações.

#### Hiper Presa
Valida dano de alvo e regra condicional ligada a crítico/recuo.

#### Provocar
Valida status autouso com efeito importante para seleção de alvo futura.

#### Tankar
Valida barreira e buff defensivo.

#### Arranhar
Valida área simples.

#### Estocada
Valida área com condicional dependente da ordem das ações do turno.

#### Guilhotina
Valida área com execução por porcentagem de vida.

### Teste técnico da fase
`TesteFase05.py`

Casos mínimos:
- Proteger aplica Protegido ao alvo;
- Resetar remove variações;
- Provocar aplica status;
- Tankar gera barreira;
- Arranhar acerta área certa;
- Estocada respeita condição de “primeiro ataque”;
- Guilhotina executa somente abaixo do limiar correto.

### Teste prático no `BatalhaTeste.py`
- forçar situações simples de alvo/status/área;
- confirmar animação básica e diff coerente.

### Critério de aceite
- a primeira camada real de dano/efeito já existe no novo motor.

---

## Fase 6 — Objetos persistentes, projéteis e colisão rica

### Objetivo
Implementar projéteis como objetos de batalha com vida própria.

### Arquivos a criar
- `SimuladorServerJogo/Batalha/ProjetilBatalha.py`
- `SimuladorServerJogo/Batalha/ParedeBatalha.py` (base mínima)
- `SimuladorServerJogo/Batalha/ConstrutoBatalha.py` (base mínima)
- `Codigo/Outros/TestesBatalha/TesteFase06.py`

### Arquivos a editar
- `SimuladorServerJogo/Batalha/FisicaBatalha.py`
- `SimuladorServerJogo/Batalha/DetectorColisoes.py`
- `SimuladorServerJogo/Batalha/MotorAcoes.py`
- `SimuladorServerJogo/Batalha/ExecutorTurnos.py`
- `SimuladorServerJogo/Batalha/ConstrutorAtaque.py`

### O que deve ser entregue nesta fase
1. criação de projétil;
2. projétil age só no tick seguinte;
3. movimento por tick;
4. colisão com pokémon;
5. colisão com parede;
6. colisão com projétil;
7. destruir / atravessar / ricochetear;
8. log de trajetória;
9. objetos persistentes no diff.

### Ataques implementados/testados aqui
- Energia
- Biscoito
- Disparo

### Observações por ataque
#### Energia
Projétil especial simples para validar o esqueleto básico do estilo tiro.

#### Biscoito
Projétil de cura, excelente para validar:
- projétil sem dano direto obrigatório;
- cura ao atingir;
- pilha/stack específica do ataque no futuro.

#### Disparo
Projétil de ricochete, excelente para validar:
- comportamento de fim por colisão;
- ricochete separado por tipo de colisão.

### Teste técnico da fase
`TesteFase06.py`

Casos mínimos:
- projétil simples;
- projétil de cura;
- projétil com ricochete;
- projétil destruído em parede;
- deduplicação de colisão por tick;
- ação termina ao criar projétil, mas projétil continua vivo.

### Teste prático no `BatalhaTeste.py`
- lançar tiros reais;
- ver rota;
- ver colisão;
- ver finalização.

### Critério de aceite
- projéteis já são objetos reais do novo sistema.

---

## Fase 7 — Dash, impulso, laser e ataque irregular com parede

### Objetivo
Fechar os estilos com física própria e timeline mais complexa.

### Arquivos a criar
- `Codigo/Outros/TestesBatalha/TesteFase07.py`

### Arquivos a editar
- `SimuladorServerJogo/Batalha/ConstrutorAtaque.py`
- `SimuladorServerJogo/Batalha/ConstrutorAcao.py`
- `SimuladorServerJogo/Batalha/FisicaBatalha.py`
- `SimuladorServerJogo/Batalha/MotorAcoes.py`
- `SimuladorServerJogo/Batalha/ExecutorTurnos.py`
- `SimuladorServerJogo/Batalha/DetectorColisoes.py`
- `SimuladorServerJogo/Batalha/ParedeBatalha.py`
- `SimuladorServerJogo/Batalha/ConstrutoBatalha.py` (se Parede nascer como construto fixo especial)

### O que deve ser entregue nesta fase
1. dash real;
2. impulso real com desaceleração;
3. ricochete físico;
4. laser contínuo por tick;
5. colisão com parede;
6. criação de parede como objeto fixo;
7. logs de avanço e impacto.

### Ataques implementados/testados aqui
- Chifrada
- Investida
- Investida Selvagem
- Hiper Raio
- Parede

### Observações por ataque
#### Chifrada
Valida dash ofensivo.

#### Investida
Valida impulso com dano e avanço.

#### Investida Selvagem
Valida impulso mais pesado e dano de retorno/erro.

#### Hiper Raio
Valida ataque laser contínuo.

#### Parede
Valida ataque irregular que cria objeto fixo de colisão.

### Teste técnico da fase
`TesteFase07.py`

Casos mínimos:
- dash até colisão;
- dash contra parede;
- impulso até velocidade zero;
- impulso com ricochete;
- laser com avanço por tick;
- criação de parede e colisão contra ela.

### Teste prático no `BatalhaTeste.py`
- usar dash, impulso e laser em batalha fake;
- ver interação com paredes e colisões físicas.

### Critério de aceite
- todos os estilos centrais de movimentação ofensiva já existem no novo motor.

---

## Fase 8 — Efeitos, clima, tile, energia e passivas

### Objetivo
Fechar a camada de fidelidade do sistema: `Verifica()`, clima, tile, energia avançada e passivas.

### Arquivos a criar
- `Codigo/Outros/TestesBatalha/TesteFase08.py`

### Arquivos a editar
- `SimuladorServerJogo/Batalha/PokemonBatalha.py`
- `SimuladorServerJogo/Batalha/Partida.py`
- `SimuladorServerJogo/Batalha/LogBatalha.py`
- `SimuladorServerJogo/Batalha/FisicaBatalha.py`
- `SimuladorServerJogo/Batalha/ConstrutorAtaque.py`
- `SimuladorServerJogo/Batalha/MotorAcoes.py`

### O que deve ser entregue nesta fase
1. `Verifica()` completa;
2. reaplicação de efeitos;
3. gasto/expiração de duração;
4. clima;
5. tile;
6. recuperação de energia;
7. regras de clamp;
8. passivas dentro dos métodos e nos arquivos `.py` próprios de item/habilidade;
9. interações com Protegido, Evasivo, Refletindo, Imortal etc.

### Ataques implementados/testados aqui
- Dança da chuva
- Bomba de lama
- Bola Climática
- Recarga
- Enraivecer

### Observações por ataque
#### Dança da chuva
Valida mudança de clima.

#### Bomba de lama
Valida zona + criação de tile lama persistente.

#### Bola Climática
Valida adaptação ao clima, aumento de dano por clima e uso mais elaborado dos executes do ataque.

#### Recarga
Valida recuperação de energia e a regra de excedente persistente após Energizado.

#### Enraivecer
Só deve ser fechado nesta fase se o mapeamento do efeito legado estiver resolvido de forma oficial.

### Teste técnico da fase
`TesteFase08.py`

Casos mínimos:
- mudança de clima;
- dano/benefício do clima;
- criação e persistência de tile;
- aplicação e duração de efeitos;
- energia recuperada corretamente;
- Bola Climática mudando comportamento conforme clima;
- Recarga respeitando as regras atuais de energia;
- Enraivecer só ativando a condição certa.

### Teste prático no `BatalhaTeste.py`
- batalhas com clima ativo;
- validação visual de tile e efeitos;
- ver interação entre ataques, clima e arena.

### Critério de aceite
- o sistema novo já está fiel à maior parte das diretrizes, não só funcional.

---

## Fase 9 — Leitura de logs, animação, reconciliamento final e remoção do núcleo legado

### Objetivo
Completar a virada final do client e aposentar o núcleo velho.

### Arquivos a criar
- `Codigo/ModulosBatalha/ExecutorAnimacao.py`
- `Codigo/Outros/TestesBatalha/TesteFase09.py`

### Arquivos a editar
- `Codigo/ModulosBatalha/LeitorLogs.py`
- `Codigo/ModulosGerais/PokemonAnimator.py`
- `Codigo/ModulosBatalha/InicializadorBatalha.py`
- `Codigo/ModulosBatalha/FinalizadorBatalha.py`
- `Codigo/ModulosBatalha/ControladorBatalha.py`

### Arquivos legados que devem ser esvaziados/removidos ao final
- `SimuladorServerJogo/Batalha/LeitorJogadas.py`
- `SimuladorServerJogo/Batalha/SistemaBatalha.py`
- `SimuladorServerJogo/Batalha/SimuladorFisica.py`
- `Codigo/ModulosBatalha/SistemaBatalha.py`
- `Codigo/ModulosBatalha/LeitorFluxos.py`
- `Codigo/ModulosBatalha/ControladorFluxos.py`

### O que deve ser entregue nesta fase
1. leitura fiel do histórico;
2. animação por timeline;
3. interpolação visual;
4. aplicação do diff final;
5. reconciliamento final de estado;
6. fechamento da batalha;
7. remoção do coração do legado.

### Ataques usados como validação final
Nesta fase, todos os ataques já implementados devem ser validados em fluxo completo:
- alvo;
- status;
- área;
- zona;
- projétil;
- dash;
- impulso;
- laser;
- clima;
- tile;
- irregular.

### Teste técnico da fase
`TesteFase09.py`

Casos mínimos:
- leitura do histórico do turno;
- interpolação de movimento;
- aplicação de dano sem recalcular localmente;
- sincronização de efeitos;
- sincronização de objetos persistentes;
- diff final reconciliando vida, energia, barreira, posição e efeitos.

### Teste prático no `BatalhaTeste.py`
- batalha completa 6v6 usando o motor novo;
- turnos sucessivos;
- troca;
- múltiplos estilos de ataque;
- encerramento normal.

### Critério de aceite
- o novo modelo funciona ponta a ponta;
- o núcleo legado deixa de ser necessário para a batalha.

---

# 8. Regras de revisão após cada patch

## 8.1. O que revisar sempre
Depois de cada patch do Codex, revisar no mínimo:

1. se respeitou as diretrizes;
2. se respeitou a ordem da fase;
3. se não adiantou lógica de fase futura sem necessidade;
4. se não reacoplou o sistema novo ao legado de forma ruim;
5. se não explodiu responsabilidades em arquivos errados;
6. se o teste técnico da fase está bom;
7. se o `BatalhaTeste.py` continua funcional.

## 8.2. Quando criar subfase
Subfase deve existir quando:

- o patch principal ficou quase bom, mas ainda precisa ajustes locais;
- uma correção é pequena demais para justificar abrir a próxima fase;
- um teste falha por detalhe pontual;
- há necessidade de ajustar só um arquivo crítico ou só um bloco de comportamento.

Exemplos:
- `5.1` corrigir execução de `Guilhotina`;
- `6.1` corrigir ricochete de `Disparo`;
- `7.1` corrigir colisão de `Parede`;
- `8.1` corrigir interação entre `Bola Climática` e clima.

---

# 9. Critério oficial para avançar de fase

Uma fase só pode ser considerada concluída quando:

- o patch foi lido e aceito;
- o `TesteFaseXX.py` passa;
- o `BatalhaTeste.py` continua abrindo e não quebra o que já existia;
- o escopo prometido da fase está realmente visível no código e no teste;
- os ataques previstos para aquela fase já entraram como casos reais de validação.

---

# 10. Resumo executivo do plano

## Sequência final fechada
1. **Contratos, dados-base e estrutura de teste**
2. **Montagem de jogadas e indicadores visuais**
3. **Server estrutural autoritativo**
4. **Rodador mínimo: movimento, troca e ordem do turno**
5. **Ataques simples: alvo, status, área e zona instantânea**
6. **Objetos persistentes, projéteis e colisão rica**
7. **Dash, impulso, laser e ataque irregular com parede**
8. **Efeitos, clima, tile, energia e passivas**
9. **Leitura de logs, animação, reconciliamento final e remoção do núcleo legado**

## Ataques novos destacados no plano
- **Dança da chuva** — valida clima
- **Bomba de lama** — valida zona + tile
- **Parede** — valida ataque irregular + objeto fixo

## Regra final do processo
O plano não será executado como uma sequência cega de prompts gigantes.  
Ele será executado como:

- fase,
- patch,
- revisão,
- teste técnico,
- teste prático,
- ajustes,
- próxima fase.

---

**FIM DO PLANO DE IMPLEMENTAÇÃO**
