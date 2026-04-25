# DiretrizesBatalha v7

## 1. Objetivo do documento

### Atualização v7 — fechamentos finais de energia, efeitos, alvos, barreira e escopo

Esta versão consolida as respostas finais dadas após a v6 e transforma lacunas de implementação em regras objetivas para a primeira fase real do sistema **Batalha**.

Decisões globais adicionadas na v7:

- Energia oficial é gasta na **execução** da ação, pelo servidor, dentro do fluxo do `RodadorTurno`. O cliente apenas prevê e bloqueia casos óbvios.
- Movimento custa `10` de energia.
- Troca custa `15` de energia.
- Energia recupera no **fim da rodada**, depois da resolução dos passos e verificações.
- Efeitos formais decrementam duração no **fim de cada passo global**.
- O limite de efeitos formais é **total**, com no máximo 4 efeitos simultâneos por Pokémon.
- Tentativa de aplicar o 5º efeito formal deve ser bloqueada e registrada em log; não substitui automaticamente efeitos existentes.
- Ataques miram **área** por padrão.
- O ocupante da área é resolvido no momento da **execução** da ação, não no momento da preparação.
- Ataques em linha/coluna recalculam seus alvos no momento da execução.
- Dano absorvido por barreira não conta para XP nem para vampirismo.
- Não existe troca automática após morte na v7.
- Captura não entra na v7.
- Construtos entram apenas como classe/contrato mínimo, sem regras complexas.
- Para XP, a nomenclatura correta é `rodadas`, não `turnos`.

Essas decisões devem ser tratadas como regras fechadas da v7 e têm prioridade sobre qualquer trecho anterior que pareça deixar esses pontos em aberto.


### Atualização v6 — ataques iniciais, efeitos existentes e decisões fechadas

Esta versão incorpora as respostas de fechamento dadas após a v4 e acrescenta uma camada inicial de leitura dos ataques e efeitos já existentes nos CSVs atuais. As mudanças não alteram a intenção central do documento: o sistema se chama **Batalha**, `CenaCombate`/cena equivalente apenas hospeda a cena da batalha dentro do sistema normal de cenas do jogo, e os arquivos novos devem seguir a arquitetura nova sem depender de arquivos legados.

Decisões globais agora fechadas:

- O nome oficial do sistema novo é **Batalha**.
- O caminho correto do adaptador client-server é `Codigo/Server/ServerBatalha.py`, seguindo o padrão real do projeto.
- A pasta `SimuladorServerJogo/Batalha/` deve ser criada para a lógica nova do servidor.
- No servidor, não usar nomenclatura fixa de `aliado`/`inimigo` como fonte de regra. O servidor deve trabalhar com `lado_id` e relações neutras entre lados, já pensando em PVP.
- Todo RNG da partida deve nascer de `seed_partida` e ser consumido por um gerador controlado da partida.
- `tick` fica reservado para animação/simulação visual do que já aconteceu. A lógica de batalha usa `rodada` e `passo`.
- Efeitos formais duram em **passos**.
- A IA de batalha fica no **cliente**, monta uma jogada para o `lado_id` controlado por bot e envia essa jogada pelo mesmo caminho JSON usado pelo jogador.
- A v6 passa a tratar os 18 ataques iniciais do CSV e os 51 registros de efeitos existentes como base prática para o primeiro JSON de propriedades.


Este arquivo define a arquitetura inicial do novo sistema de batalha do jogo.

A intenção desta versão é organizar os arquivos, responsabilidades, métodos conceituais e `selfs` relevantes antes da implementação completa. O documento ainda não fecha todos os detalhes finais de balanceamento, IA e polimento visual, mas agora consolida regras iniciais de atributos, assertividade, dano, efeitos, barreira, ataques iniciais e interpretação dos efeitos existentes para que o sistema cresça sem misturar cliente, servidor e dados.

Nesta fase, o foco real é o modo **Confronto**, ou seja, a batalha iniciada quando o jogador encontra um Pokémon selvagem no mundo e colide/interage com ele. Os modos **Treinador** e **PVP** devem existir como conceitos no sistema, mas não são o foco da implementação inicial.

---

## 2. Princípios gerais do sistema de batalha

### 2.1 Separação entre cliente, servidor e dados

O sistema de batalha deve ser dividido em três grandes áreas:

- **Cliente**
  - Renderiza arena, Pokémon, HUD, indicadores, animações e interação do jogador.
  - Monta a intenção da jogada do jogador.
  - Envia inicialização e ações preparadas para o servidor por um único arquivo de comunicação.
  - Lê o log retornado pelo servidor e reproduz visualmente os acontecimentos.

- **Servidor**
  - É a autoridade real da batalha.
  - Armazena o estado oficial da partida.
  - Valida ações.
  - Ordena e executa ações.
  - Aplica dano, cura, efeitos, movimentação, troca, clima e alterações de arena.
  - Gera logs e diffs confiáveis da rodada.

- **Dados**
  - Armazenam a definição dos ataques, propriedades de alvos, efeitos visuais, custos, estilo, descrição e regras de funcionamento.
  - O CSV de ataques contém a definição mais direta e visual.
  - O JSON de propriedades dos ataques contém o comportamento mais complexo.

### 2.2 Cliente não deve ser a fonte da verdade da batalha

O cliente pode prever, exibir, animar e montar jogadas, mas o resultado oficial vem do servidor.

A vida, energia, posição, efeitos, clima, morte, troca e resultado final da batalha devem ser definidos pelo servidor e refletidos no cliente por meio do log/diff da rodada.

### 2.3 Comunicação client-servidor passa por um único arquivo no cliente

Toda comunicação entre cliente e servidor relacionada à batalha deve passar por:

```text
Codigo/Server/ServerBatalha.py
```

Esse arquivo funciona como adaptador de comunicação do cliente. Nenhum outro arquivo do cliente deve sair chamando diretamente `GerenciadorPartidas`, `Partida`, `RodadorTurno` ou qualquer classe interna da batalha no servidor.

Nesta versão inicial, esse arquivo precisa expor três rotas/chamadas conceituais:

1. **Inicialização de batalha**
   - Envia ao servidor os dados necessários para criar/registrar a batalha.
   - Usada pelo `InicializadorBatalha`.

2. **Envio de jogada**
   - Envia ao servidor as ações preparadas pelo jogador.
   - Usada pelo `ControladorBatalha`/`MontadorJogadas` quando o jogador clica em pronto.

3. **Finalização de batalha**
   - Envia ou solicita ao servidor o encerramento da batalha quando o fluxo oficial terminar ou quando houver fuga.
   - Usada pelo `FinalizadorBatalha`/`ControladorBatalha` para devolver o jogador ao fluxo normal sem misturar regra de finalização no HUD.

As três chamadas passam pelo arquivo de rotas no servidor antes de chegarem à lógica real da batalha.

Fluxo obrigatório:

```text
Cliente
  Codigo/ModulosBatalha/InicializadorBatalha.py
  Codigo/ModulosBatalha/ControladorBatalha.py
        ↓
  Codigo/Server/ServerBatalha.py
        ↓
Servidor
  arquivo de rotas de batalha do servidor
        ↓
  SimuladorServerJogo/Batalha/GerenciadorPartidas.py
        ↓
  SimuladorServerJogo/Batalha/Partida.py
```

### 2.4 Exceção temporária proibida: importação direta do servidor no inicializador

Como exceção provisória, o arquivo `InicializadorBatalha` do cliente poderá importar funções do servidor para gerar/materializar Pokémon selvagens.

Essa exceção envolve:

```text
SimuladorServerJogo/Gerais/Geradores/GeradorPokemon.py
```

Funções envolvidas:

- `GerarPokemon`
- `MaterializarPokemon`

Isso é considerado uma solução proibida no desenho ideal, porque mistura responsabilidades entre cliente e servidor. Porém, nesta fase inicial, será aceito para não aumentar a complexidade antes da estrutura principal estar pronta.

A exceção deve ficar bem isolada no `InicializadorBatalha`. Ela não autoriza outros arquivos do cliente a importar livremente arquivos internos do servidor.

### 2.5 Confronto é o foco inicial

Tipos conceituais de batalha:

- **Confronto**
  - Batalha contra Pokémon selvagem encontrado no mundo.
  - Pode envolver um Pokémon selvagem sozinho ou um bando.
  - É o foco da primeira implementação.

- **Treinador**
  - Batalha contra NPC treinador.
  - Deve ser prevista pela arquitetura, mas não aprofundada nesta etapa.

- **PVP**
  - Batalha contra outro jogador.
  - Deve ser prevista pela arquitetura, mas não é prioridade nesta etapa.

---

### 2.6 Rodada, passos, ações e autoridade do servidor

#### Atualização v5 — rodada, passo e tick

Definições fechadas:

- `rodada`: conjunto de jogadas recebidas dos lados e resolvidas como um ciclo lógico.
- `passo`: execução de uma única ação ordenada pelo `RodadorTurno`.
- `tick`: unidade apenas de animação/simulação visual no cliente, usada para controlar ritmo, acelerar ou desacelerar a reprodução dos eventos já resolvidos.

A lógica oficial da batalha não deve depender de tick visual. O servidor resolve em passos; o cliente anima em ticks.


A resolução da rodada no servidor funciona em **passos**.

Regra central:

```text
1 passo = 1 ação executada pelo RodadorTurno
```

Fluxo conceitual de cada passo:

1. O `RodadorTurno` pega a próxima ação já validada e ordenada pelo `ColetorAcoes`.
2. Se a ação for ataque, calcula a chance de acerto por alvo usando acurácia, assertividade e velocidade relativa.
3. Antes de decidir se o ataque acerta ou falha, roda o **execute de alvificação**, quando o ataque possuir esse tipo de execute.
4. Depois da alvificação, define quais alvos foram atingidos.
5. Para os alvos atingidos, chama o **execute principal** do ataque.
6. O execute principal chama métodos oficiais do `PokemonBatalha`, como `AplicarDano`, `ReceberDano`, `AplicarEfeito`, `ReceberEfeito`, `Mover`, `Trocar`, `GanharEnergia` etc.
7. Os métodos oficiais do Pokémon alteram o estado real da partida e disparam flags quando necessário.
8. Ao final de cada passo, o sistema roda `Verificar` nos Pokémon relevantes, e preferencialmente em todos os Pokémon/construtos da partida para manter consistência.

Resumo obrigatório:

```text
RodadorTurno roda ações em passos.
Ações verificam assertividade/acerto.
Executes aplicam a lógica do ataque.
Executes chamam métodos do PokemonBatalha.
Métodos mudam Pokémon/partida e disparam flags.
Verificar roda no fim de cada passo.
```

### 2.7 Executes, flags e grupos de ativação

#### Atualização v5 — grupos relativos e neutralidade do servidor

No cliente, a UI pode falar em aliado/inimigo porque está desenhando do ponto de vista do jogador.

No servidor, entretanto, a regra deve ser neutra:

- cada time/lado possui `lado_id`;
- relações devem ser calculadas por comparação de `lado_id`;
- evitar nomes fixos como `inimigo` e `aliado` como regra persistida no servidor;
- quando uma propriedade precisar indicar relação, preferir termos como:
  - `self`;
  - `mesmo_lado`;
  - `lado_oposto`;
  - `qualquer_lado`;
  - `todos`.

Os nomes antigos `aliado` e `inimigo` podem aparecer em texto de HUD, comentários visuais ou adaptação client-side, mas não devem ser a base estrutural do servidor.


Todos os ataques possuem um **execute principal**.

Além dele, um ataque pode possuir:

- **executes periféricos**;
- **execute de alvificação**.

#### Execute principal

É a função principal do ataque. Normalmente causa dano, cura, aplica efeito, move, troca, cria barreira, muda clima ou altera arena.

Ele só é chamado para os alvos que realmente forem atingidos, salvo exceções explícitas do ataque.

#### Execute de alvificação

É um execute especial que roda **antes** da definição final de acerto/falha.

Ele existe para ataques que mexem diretamente com a própria alvificação, com acurácia, assertividade, seleção de alvos ou chance de acerto.

Regra:

```text
execute de alvificação roda antes de decidir se o ataque acerta
```

#### Executes periféricos

São executes extras que não representam o efeito principal do ataque, mas podem ser ativados por flags durante o curso da ação.

Exemplo conceitual:

- Um ataque causa dano como execute principal.
- Se esse dano matar o alvo, um execute periférico com flag `AoMatar` ou `AoMorrer` é testado.
- Esse execute periférico pode curar o usuário, aplicar atributo, gerar energia ou disparar qualquer outro efeito especial.

#### Flags

Flags são pontos de ativação ao longo dos métodos oficiais do servidor.

Exemplos de flags:

- `AoCurar`
- `AoReceberCura`
- `AoAplicarDano`
- `AoReceberDano`
- `AoMatar`
- `AoMorrer`
- `AoGanharEnergia`
- `AoMover`
- `AoTrocar`
- `AoAplicarEfeito`
- `AoReceberEfeito`

As flags existem principalmente para passivas de itens, passivas de habilidades e executes periféricos de ataques.

#### Grupos de ativação

Cada passiva/execute testável por flag deve declarar um grupo.

Grupos oficiais iniciais no servidor:

- `self`
  - Só testa quando o evento envolve o próprio Pokémon que possui a passiva/execute.

- `mesmo_lado`
  - Testa quando o evento envolve um Pokémon do mesmo `lado_id`.

- `lado_oposto`
  - Testa quando o evento envolve um Pokémon de outro `lado_id`.

- `qualquer_lado`
  - Testa quando o evento envolve qualquer Pokémon relevante da partida.

- `todos`
  - Sinônimo conceitual para varreduras gerais quando a regra precisar atingir todos os envolvidos.

Exemplo:

```text
Passiva: ganhar Atk ao receber cura.
Flag: AoReceberCura.
Grupo: self.
Resultado: só testa quando o próprio Pokémon com essa passiva recebe cura.
```

Outro exemplo:

```text
Passiva: ganhar Atk quando qualquer Pokémon do mesmo lado recebe cura.
Flag: AoReceberCura.
Grupo: mesmo_lado.
Resultado: quando um Pokémon do mesmo `lado_id` recebe cura, essa passiva entra na lista de executes testados.
```

#### Lista de executes testados

Sempre que um método oficial do `PokemonBatalha` é chamado, ele deve montar ou receber uma lista de executes/passivas testáveis naquele contexto.

Essa lista pode incluir:

- passivas do próprio Pokémon;
- passivas de Pokémon do mesmo lado;
- passivas de Pokémon de lados opostos;
- passivas de itens da `Build`;
- passivas de habilidades;
- executes periféricos do ataque atual, alocados artificialmente no contexto da ação.

Assim, o sistema consegue criar ataques muito variados sem codificar todos os casos diretamente no `RodadorTurno`.

---

### 2.8 Identificadores oficiais da batalha

Toda entidade relevante criada dentro de uma batalha deve receber ID único gerado pelo servidor. O cliente pode enviar IDs originais do inventário/mundo, mas o ID oficial da partida nasce no servidor.

Regra inicial de prefixos:

| Prefixo | Entidade |
|---|---|
| `0` | Pokémon de batalha |
| `1` | Ataque instanciado na batalha |
| `2` | Ação |
| `3` | Registro/evento individual do log |
| `4` | Construto |
| `5` | Time/lado |
| `6` | Log de rodada |

Regras específicas:

- Pokémon: o primeiro dígito é `0`; o segundo dígito representa o ID do time/lado; os demais indicam a ordem dentro da partida.
- Time/lado: o primeiro dígito é `5`; o segundo identifica o time. No modelo inicial 1x1, os times podem ser `50` e `51`.
- Ataque, ação, registro, construto e log também devem receber IDs próprios.
- IDs da batalha não substituem IDs originais persistentes do jogador; eles existem para a partida, log, replay visual e validação.
- O pacote serializado deve sempre diferenciar `id_original` de `id_batalha` quando ambos existirem.

## 3. Modelo oficial de atributos do `PokemonBatalha`

Todo `PokemonBatalha` deve separar claramente **atributos padrão modificáveis** de **estados atuais**.

Essa separação é importante porque alguns valores representam a capacidade/base do Pokémon, enquanto outros representam a situação momentânea dele dentro da batalha.

### 3.1 Atributos padrão

Os atributos abaixo são os atributos regulares do Pokémon na batalha.

Todos eles seguem a mesma regra de composição:

```text
valor final = valor base + variação temporária + variação permanente/fixa
```

Camadas:

- **Base**
  - Valor original vindo do Pokémon materializado ou da regra de criação do Pokémon.

- **Variação temporária**
  - Resetada a cada `Verificar`.
  - Reaplicada por efeitos ativos, condições, buffs, debuffs, clima, arena, itens ou passivas temporárias.

- **Variação permanente/fixa**
  - Não é resetada normalmente.
  - Representa alterações fixas durante a batalha, quando existirem.

Lista oficial de atributos padrão:

| Atributo | Significado |
|---|---|
| `Vida` | Vida máxima do Pokémon. |
| `Atk` | Ataque físico/normal. |
| `SpA` | Ataque especial. |
| `Def` | Defesa contra dano normal/físico. |
| `SpD` | Defesa especial. |
| `Mag` | Magia, usada em aplicação e defesa de efeitos. |
| `Ene` | Energia, usada para recuperação de energia. |
| `Vel` | Velocidade base. |
| `Per` | Perfuração. |
| `Int` | Inteligência. |
| `Vamp` | Vampirismo. |
| `CrC` | Chance de crítico. |
| `CrD` | Dano crítico adicional. |
| `Dur` | Durabilidade. |
| `Amp` | Amplificação. |
| `EneM` | Energia máxima. |
| `Acuracia` | Capacidade de acertar outros Pokémon. |
| `Assertividade` | Capacidade de outros Pokémon acertarem este Pokémon. |

Valores base padrão especiais:

- `Dur`, `Amp` e `Vamp` começam em `0` para todos os Pokémon, salvo regra explícita em contrário.
- `Acuracia` e `Assertividade` começam em `100` para todos os Pokémon, pois são valores percentuais.
- `CrC`, `CrD` e demais atributos podem vir da espécie, materialização, build ou regra futura, mas devem seguir a mesma estrutura de base + variação temporária + variação permanente.

Observações importantes:

- `Vida` representa a **vida máxima**, não a vida atual.
- `EneM` representa a **energia máxima**, não a energia atual.
- `Ene` é o atributo usado para recuperação/geração de energia, não o estoque atual de energia.
- Alterações temporárias e permanentes devem ser armazenadas separadamente para permitir recálculo limpo no `Verificar`.

### 3.2 Estados atuais

### Atualização v7 — efeitos formais, limite total e duração

Regras fechadas na v7:

- O limite de efeitos formais é total: cada Pokémon pode ter no máximo 4 efeitos formais simultâneos, somando positivos e negativos.
- Ao tentar aplicar um 5º efeito formal, o sistema bloqueia a aplicação e registra evento no log, como `efeito_bloqueado_por_limite`.
- O 5º efeito não substitui automaticamente nenhum efeito existente.
- Efeitos repetidos continuam podendo stackar inicialmente, mas cada instância ocupa um dos 4 slots, salvo regra futura explícita do próprio efeito.
- A duração dos efeitos formais decrementa no fim de cada passo global.
- Estados transitórios de resolução, como `entrou_na_rodada`, `acao_cancelada`, `protegido_nesta_instancia` ou equivalentes, não contam como efeitos formais e não ocupam slot.


### Atualização v5 — vida atual, energia atual e efeitos simultâneos

`Vida` continua sendo vida máxima. `VidaAtual` é um único estado atual separado e não deve ser tratada como variação temporária ou permanente.

Regras fechadas:

- No início, `VidaAtual` espelha a vida atual real do Pokémon. Para selvagem recém-gerado, normalmente começa cheia.
- Se `Vida` máxima aumentar durante a batalha, `VidaAtual` deve aumentar proporcionalmente.
- Cura pode levar `VidaAtual` até a `Vida` máxima final atual, não apenas até a vida que o Pokémon tinha ao entrar.
- Dano desgasta `VidaAtual`; não entra em `variacoes_temporarias` nem em `variacoes_permanentes`.
- `EnergiaAtual` começa em 75% de `EneM` no servidor, salvo regra explícita futura.
- Um Pokémon pode manter no máximo 4 efeitos simultâneos.
- Efeitos repetidos devem **stackar** inicialmente, tanto positivos quanto negativos, respeitando o limite de efeitos e as regras futuras do próprio efeito.


Os campos abaixo não são apenas atributos padrão. Eles representam o estado atual do Pokémon durante a partida.

Lista oficial de estados atuais:

- `VidaAtual`
- `EnergiaAtual`
- `BarreiraAtual`
- Efeitos positivos ativos.
- Efeitos negativos ativos.
- `Build`, ou lista de itens equipáveis/equipados relevantes para a batalha.
- Posição.
- Estado vivo/morto.

Regras de leitura:

- `VidaAtual` deve ser comparada com o atributo final `Vida`.
- `EnergiaAtual` deve ser comparada com o atributo final `EneM`.
- `BarreiraAtual` representa proteção acumulada no momento, não um atributo padrão do Pokémon.
- Efeitos positivos e negativos ativos devem ser considerados na reaplicação das variações temporárias durante o `Verificar`.
- A posição deve indicar onde o Pokémon está na arena ou se ele está na reserva.
- O estado vivo/morto deve ser derivado e validado principalmente a partir de `VidaAtual`, mas pode ser armazenado para facilitar leitura, serialização e logs.

---

## 4. Mapa inicial de arquivos e áreas

### Atualização v5 — nomes reais e criação de arquivos novos

O adaptador do cliente deve ficar em `Codigo/Server/ServerBatalha.py`.

A pasta `SimuladorServerJogo/Batalha/` será criada para a implementação nova. Arquivos legados que não tenham relação com o novo sistema não devem ser considerados fonte de verdade nem receber compatibilidade artificial.

`CenaCombate` ou a cena equivalente continua sendo apenas a cena da batalha dentro do sistema normal de cenas do jogo. A lógica nova deve ser organizada nos controladores e módulos de batalha descritos aqui.


Estrutura conceitual inicial:

```text
Codigo/
  Server/
    ServerBatalha.py

  ModulosBatalha/
    InicializadorBatalha.py
    Arena.py
    PokemonBatalha.py
    PlayerBatalha.py
    ElementosHudBatalha.py
    MontadorJogadas.py
    IndicadorAtaque.py
    ControladorBatalha.py
    LeitorLogs.py
    ControladorAnimacoes.py
    FinalizadorBatalha.py
    IA/
      ControladorIA.py

  ModulosGerais/
    PokemonAnimator.py

Dados/
  CSV de ataques
  JSON de propriedades dos ataques

SimuladorServerJogo/
  Rotas/
    RotasBatalha.py

  Batalha/
    GerenciadorPartidas.py
    Partida.py
    PokemonBatalha.py
    ColetorAcoes.py
    RodadorTurno.py
    ConstrutorLog.py
    FraquezasResistencia.py
    Construto.py

  Logica/
    Executes/
      ExecuteAtaques.py
      PassivaAtaques.py
      PassivaItens.py

  Gerais/
    Geradores/
      GeradorPokemon.py
```

Os nomes acima representam a organização lógica inicial. Caso algum nome real do projeto já exista com leve diferença, a implementação deve respeitar o padrão já usado no repositório, evitando criar duplicatas desnecessárias.

---

# CLIENTE

---

## 5. `Codigo/Server/ServerBatalha.py`

### Atualização v5 — contrato fechado do adaptador

O arquivo correto é `Codigo/Server/ServerBatalha.py`.

Ele deve expor três chamadas públicas conceituais:

1. `inicializar_batalha(dados_inicializacao)`;
2. `enviar_jogada(id_partida, lado_id, jogada)`;
3. `finalizar_batalha(id_partida, lado_id=None, motivo=None, dados=None)`.

Mesmo em modo local, esse arquivo deve simular comunicação real por JSON/dicionários serializáveis. Ele pode chamar a camada do servidor por ser a ponte oficial, mas não deve entregar objetos Python complexos diretamente ao cliente.

Formato geral das respostas:

- Inicialização:
  - deve retornar `status`, `mensagem`, `id_partida`, `estado_inicial`, `avisos` e `erros`;
  - não deve retornar `log`;
  - não deve retornar `resultado`.

- Envio de jogada:
  - pode retornar `status`, `mensagem`, `id_partida`, `estado_batalha`, `log`, `avisos` e `erros`;
  - `resultado` fica dentro do `log`, junto com `historico`.

- Finalização:
  - deve retornar `status`, `mensagem`, `id_partida`, `estado_finalizacao`, `avisos` e `erros`;
  - não deve retornar `log`;
  - não deve retornar `resultado`, porque resultado oficial de batalha pertence ao log da rodada/finalização lógica.

Se uma ação falhar durante a rodada por erro ou invalidação, isso deve virar registro no log e a rodada segue sem aquela ação. A jogada inteira não deve ser cancelada só porque uma ação falhou.


### Responsabilidade principal

Centralizar toda a comunicação do cliente com o servidor para o sistema de batalha.

Esse arquivo é uma camada de acesso. Ele não monta HUD, não executa dano, não calcula rodada e não interpreta animações. Ele apenas recebe dados do cliente, chama a rota correta no servidor e devolve a resposta ao cliente em formato estável.

### Classe/funções esperadas

Pode ser implementado como funções soltas ou como uma classe de serviço, conforme o padrão do projeto. Conceitualmente, deve fornecer apenas a API pública de batalha do cliente.

### `selfs`/estado relevante, caso seja classe

- `self.conexao` ou referência equivalente para comunicação com o servidor.
- `self.rotas_batalha` ou adaptador interno para acessar as rotas.
- `self.timeout_padrao`, se o projeto usar timeout.
- `self.ultima_resposta`, apenas se já houver padrão de debug no projeto.

### Métodos relevantes

#### `inicializar_batalha(dados_inicializacao)`

Responsável por enviar ao servidor a solicitação de criação da batalha.

Entrada conceitual:

- tipo da batalha, inicialmente `Confronto`;
- time do jogador;
- time selvagem;
- posições iniciais sugeridas ou dados necessários para o servidor validar posições;
- contexto mínimo da arena;
- identificadores necessários do jogador e do encontro selvagem.

Saída conceitual:

- `id_partida`;
- estado inicial oficial da partida;
- dados dos lados;
- Pokémon ativos e reservas;
- estado inicial da arena;
- rodada inicial;
- qualquer aviso de erro/validação.

Regras:

- Não deve criar `Partida` diretamente no cliente.
- Não deve chamar `GerenciadorPartidas` diretamente se existir rota de servidor.
- Deve passar pelo arquivo de rotas do servidor.

#### `enviar_jogada(id_partida, lado_id, jogada)`

Responsável por enviar ao servidor as ações preparadas pelo jogador.

Entrada conceitual:

- `id_partida`;
- `lado_id` do jogador/lado que está enviando;
- lista de ações preparadas;
- rodada em que a jogada foi montada;
- dados mínimos de validação.

Saída conceitual:

- confirmação de recebimento;
- estado de espera, se o outro lado ainda não jogou;
- log da rodada, se a rodada já puder ser resolvida;
- erros de validação, se a jogada for inválida.

Regras:

- Não deve resolver a rodada no cliente.
- Não deve alterar vida, energia, posição ou efeitos por conta própria.
- Apenas encaminha a jogada e devolve ao cliente a resposta oficial.

---

#### `finalizar_batalha(id_partida, lado_id=None, motivo=None, dados=None)`

Responsável por encaminhar o encerramento da batalha ao servidor/rota de batalha.

Usos iniciais:

- encerramento normal após log final;
- fuga;
- limpeza de partida finalizada;
- retorno do jogador ao mundo.

Saída conceitual:

- confirmação de finalização;
- estado de finalização;
- avisos/erros.

Regras:

- Não deve recalcular vencedor, XP ou estado de Pokémon.
- Não deve gerar log novo por conta própria.
- Apenas encaminha a solicitação e devolve a resposta oficial.

## 6. `Codigo/ModulosBatalha/InicializadorBatalha.py`

### Atualização v5 — confronto, bando e posições

Regras fechadas para o inicializador:

- O tipo inicial continua sendo `Confronto`.
- O Pokémon selvagem encontrado sempre participa e entra como ativo.
- O bando pode ter reserva, respeitando o limite total de 6 Pokémon como uma equipe padrão.
- O limite de ativos iniciais é 3 Pokémon por lado.
- O bando respeita estágio evolutivo menor ou igual ao Pokémon base.
- Formas especiais, Mega, Ultra, Gigantamax e equivalentes não devem ser geradas no bando.
- Pokémon adicionais do bando devem ter nível parecido com o Pokémon encontrado, com variação de até 20%.
- O máximo de 3 Pokémon iguais conta também o Pokémon base encontrado.
- O jogador pode iniciar com time incompleto, desde que exista pelo menos 1 Pokémon apto.
- Pokémon apto, nesta fase, significa apenas `vida_atual > 0`.
- As posições iniciais oficiais são definidas pelo cliente e enviadas no pacote de inicialização.
- O clima do mundo não entra automaticamente na batalha.
- A dimensão/contexto do mundo entra para geração visual da arena. Por enquanto, dimensões sem contexto visual próprio podem gerar fundo preto com os botões/áreas da arena.


### Responsabilidade principal

Inicializar a batalha no cliente, montar os dados iniciais do confronto e chamar `Codigo/Server/ServerBatalha.py` para registrar/criar a partida no servidor.

Esse arquivo é o ponto de entrada do sistema de batalha no cliente.

### `selfs`/estado relevante

- `self.tipo_batalha`
  - Tipo conceitual da batalha: `Confronto`, `Treinador` ou `PVP`.

- `self.pokemon_encontrado`
  - Pokémon selvagem que iniciou o confronto.

- `self.time_jogador`
  - Lista de Pokémon escolhidos para o lado do jogador.

- `self.time_inimigo`
  - Lista de Pokémon selvagens do confronto/bando.

- `self.contexto_mundo`
  - Dados do mundo necessários para montar a arena.

- `self.posicoes_iniciais`
  - Posições iniciais sugeridas para os Pokémon ativos.

- `self.server_batalha`
  - Referência ao adaptador `Codigo/Server/ServerBatalha.py`.

- `self.id_partida`
  - ID recebido do servidor depois da criação da partida.

### Métodos relevantes

#### `inicializar_confronto(pokemon_encontrado, jogador, contexto_mundo)`

Fluxo principal do confronto.

Passos:

1. Define `self.tipo_batalha = Confronto`.
2. Guarda o Pokémon encontrado.
3. Monta o time selvagem.
4. Monta o time do jogador.
5. Gera posições iniciais.
6. Monta o pacote de inicialização.
7. Chama `ServerBatalha.inicializar_batalha(...)`.
8. Recebe o estado oficial inicial.
9. Cria/aciona o `ControladorBatalha` no cliente.

#### `montar_time_selvagem(pokemon_base)`

Monta o time do lado selvagem.

Regras:

- O Pokémon base do confronto sempre participa.
- O bando pode conter Pokémon da mesma linhagem.
- Os Pokémon gerados devem ter estágio evolutivo menor ou igual ao estágio do Pokémon encontrado.
- Exemplo: se o Pokémon encontrado é `Charmeleon`, o bando pode conter `Charmander` e `Charmeleon`, mas não `Charizard`.
- O limite máximo de uma equipe é 6 Pokémon.
- O gerador de bando só pode gerar até 3 Pokémon iguais.
- A geração do bando deve respeitar o limite total de 6 membros.
- Os Pokémon gerados para o bando devem ser materializados antes de serem enviados para a batalha.

#### `buscar_linhagem_compativel(pokemon_base)`

Consulta a tabela CSV de Pokémon em `Dados` para localizar Pokémon da mesma linhagem com estágio menor ou igual ao Pokémon base.

Saída esperada:

- lista de espécies possíveis para o bando;
- dados necessários para chamar `GerarPokemon` e `MaterializarPokemon`.

#### `gerar_membros_bando(pokemon_base, especies_possiveis)`

Usa a exceção temporária de importação do servidor para gerar/materializar os Pokémon adicionais.

Funções temporariamente permitidas:

- `GerarPokemon`
- `MaterializarPokemon`

Regra importante:

- Essa exceção deve ficar isolada aqui.

#### `montar_time_jogador(jogador)`

Procura uma equipe disponível para o jogador.

Ordem de busca:

1. Procurar um time completo do jogador.
2. Validar se os Pokémon do time estão aptos.
3. Caso não exista time completo apto, procurar um time incompleto.
4. Caso também não exista time incompleto adequado, procurar diretamente na lista geral de Pokémon do jogador.
5. Selecionar os primeiros Pokémon aptos encontrados.
6. Montar um time temporário com esses Pokémon.

Um Pokémon é considerado apto quando:

- possui vida maior que 0;
- está em condição mínima de entrar em batalha.

#### `pokemon_esta_apto(pokemon)`

Valida se um Pokémon pode entrar na batalha.

Critérios iniciais:

- vida maior que 0;
- não estar bloqueado por estado externo que impeça batalha, se existir.

#### `gerar_posicoes_iniciais(arena, time_jogador, time_inimigo)`

Define posições iniciais aleatórias para Pokémon ativos.

Regras:

- As posições devem ser escolhidas aleatoriamente dentro das áreas disponíveis da arena.
- Apenas Pokémon ativos começam posicionados nas áreas da arena.
- Pokémon da reserva ficam fora da arena, desenhados como banco/reserva.
- A escolha aleatória não deve colocar dois Pokémon na mesma área.

#### `montar_pacote_inicializacao()`

Cria o dicionário/estrutura enviada para `ServerBatalha.inicializar_batalha(...)`.

Deve conter:

- tipo da batalha;
- time do jogador;
- time selvagem;
- contexto da arena;
- posições iniciais;
- identificadores necessários.

---

## 7. `Codigo/ModulosBatalha/Arena.py`

### Atualização v5 — áreas, IDs e reserva

A arena usa áreas quadradas discretas para seleção e validação da jogada.

IDs oficiais das áreas no cliente:

- lado do jogador/aliado visual: `A1` até `A9`;
- lado oponente/inimigo visual: `I1` até `I9`.

Esses nomes são úteis para UI e montagem visual. Ao serializar para o servidor, a área deve continuar vinculada ao `lado_id` real, para não prender a lógica oficial aos nomes aliado/inimigo.

Regras fechadas:

- As 18 áreas são quadradas.
- A arena conhece também a região visual de reserva/banco.
- Pokémon da reserva podem ser desenhados fora das 18 áreas, no canto/lateral da arena.
- A reserva pertence ao sistema da arena para fins de clique, arraste e troca, mesmo que visualmente pareça um painel.
- Existem efeitos que podem afetar áreas específicas.
- O servidor também precisa conhecer as áreas para validar alvo, ocupação, movimento, troca de posição e efeitos de área.


### Responsabilidade principal

Representar visualmente e logicamente o contexto da arena no cliente.

A arena usa um recorte do mundo como contexto visual, mas cria uma área central própria para a batalha.

### `selfs`/estado relevante

- `self.contexto_tiles`
  - Recorte de `80 x 40 tiles` vindo do mundo.

- `self.area_central`
  - Centro livre de `40 x 20 tiles`.

- `self.areas_aliadas`
  - Matriz/lista com 9 áreas do lado aliado.

- `self.areas_inimigas`
  - Matriz/lista com 9 áreas do lado inimigo.

- `self.areas_todas`
  - Lista unificada das 18 áreas selecionáveis.

- `self.ocupacao_areas`
  - Mapeamento entre área e Pokémon ocupante.

- `self.camera`
  - Referência/estado de câmera móvel usada na batalha.

- `self.zoom`
  - Zoom atual da câmera, se aplicável.

### Métodos relevantes

#### `criar_contexto_mundo(mundo, posicao_origem)`

Obtém o contexto visual de `80 x 40 tiles` ao redor do ponto em que a batalha foi iniciada.

#### `limpar_centro_arena()`

Garante que o centro de `40 x 20 tiles` fique sem estruturas naturais como árvores, pedras, plantas ou obstáculos visuais que atrapalhem a batalha.

#### `criar_areas_batalha()`

Cria dois lados de áreas.

Cada lado possui:

```text
3 x 3 áreas
```

Total:

- 9 áreas aliadas;
- 9 áreas inimigas;
- 18 áreas selecionáveis.

#### `desenhar(surface)`

Renderiza o contexto visual da arena, respeitando câmera e zoom.

#### `desenhar_areas(surface)`

Desenha as áreas selecionáveis e seus estados visuais.

#### `area_em_posicao_mouse(pos_mouse)`

Converte posição do mouse para uma área selecionável, se houver.

#### `obter_area_por_id(area_id)`

Retorna a área correspondente a um ID.

#### `area_esta_ocupada(area_id)`

Informa se uma área está ocupada por Pokémon.

#### `pokemon_na_area(area_id)`

Retorna o Pokémon que ocupa a área, quando existir.

#### `atualizar_ocupacao(pokemons)`

Atualiza a ocupação das áreas com base no estado recebido do servidor ou no estado visual consolidado.

#### `posicao_mundo_para_tela(posicao_mundo)`

Converte posição de mundo/arena para posição de tela.

#### `posicao_tela_para_mundo(posicao_tela)`

Converte posição de tela para posição de mundo/arena.

### Regra importante

A arena não deve decidir resultado de ataque, dano, cura ou efeito. Isso é responsabilidade do servidor.

---

## 8. `Codigo/ModulosBatalha/PokemonBatalha.py`

### Atualização v5 — espelho completo e prévia de energia

Mesmo no cliente, `PokemonBatalha` deve manter as estruturas de atributos base, variações temporárias, variações permanentes e atributos finais, porque a ficha/visualização precisa refletir o estado completo recebido do servidor.

Regras fechadas:

- O cliente pode prever energia para bloquear montagem de ações.
- A previsão de energia deve aparecer tanto na ficha quanto na barra do próprio Pokémon.
- O gasto previsto deve piscar/brilhar em branco.
- Se a ação ultrapassar a energia disponível prevista, a barra deve indicar branco avermelhado e impedir a preparação por energia.
- O cliente não deve prever vida/dano como regra local.
- Pokémon morto executa animação de morte/desmaio e depois some da arena.
- Pokémon na reserva fica no canto/lateral esperando entrada; ele entra quando uma ação de troca for preparada por arraste até ele.


### Responsabilidade principal

Representar o Pokémon da batalha no cliente.

No cliente, `PokemonBatalha` é principalmente um container visual e de estado local refletido do servidor. Ele não deve ser a autoridade real das regras de batalha.

### `selfs`/estado relevante

- `self.id_batalha`
  - ID do Pokémon dentro da partida.

- `self.id_original`
  - ID do Pokémon original do jogador/servidor, quando existir.

- `self.nome`
- `self.especie`
- `self.lado_id`
- `self.time_id`
- `self.ativo`
- `self.reserva`
- `self.vivo`

- `self.atributos`
  - Atributos finais recebidos do servidor.

- `self.estados_atuais`
  - `VidaAtual`, `EnergiaAtual`, `BarreiraAtual`, efeitos, posição e vivo/morto.

- `self.vida_atual`
- `self.energia_atual`
- `self.barreira_atual`

- `self.efeitos_positivos`
- `self.efeitos_negativos`
- `self.build`

- `self.posicao`
  - Área da arena ou posição de reserva.

- `self.frames`
  - Frames carregados via função auxiliar.

- `self.frame_atual`
- `self.tempo_animacao`
- `self.animator`
  - Referência ao `PokemonAnimator` ou estado de animação associado.

### Métodos relevantes

#### `from_serializado(dados)`

Cria ou atualiza o objeto client-side a partir dos dados enviados pelo servidor.

#### `serializar()`

Gera uma versão simples do estado local quando necessário para debug, HUD ou comunicação indireta. O cliente não deve usar isso para inventar regra oficial.

#### `atualizar_por_diff(diff)`

Aplica alterações recebidas do resultado/log do servidor.

Pode atualizar:

- vida atual;
- energia atual;
- barreira;
- efeitos;
- posição;
- estado vivo/morto;
- atributos finais.

#### `carregar_frames()`

Usa função auxiliar do projeto para carregar frames do Pokémon.

Não deve duplicar lógica pesada de carregamento se já houver módulo apropriado.

#### `atualizar_animacao(dt)`

Atualiza o frame visual base do Pokémon.

#### `desenhar(surface, camera)`

Desenha o Pokémon quando ele está ativo na arena.

#### `desenhar_reserva(surface, posicao_hud)`

Desenha o Pokémon fora da arena, no banco/reserva.

#### `desenhar_barras(surface)`

Desenha barra de vida, energia e barreira quando aplicável.

#### `desenhar_efeitos(surface)`

Desenha círculos/ícones de efeitos positivos e negativos acima do Pokémon.

#### `esta_ativo()`

Retorna se o Pokémon está ativo na arena.

#### `esta_na_reserva()`

Retorna se o Pokémon está no banco/reserva.

#### `esta_vivo()`

Retorna estado vivo/morto conforme estado recebido do servidor.

### Regra importante

O cliente não recalcula a regra oficial desses valores. Ele apenas reflete o estado vindo do servidor e anima as mudanças recebidas em log/diff.

---

## 9. `Codigo/ModulosGerais/PokemonAnimator.py`

### Atualização v5 — animação por Pokémon e ticks visuais

O `PokemonAnimator` deve ser associado ao Pokémon. Projéteis e cartuchos podem ser renderizados por ele mesmo.

A leitura visual dos acontecimentos deve usar um modelo de ticks de animação no cliente. Isso permite controlar futuramente velocidade de reprodução, aceleração e desaceleração sem mudar a lógica oficial da batalha.


### Responsabilidade principal

Controlar animações relacionadas aos Pokémon.

Esse módulo é compartilhado e deve concentrar as animações visuais envolvendo Pokémon, evitando espalhar efeitos visuais diretamente em `PokemonBatalha`, `LeitorLogs` ou `ControladorAnimacoes`.

### `selfs`/estado relevante

- `self.pokemon`
  - Pokémon visual associado, quando o animator for por instância.

- `self.animacao_atual`
- `self.fila_animacoes`
- `self.tempo_animacao`
- `self.estado_visual`
- `self.cartuchos_ativos`
- `self.projeteis_ativos`

### Métodos relevantes

#### `animar_morrer(pokemon)`

Executa animação de morte/desmaio.

#### `animar_tomar_dano(pokemon, valor=None)`

Executa animação de dano.

#### `animar_receber_cura(pokemon, valor=None)`

Executa animação de cura.

#### `exibir_cartucho(pokemon, texto, tipo)`

Exibe número ou mensagem flutuante.

Usos:

- dano;
- cura;
- ganho/perda de energia;
- texto especial de efeito.

#### `animar_lancar_projetil(origem, destino, sprite=None)`

Executa animação de projétil.

#### `animar_avanco(pokemon, destino)`

Executa animação de avanço.

#### `animar_salto(pokemon, destino)`

Executa animação de salto.

#### `animar_troca(pokemon_saida, pokemon_entrada)`

Executa animação visual de troca.

#### `animar_sofrer_ataque(pokemon, dados_evento)`

Executa animação mais genérica de sofrer ataque, caso o evento não caia em dano/cura simples.

#### `atualizar(dt)`

Atualiza animações em andamento.

#### `desenhar(surface)`

Desenha efeitos visuais próprios do animator, como projéteis e cartuchos.

### Regra importante

O `PokemonAnimator` não decide regra. Ele apenas executa a animação pedida pelo sistema de batalha.

---

## 10. `Codigo/ModulosBatalha/PlayerBatalha.py`

### Atualização v5 — seleção, arraste e bloqueio de input

Regras fechadas de input:

- Clicar na área de um Pokémon aliado ativo seleciona aquele Pokémon.
- Clicar em outro Pokémon troca a seleção.
- Clicar em área vazia seleciona a área vazia.
- Clicar no Pokémon já selecionado desseleciona e deixa nada selecionado.
- Pokémon inimigo/oponente pode ser selecionado para visualização, mas não permite selecionar ataques nem arrastar para mover.
- Arrastar Pokémon aliado ativo para área aliada livre prepara movimento.
- Arrastar Pokémon aliado ativo para área aliada ocupada troca a posição dos dois aliados.
- Arrastar Pokémon aliado ativo até Pokémon da reserva prepara troca.
- Arrastar para fora da arena sem cair em destino válido cancela e volta como se nada tivesse ocorrido.
- Clicar novamente no ataque selecionado cancela a seleção daquele ataque.
- `ESC` cancela primeiro a preparação/seleção atual; se não houver preparação, segue o comportamento normal da cena.
- Durante leitura/animação da rodada, não dá para fazer nada; Pokémon e ataque selecionados devem ser limpos.


### Responsabilidade principal

Controlar a interação do jogador com a batalha.

Esse arquivo deve lidar com inputs, keybinds e comandos do jogador durante a batalha.

### `selfs`/estado relevante

- `self.controlador`
  - Referência ao `ControladorBatalha`.

- `self.montador_jogadas`
- `self.hud`
- `self.arena`

- `self.pokemon_selecionado`
- `self.ataque_selecionado`
- `self.arrastando_pokemon`
- `self.estado_input`

- `self.input_bloqueado`
  - Verdadeiro durante leitura de log/animação/finalização.

### Métodos relevantes

#### `processar_evento(evento)`

Recebe eventos do Pygame/sistema de input e encaminha para métodos específicos.

#### `processar_clique(pos_mouse)`

Lida com clique em área, Pokémon, HUD, ficha, botão de pronto, botão de fugir etc.

#### `processar_mouse_down(pos_mouse)`

Inicia seleção ou arraste.

#### `processar_mouse_up(pos_mouse)`

Finaliza seleção, movimento, troca ou alvo de ataque.

#### `processar_movimento_mouse(pos_mouse)`

Atualiza prévias visuais do `MontadorJogadas` e `IndicadorAtaque`.

#### `processar_tecla(tecla)`

Lida com keybinds da batalha.

#### `selecionar_pokemon(pokemon)`

Seleciona um Pokémon e informa HUD/montador.

#### `selecionar_ataque(ataque)`

Seleciona um ataque na ficha do Pokémon.

#### `cancelar_selecao()`

Limpa seleção atual.

#### `confirmar_pronto()`

Solicita ao controlador o envio da jogada.

#### `tentar_fugir()`

Aciona o fluxo de fuga, quando a regra estiver definida.

#### `bloquear_input()` / `desbloquear_input()`

Controla se o jogador pode interagir durante leitura de log, animação ou finalização.

---

## 11. `Codigo/ModulosBatalha/ElementosHudBatalha.py`

### Atualização v5 — ficha, pronto e fuga

Regras fechadas de HUD:

- A ficha de Pokémon já existe e deve sofrer alteração leve.
- Na linha de atributos extras, onde antes apareciam escala/peso, agora devem aparecer `Assertividade` e `Acuracia`.
- A ficha usa ataques de `habilidade`.
- A ficha do Pokémon oponente pode ser mostrada, mas não permite selecionar ataque.
- O botão `Pronto` aparece durante montagem e pode enviar uma jogada sem ações.
- O painel de ações preparadas deve permitir remover ação, usando o botão já previsto/existente.
- A energia prevista deve aparecer na ficha e na barra do Pokémon.
- O botão de fugir funciona por cliques repetidos: cada clique escurece a tela; ela clareia naturalmente aos poucos; se o jogador clicar várias vezes rápido o suficiente para a tela ficar escura, a fuga conclui e volta ao mundo normal.


### Responsabilidade principal

Renderizar e organizar os elementos fixos da interface da batalha.

A batalha possui câmera móvel. Por isso, arena e Pokémon ativos são desenhados no mundo e sofrem influência de posição/zoom da câmera. O HUD fica acoplado à tela.

### `selfs`/estado relevante

- `self.controlador`
- `self.pokemon_selecionado`
- `self.ficha_pokemon`
- `self.botao_pronto`
- `self.botao_fugir`
- `self.barra_tempo`
- `self.texto_rodada`
- `self.paineis_acoes`
- `self.visualizador_logs`
- `self.estado_visivel`

### Métodos relevantes

#### `atualizar(dt)`

Atualiza estado visual de botões, barra de tempo, painéis e logs.

#### `desenhar(surface)`

Desenha todos os elementos fixos da interface.

#### `desenhar_ficha_pokemon(surface)`

Desenha a ficha do Pokémon selecionado.

Para Pokémon aliado ativo, a ficha deve permitir seleção de ataques.

#### `desenhar_botao_pronto(surface)`

Desenha o botão de pronto no canto inferior direito.

#### `desenhar_barra_tempo(surface)`

Desenha barra de tempo no canto superior esquerdo.

#### `desenhar_texto_rodada(surface)`

Mostra a rodada atual.

#### `desenhar_paineis_acoes(surface)`

Mostra as ações preparadas na lateral esquerda.

#### `desenhar_visualizador_logs(surface)`

Mostra acontecimentos da batalha na lateral direita.

#### `desenhar_botao_fugir(surface)`

Desenha botão de fugir no canto inferior esquerdo.

#### `set_pokemon_selecionado(pokemon)`

Atualiza a ficha conforme Pokémon selecionado.

#### `atualizar_acoes_preparadas(acoes)`

Atualiza painéis da lateral esquerda.

#### `adicionar_log_visual(texto)`

Adiciona linha ao visualizador de logs.

#### `clique_em_hud(pos_mouse)`

Detecta cliques em botões e áreas do HUD.

#### `selecionar_ataque_por_clique(pos_mouse)`

Retorna o ataque clicado na ficha, se existir.

---

## 12. `Codigo/ModulosBatalha/MontadorJogadas.py`

### Atualização v7 — custo previsto, custo real e ações de movimento/troca

Regras fechadas na v7:

- Energia real é gasta somente na execução oficial da ação, pelo servidor.
- O cliente calcula energia prevista apenas para impedir montagem obviamente inválida e para exibir gasto na HUD/ficha/barra.
- Movimento custa `10` de energia.
- Troca custa `15` de energia.
- Ataques usam o custo vindo do JSON de propriedades, quando existir, ou do CSV quando o JSON não sobrescrever.
- Segunda ação do mesmo Pokémon continua custando `+10%`, aplicada sobre o custo base da ação específica.
- Se o Pokémon perder energia antes de executar sua ação, a ação falha no log e a rodada segue.
- Remover uma ação preparada recalcula a energia prevista e pode fazer uma ação restante voltar ao custo normal.


### Atualização v5 — ações, energia, área e troca de posição

Regras fechadas de montagem:

- Limite: 5 ações por lado em cada rodada.
- Limite: 2 ações por Pokémon.
- Qualquer ação conta para o limite do Pokémon: ataque, movimento ou troca.
- Troca conta como ação do Pokémon que sai.
- O Pokémon que entra por troca não pode agir no mesmo turno em que entrou.
- Segunda ação do mesmo Pokémon custa +10%.
- Se uma ação for removida, a energia prevista é recalculada e a ação que sobrar pode voltar ao custo normal.
- A ordem visual das ações preparadas importa apenas quando o mesmo Pokémon tem duas ações, pois ele executa primeiro a ação colocada primeiro.
- O cliente deve impedir ação por energia insuficiente e alvificação claramente errada.
- O cliente não precisa ter validador forte para todo o resto; o servidor/log resolve falhas restantes.
- Alvo de ataque é normalmente área, não Pokémon.
- Por padrão, o jogador pode atacar área vazia para prever movimento inimigo.
- A propriedade especial deve indicar quando um ataque **só pode** mirar área ocupada.
- Ataques em linha/coluna conectam o indicador na frente da fileira ou coluna.
- Movimento para área livre prepara movimento.
- Movimento para área ocupada por aliado prepara troca de posição entre os dois aliados.
- Movimento/troca envolvendo Pokémon morto não é permitido; se o Pokémon morrer antes da ação futura, a ação falha.


### Responsabilidade principal

Montar as ações que compõem a jogada do jogador.

Esse arquivo controla o estado de preparação da jogada antes de ela ser enviada ao servidor.

### `selfs`/estado relevante

- `self.partida_cliente`
- `self.arena`
- `self.hud`
- `self.indicador`

- `self.pokemon_origem`
- `self.ataque_selecionado`
- `self.estado_montagem`
  - Exemplo: nenhum, preparando ataque, preparando movimento, preparando troca.

- `self.acoes_preparadas`
- `self.limite_acoes_jogada = 5`
- `self.limite_acoes_por_pokemon = 2`
- `self.multiplicador_segunda_acao = 1.10`

- `self.previa_energia`
- `self.alvos_validos`
- `self.destino_previo`

### Métodos relevantes

#### `iniciar_preparacao_ataque(pokemon, ataque)`

Entra em estado de preparação de ataque.

Fluxo:

1. Guarda Pokémon origem.
2. Guarda ataque selecionado.
3. Lê propriedades do ataque.
4. Calcula alvos válidos.
5. Ativa indicador visual.

#### `calcular_alvos_validos(ataque, pokemon_origem)`

Usa o JSON de propriedades do ataque para descobrir quais áreas/Pokémon podem ser alvo.

Deve considerar alvificação como:

- 1 alvo;
- 2 alvos;
- alvo do mesmo lado;
- alvo de lado oposto;
- mesmo lado e lado oposto;
- combinações como 1 alvo do mesmo lado e 2 de lado oposto;
- linha;
- coluna;
- duas linhas;
- duas colunas;
- variações por lado.

#### `atualizar_preparacao(pos_mouse)`

Atualiza prévia enquanto o mouse se move.

Deve permitir que o indicador se prenda ao centro da área quando o mouse passa sobre uma área relevante.

#### `confirmar_alvo(area_ou_pokemon)`

Tenta preparar uma ação de ataque com o alvo selecionado.

Se válido, adiciona a ação automaticamente à jogada.

#### `iniciar_arraste_pokemon(pokemon)`

Inicia preparação de movimento ou troca por arraste.

#### `atualizar_arraste(pos_mouse)`

Atualiza prévia de movimento/troca durante arraste.

#### `soltar_arraste(destino)`

Decide se o destino representa:

- área aliada válida: prepara movimento;
- Pokémon do banco: prepara troca;
- destino inválido: cancela prévia.

#### `preparar_movimento(pokemon, area_destino)`

Adiciona ação de movimento.

#### `preparar_troca(pokemon_ativo, pokemon_reserva)`

Adiciona ação de troca.

#### `adicionar_acao(acao)`

Adiciona uma ação à jogada se passar pelas validações locais.

Valida:

- limite de 5 ações por jogada;
- limite de 2 ações por Pokémon;
- energia disponível prevista;
- destino/alvo coerente.

#### `remover_acao(indice_ou_id)`

Remove ação preparada e recalcula energia prevista.

#### `limpar_jogada()`

Limpa todas as ações preparadas.

#### `calcular_custo_acao(pokemon, acao)`

Calcula custo previsto.

Regras:

- custo base vem do ataque/ação;
- se for a segunda ação do mesmo Pokémon, aumenta 10%;
- não permite preparar se energia projetada for insuficiente.

#### `gerar_pacote_jogada()`

Serializa as ações preparadas para envio ao servidor via `ServerBatalha.enviar_jogada(...)`.

---

## 13. `Codigo/ModulosBatalha/IndicadorAtaque.py`

### Atualização v5 — prévia e ação preparada

O indicador representa tanto a prévia quanto a ação já preparada.

Regras fechadas:

- Cada ação preparada mantém seu próprio indicador.
- Indicador de troca liga o Pokémon ativo ao slot/Pokémon da reserva.
- Indicador inválido aparece em vermelho durante a prévia.
- Após soltar em destino inválido, a prévia some.
- Cores são padrão visual, não regra de servidor.


### Responsabilidade principal

Renderizar indicadores visuais de ações durante a preparação e depois que a ação foi preparada.

Apesar do nome inicial ser `IndicadorAtaque`, esse arquivo deve representar visualmente não apenas ataques, mas também movimento e troca, caso não seja criado outro arquivo específico para indicadores de ações.

### `selfs`/estado relevante

- `self.origem`
- `self.destino`
- `self.tipo_acao`
  - ataque, movimento, troca ou inválido.

- `self.estado`
  - preparando ou preparado.

- `self.valido`
- `self.cor`
- `self.alpha`
- `self.animacao_fluxo`
- `self.tempo_animacao`
- `self.pontos_setas`

### Métodos relevantes

#### `configurar(origem, destino, tipo_acao, estado, valido)`

Define os dados usados para desenhar o indicador.

#### `atualizar(destino_atual, dt)`

Atualiza destino e animação de fluxo.

#### `desenhar(surface, camera)`

Desenha o fluxo de setas.

A aparência deve lembrar:

```text
>>>>>
```

As setas devem ser levemente arredondadas, transparentes e com sensação de fluxo.

#### `definir_estado_preparando()`

Deixa o indicador mais visível e animado.

#### `definir_estado_preparado()`

Deixa o indicador mais transparente e sem animação de fluxo.

#### `definir_validade(valido)`

Atualiza cor/estado inválido.

Cores conceituais:

- inválido: vermelho;
- movimento: azul;
- ataque: laranja;
- troca: verde.

#### `calcular_pontos_setas()`

Calcula os pontos entre origem e destino para formar o fluxo visual.

---

## 14. `Codigo/ModulosBatalha/ControladorBatalha.py`

### Atualização v5 — estado inicial e seleção durante log

Regras fechadas:

- Depois do estado oficial inicial, a batalha entra em `montando_jogada`.
- O servidor define `rodada_atual`; o cliente apenas reflete.
- O controlador mantém o espelho visual da partida, mas não vira fonte de regra.
- Ao terminar leitura/animação do log e a batalha não estiver finalizada, volta para montagem.
- Durante log/animação, seleção e input ficam bloqueados.


### Responsabilidade principal

Organizar o sistema de batalha no cliente.

O `ControladorBatalha` é o maestro da batalha no cliente. Ele conecta arena, HUD, Pokémon, jogador, montador, logs, animações, comunicação e finalização.

### `selfs`/estado relevante

- `self.id_partida`
- `self.tipo_batalha`
- `self.estado_batalha`
  - inicializando, montando jogada, aguardando outro lado, lendo log, animando rodada, finalizando, encerrada.

- `self.partida_cliente`
- `self.arena`
- `self.pokemons`
- `self.pokemons_por_id`
- `self.pokemon_selecionado`

- `self.player_batalha`
- `self.montador_jogadas`
- `self.hud`
- `self.leitor_logs`
- `self.controlador_animacoes`
- `self.finalizador`
- `self.server_batalha`

- `self.rodada_atual`
- `self.lado_jogador`
- `self.aguardando_servidor`

### Métodos relevantes

#### `iniciar(estado_inicial)`

Recebe o estado oficial inicial do servidor e monta os componentes client-side.

#### `criar_componentes()`

Cria arena, HUD, player, montador, leitor, controlador de animações e finalizador.

#### `atualizar(dt, eventos)`

Atualiza o estado geral da batalha.

Deve:

- processar inputs quando permitido;
- atualizar HUD;
- atualizar arena/Pokémon;
- atualizar animações;
- ler logs quando estiver nesse estado.

#### `desenhar(surface)`

Desenha arena, Pokémon, indicadores, animações e HUD na ordem correta.

#### `selecionar_pokemon(pokemon)`

Atualiza seleção global e HUD.

#### `enviar_jogada_pronta()`

Pega pacote do `MontadorJogadas`, chama `ServerBatalha.enviar_jogada(...)` e trata a resposta.

#### `tratar_resposta_jogada(resposta)`

Pode receber:

- confirmação de espera;
- log da rodada;
- erro de validação.

#### `receber_log(log)`

Entrega log ao `LeitorLogs` e muda estado para leitura/animação.

#### `aplicar_resultado_final(resultado)`

Consolida o diff final no estado local.

#### `voltar_para_montagem()`

Prepara nova rodada se a batalha não acabou.

#### `finalizar_batalha(dados_finalizacao)`

Chama `FinalizadorBatalha`.

#### `mudar_estado(novo_estado)`

Centraliza mudanças de estado da batalha.

---

## 15. `Codigo/ModulosBatalha/LeitorLogs.py`

### Atualização v5 — histórico, resultado e erros

Formato fechado:

- O log contém `historico` evento a evento.
- O log contém `resultado` com diffs finais para assegurar consistência.
- Não é necessário snapshot antes/depois em todo evento.
- Evento intermediário pode alterar visualmente vida/estado antes do resultado final.
- Ao fim, o `resultado` consolida e corrige o estado local.
- Falha visual/animação ausente deve passar seco e continuar leitura.
- Erros de ação entram no log, mas não precisam ser animados porque indicam algo a corrigir depois.
- O HUD deve criar seus próprios textos para o visualizador ficar mais vivo/quente; o log não precisa trazer texto pronto como fonte principal.


### Responsabilidade principal

Ler o log retornado pelo servidor e aplicar os acontecimentos no cliente em ordem.

O servidor resolve a rodada e devolve um log. O cliente não recalcula a rodada; ele lê o que aconteceu e reproduz.

### `selfs`/estado relevante

- `self.controlador`
- `self.hud`
- `self.controlador_animacoes`

- `self.log_atual`
- `self.historico`
- `self.resultado`
- `self.indice_evento`
- `self.tempo_entre_eventos`
- `self.timer_evento`
- `self.lendo`
- `self.finalizado`

### Métodos relevantes

#### `carregar_log(log)`

Recebe o log do servidor e separa histórico e resultado.

#### `iniciar_leitura()`

Começa o processamento do histórico.

#### `atualizar(dt)`

Avança a leitura com ritmo controlado.

#### `processar_proximo_evento()`

Lê o próximo evento do histórico.

#### `processar_evento(evento)`

Atualiza HUD, chama animações e aplica mudanças visuais intermediárias.

Eventos possíveis:

- Pokémon usou ataque;
- Pokémon se moveu;
- Pokémon trocou;
- Pokémon sofreu dano;
- Pokémon recebeu cura;
- Pokémon recebeu efeito;
- Pokémon morreu/desmaiou;
- clima mudou;
- arena mudou;
- rodada terminou;
- batalha terminou.

#### `aplicar_diff_evento(evento)`

Aplica alteração visual/local ligada ao evento, quando necessário.

#### `enviar_evento_para_hud(evento)`

Adiciona texto ao visualizador de logs.

#### `enviar_evento_para_animacao(evento)`

Chama o `ControladorAnimacoes` para o evento.

#### `consolidar_resultado()`

Ao fim da leitura, aplica o resultado/diff final oficial.

#### `terminou()`

Retorna se o log já foi completamente lido.

---

## 16. `Codigo/ModulosBatalha/ControladorAnimacoes.py`

### Atualização v5 — bloqueio e ticks

Animações importantes podem bloquear a leitura do próximo evento. Cartuchos e efeitos pequenos podem não bloquear.

A animação deve seguir o log recebido. O cliente não recalcula colisão, acerto, dano ou deslocamento real. Avanço, salto e projétil são apenas interpolação visual; a posição oficial vem do diff/log.


### Responsabilidade principal

Controlar a execução das animações da rodada no cliente.

Esse arquivo trabalha junto com o `LeitorLogs` e chama o `PokemonAnimator` quando necessário.

### `selfs`/estado relevante

- `self.controlador`
- `self.animator`
- `self.fila_animacoes`
- `self.animacoes_ativas`
- `self.bloqueia_log`
  - Indica se a leitura deve esperar a animação terminar.

- `self.animacao_em_andamento`

### Métodos relevantes

#### `receber_evento(evento)`

Converte evento de log em uma ou mais animações.

#### `criar_animacao_de_evento(evento)`

Mapeia tipos de evento para animações específicas.

#### `adicionar_animacao(animacao)`

Adiciona animação à fila.

#### `executar_proxima()`

Inicia próxima animação.

#### `atualizar(dt)`

Atualiza animações ativas.

#### `desenhar(surface)`

Desenha animações próprias, projéteis e efeitos temporários.

#### `animar_ataque(evento)`

Anima uso de ataque.

#### `animar_projetil(evento)`

Anima projétil, se o ataque tiver contato do tipo tiro.

#### `animar_avanco(evento)`

Anima avanço.

#### `animar_salto(evento)`

Anima salto.

#### `animar_dano(evento)`

Chama `PokemonAnimator.animar_tomar_dano(...)`.

#### `animar_cura(evento)`

Chama `PokemonAnimator.animar_receber_cura(...)`.

#### `animar_morte(evento)`

Chama `PokemonAnimator.animar_morrer(...)`.

#### `animar_troca(evento)`

Chama `PokemonAnimator.animar_troca(...)`.

#### `esta_ocupado()`

Retorna se há animação bloqueante em andamento.

---

## 17. `Codigo/ModulosBatalha/FinalizadorBatalha.py`

### Atualização v5 — fim, fuga e XP

Fim normal da batalha:

- A batalha acaba quando um dos lados fica sem nenhum Pokémon com vida.
- Em confronto, vencer normalmente significa derrotar todos os selvagens, salvo fuga/captura futura.
- Derrota do jogador ocorre quando não há ativo nem reserva viva.

Fuga:

- Fuga encerra a batalha antes de vitória/derrota normal.
- Fuga reduz pela metade o XP de todos os Pokémon.
- Fuga não abre subtela de resultados; ela volta ao mundo normal pelo fluxo já existente.

XP:

```text
xp_base = dano_causado + energia_gasta + rodadas * 10
xp_final_por_pokemon = xp_base * multiplicador
```

O multiplicador individual de cada Pokémon deve variar de `0.75` a `1.5`.

Persistência pós-batalha:

- Apenas vida e XP persistem.
- Nenhuma variação temporária, variação permanente de batalha ou efeito de batalha persiste depois do encerramento.


### Responsabilidade principal

Finalizar a batalha no cliente quando o servidor indicar que ela terminou.

O fim da batalha deve vir do log/resultado oficial do servidor.

### `selfs`/estado relevante

- `self.controlador`
- `self.resultado_final`
- `self.vencedor`
- `self.perdedor`
- `self.xp_concedido`
- `self.estado_pokemons_final`
- `self.subtela_resultados`

### Métodos relevantes

#### `finalizar(resultado_final)`

Fluxo principal de encerramento.

#### `detectar_vencedor(resultado_final)`

Lê vencedor/perdedor do resultado oficial.

#### `aplicar_estado_final_pokemons(resultado_final)`

Atualiza vida final dos Pokémon do jogador conforme estado pós-batalha.

#### `conceder_xp(resultado_final)`

Aplica XP aos Pokémon do jogador.

Detalhes de cálculo de XP ainda serão aprofundados depois.

#### `abrir_subtela_resultados()`

Chama a subtela de resultados.

#### `fechar_batalha()`

Retorna o jogador ao fluxo normal do jogo.

---

## 18. `Codigo/ModulosBatalha/IA/ControladorIA.py`

### Atualização v5 — IA fica no cliente

A IA de batalha fica no cliente.

Ela recebe o estado/espelho da partida e devolve uma jogada para o `lado_id` que ela controla. Essa jogada deve ter o mesmo formato da jogada do jogador e passar pelo mesmo caminho:

```text
ControladorIA
  ↓
Montador/serializador de jogada
  ↓
Codigo/Server/ServerBatalha.py
  ↓
RotasBatalha/GerenciadorPartidas/Partida
```

Em confronto contra selvagem, o cliente deve produzir e enviar a jogada do lado controlado por IA. O servidor permanece neutro e não escolhe ações por conta própria.

A IA deve usar a `seed_partida`/RNG controlado quando precisar sortear decisões.


### Responsabilidade principal

Guardar a entrada principal da IA de batalha.

A IA ainda não é foco desta etapa, mas a arquitetura deve reservar uma pasta própria para ela.

### `selfs`/estado relevante

- `self.partida`
- `self.lado_controlado`
- `self.configuracao_ia`
- `self.random`

### Métodos relevantes

#### `gerar_jogada(partida, lado)`

Recebe a partida e devolve as jogadas do lado controlado por bot.

Uso inicial:

- confronto contra Pokémon selvagem;
- futuramente, batalha contra treinador.

#### `escolher_pokemon_ativo()`

Seleciona Pokémon apto para agir.

#### `escolher_acao(pokemon)`

Escolhe ataque, movimento ou troca.

#### `escolher_alvo(acao)`

Escolhe alvo válido para a ação.

#### `montar_pacote_jogada()`

Retorna jogada no mesmo formato aceito pelo servidor.

### Escopo inicial

A IA inicial pode ser simples. Ela não precisa ser inteligente ou complexa nesta fase.

---

# DADOS

---

## 19. `Dados/CSV de ataques`

### Atualização v5 — papel do CSV

O CSV continua sendo fonte de dados simples/visuais.

Regras fechadas:

- O campo `ID` identifica o ataque na batalha/dados.
- `Code` é código estável entre ataques, mas `ID` também existe e deve ser respeitado.
- `Estilo` não deve controlar a lógica profunda do ataque.
- Ataques sem JSON de propriedades não rodam.
- Descrição não altera lógica.
- Campos visuais simples podem permanecer no CSV, mas propriedades complexas e custo sobrescrito pertencem ao JSON.


### Responsabilidade principal

Listar os ataques existentes e suas informações mais diretas.

O CSV de ataques deve conter dados mais simples e visuais dos ataques.

### Campos conceituais esperados

- identificador/code do ataque;
- nome;
- descrição;
- tipo;
- estilo;
- custo;
- dados simples usados pela ficha/HUD;
- identificador usado para conectar o ataque ao JSON de propriedades e aos executes.

### Funções conceituais de leitura

Mesmo que fiquem em outro loader já existente, o sistema deve possuir acesso equivalente a:

#### `carregar_ataques_csv()`

Carrega todos os ataques.

#### `buscar_ataque_por_id(id_ataque)`

Retorna dados simples do ataque.

#### `listar_ataques_do_pokemon(pokemon)`

Retorna ataques disponíveis para a ficha do Pokémon.

### Regra importante

O CSV não deve carregar toda a complexidade de alvos, animações, propriedades especiais e funcionamento detalhado. Essas informações pertencem ao JSON de propriedades do ataque e aos executes do servidor.

---

## 20. `Dados/JSON de propriedades dos ataques`

### Atualização v7 — alvo por área e resolução no momento da execução

Regras fechadas na v7:

- O alvo serializado de ataques deve ser, por padrão, `area_id`, não o objeto Pokémon.
- Mesmo quando o jogador clica visualmente em um Pokémon, a jogada deve enviar a área ocupada por ele.
- Ataques podem mirar área vazia por padrão.
- Quando um ataque exigir ocupante, o JSON deve declarar explicitamente `exige_area_ocupada: true`.
- O ocupante real da área deve ser resolvido pelo servidor no momento da execução da ação.
- Se o alvo saiu da área antes da execução, o ataque atinge a área e pode gerar evento de falha/sem alvo real, conforme propriedades do ataque.
- Ataques em linha, coluna, múltiplas linhas ou múltiplas colunas recalculam a formação no momento da execução.
- Esse comportamento evita que o cliente seja fonte da verdade e permite prever movimentação inimiga com ataques em área.


### Atualização v5 — schema, alvificação e remoção de legado antigo

Regras fechadas:

- O JSON deve ter `schema_version`.
- Ataque tem `ID` e `Code`: `ID` é o identificador usado na batalha/dados; `Code` é código estável do ataque.
- Ataques sem JSON não rodam.
- O JSON pode sobrescrever custo do CSV quando houver regra específica.
- A alvificação precisa ser altamente configurável, permitindo combinações como:
  - 2 alvos do mesmo lado;
  - 1 alvo de lado oposto;
  - mistura de alvos em lados diferentes;
  - linhas/fileiras;
  - colunas;
  - 2 colunas e 1 fileira;
  - fileira apenas de um lado específico.
- Por padrão, pode mirar área vazia.
- A propriedade especial deve indicar o oposto: quando o ataque **só pode** mirar área ocupada.
- Não usar conceitos antigos de cone, círculo, parede, ricochete ou colisão de projétil como regra base deste modelo.
- Não existe mais regra de ricochete neste modelo.
- Não existe parede como colisão de ataque neste modelo.
- Não precisa declarar imunidades genéricas no JSON neste momento.
- O estilo básico de ataque deve distinguir principalmente ataque ativo/passivo conforme o modelo atual.
- A animação/projétil visual vem do JSON, mas a execução real continua no servidor.


### Responsabilidade principal

Definir o comportamento detalhado dos ataques.

Esse JSON é mais intenso que o CSV e determina como o ataque funciona em termos de alvificação, animação, projétil e efeitos.

### Campos conceituais esperados

- ID/code do ataque;
- regra de alvificação;
- número de alvos;
- lado permitido do alvo;
- formato de alvo: regular, linha, coluna, múltiplas linhas, múltiplas colunas etc.;
- animação de contato: tiro, avanço, salto, nenhum;
- sprite do tiro/projétil;
- efeito aplicado ao Pokémon atingido;
- efeito aplicado ao Pokémon que utiliza;
- execute principal do ataque;
- execute de alvificação, quando existir;
- executes periféricos do ataque, quando existirem;
- flags usadas pelos executes periféricos;
- grupo de ativação dos executes periféricos, quando aplicável (`self`, `mesmo_lado`, `lado_oposto`, `qualquer_lado`, `todos`);
- parâmetros extras necessários para execução.

### Funções conceituais de leitura

#### `carregar_propriedades_ataques()`

Carrega o JSON completo.

#### `buscar_propriedades_ataque(id_ataque)`

Retorna propriedades detalhadas de um ataque.

#### `validar_schema_propriedades()`

Garante que o JSON tenha formato mínimo esperado.

### Alvificação

A alvificação define como o jogador pode escolher os alvos do ataque.

Formatos possíveis:

- alvo regular;
- número definido de alvos;
- alvo do mesmo lado;
- alvo de lado oposto;
- alvo de mesmo lado ou lado oposto;
- combinação configurável entre lados;
- linha;
- coluna;
- duas linhas;
- duas colunas;
- variações específicas por lado.

### Executes declarados no JSON

O JSON pode apontar quais funções de execute serão usadas pelo ataque.

Tipos de execute:

- `execute_principal`;
- `execute_alvificacao`;
- `executes_perifericos`.

O JSON não deve conter a lógica Python em si. Ele apenas declara os nomes/códigos que serão resolvidos no servidor pelos arquivos de executes.

Para executes periféricos, o JSON deve conseguir declarar a flag e o grupo de ativação.

Exemplo conceitual:

```json
{
  "ataque": "lamina_noturna",
  "execute_principal": "causar_dano_normal",
  "executes_perifericos": [
    {
      "execute": "curar_usuario_ao_matar",
      "flag": "AoMatar",
      "grupo": "self"
    }
  ]
}
```

### Regra importante

A execução real dos efeitos deve acontecer no servidor. O cliente usa o JSON para montar jogada e visualização, mas não para aplicar resultado oficial.

---

# SERVIDOR — ROTAS

---

## 21. `SimuladorServerJogo/Rotas/RotasBatalha.py`

### Atualização v5 — três rotas

Rotas oficiais iniciais:

1. `rota_inicializar_batalha(dados_inicializacao)`;
2. `rota_enviar_jogada(dados_jogada)`;
3. `rota_finalizar_batalha(dados_finalizacao)`.

A rota de inicialização não retorna log/resultado.  
A rota de finalização não retorna log/resultado.  
A rota de jogada pode retornar log, e o resultado fica dentro do log.


### Responsabilidade principal

Receber as duas chamadas de batalha vindas do client através de `Codigo/Server/ServerBatalha.py` e encaminhar para `GerenciadorPartidas`.

Caso o projeto já tenha um arquivo central de rotas com outro nome, a implementação deve adicionar as rotas de batalha nele em vez de criar duplicata desnecessária.

### `selfs`/estado relevante, caso seja classe

- `self.gerenciador_partidas`
- `self.rotas_registradas`
- `self.validador_entrada`, se existir padrão no servidor.

### Métodos/rotas relevantes

#### `rota_inicializar_batalha(dados_inicializacao)`

Recebe pedido de criação da batalha.

Fluxo:

1. Valida formato mínimo dos dados.
2. Encaminha para `GerenciadorPartidas.criar_partida(...)`.
3. Retorna o estado inicial oficial ao cliente.

#### `rota_enviar_jogada(dados_jogada)`

Recebe jogada preparada por um lado.

Fluxo:

1. Valida formato mínimo.
2. Localiza partida por ID.
3. Encaminha para `GerenciadorPartidas.receber_jogada(...)`.
4. Retorna espera, erro ou log da rodada.

### Regra importante

O arquivo de rotas não deve conter regra de batalha pesada. Ele apenas valida entrada básica e encaminha para a camada correta.

---

# SERVIDOR — BATALHA

---

#### `rota_finalizar_batalha(dados_finalizacao)`

Recebe pedido de encerramento/limpeza de batalha.

Fluxo:

1. Valida formato mínimo.
2. Localiza partida por ID.
3. Encaminha para `GerenciadorPartidas.encerrar_partida(...)` ou método equivalente.
4. Retorna confirmação de finalização.

Não deve recalcular resultado de batalha. Resultado oficial fica no log.

## 22. `SimuladorServerJogo/Batalha/GerenciadorPartidas.py`

### Atualização v5 — neutralidade e responsabilidade

O `GerenciadorPartidas` não deve escolher ação de IA. A IA fica no cliente.

Regras fechadas:

- Mantém partidas ativas.
- Pode manter partidas finalizadas temporariamente para debug/reenvio/limpeza.
- Gera ou coordena ID de partida.
- Delega validação detalhada para `Partida`.
- Conhece/carrega configurações globais de batalha quando necessário, mas não executa regra pesada.


### Responsabilidade principal

Gerenciar as partidas de batalha abertas no servidor.

Esse arquivo recebe pedidos de inicialização vindos das rotas e registra partidas.

### `selfs`/estado relevante

- `self.partidas_ativas`
  - Dicionário `id_partida -> Partida`.

- `self.proximo_id` ou gerador de IDs.
- `self.partidas_finalizadas`, se for necessário manter histórico temporário.
- `self.config_batalha`, se houver regras globais.

### Métodos relevantes

#### `criar_partida(dados_inicializacao)`

Cria uma nova `Partida` no servidor.

Passos:

1. Gera ID da partida.
2. Valida times recebidos.
3. Cria objeto `Partida`.
4. Registra em `self.partidas_ativas`.
5. Retorna estado inicial oficial.

#### `registrar_partida(partida)`

Adiciona partida ao dicionário de partidas ativas.

#### `obter_partida(id_partida)`

Localiza partida existente.

#### `receber_jogada(id_partida, lado_id, jogada)`

Encaminha jogada para a partida correta.

Pode retornar:

- erro de validação;
- confirmação de espera;
- log da rodada, se ambos os lados já enviaram jogada.

#### `encerrar_partida(id_partida)`

Remove ou marca partida como finalizada.

#### `limpar_partidas_finalizadas()`

Limpeza periódica, se necessário.

---

## 23. `SimuladorServerJogo/Batalha/Partida.py`

### Atualização v7 — fim da rodada, energia e ausência de troca automática

Regras fechadas na v7:

- A energia recupera no fim da rodada, depois que todas as ações ordenadas forem executadas ou falharem.
- A recuperação de energia deve ocorrer após as verificações de fim de passo e antes de preparar a próxima rodada.
- Não existe troca automática quando um Pokémon morre.
- Se um lado ainda tiver reserva viva, ele permanece com o ativo morto/removido até preparar uma troca em rodada futura, salvo regra futura específica.
- Captura não faz parte da v7 e não deve ser implementada como fluxo jogável nesta etapa.


### Atualização v5 — estado oficial, seed e fim de rodada

Regras fechadas:

- `Partida` tem `seed_partida` e RNG próprio.
- Todo RNG oficial da batalha usa esse RNG controlado.
- A partida trabalha com `lado_id`, não com nomes fixos de aliado/inimigo.
- Times/lados iniciais podem ser `50` e `51` no modelo 1x1.
- A partida guarda lista de objetos serializáveis.
- Pokémon, construtos e a própria partida devem ter `Verificar`.
- No fim de cada passo: verificar Pokémon, depois construtos, depois estado geral quando aplicável.
- No fim da rodada: chamar método de fim de rodada da partida, incrementar rodada se a batalha continuar e limpar jogadas recebidas.
- Clima pode ser dict simples ou `None`.
- Efeitos de área ficam na partida e são ligados a áreas oficiais.
- A partida finaliza quando um lado fica sem Pokémon com vida, ou por encerramento especial como fuga.


### Responsabilidade principal

Representar a partida de batalha oficial no servidor.

Essa é a classe central do estado real da batalha.

### `selfs`/estado relevante

- `self.id_partida`
- `self.tipo_batalha`
- `self.rodada_atual`
- `self.estado_partida`

- `self.lados`
- `self.times`
- `self.pokemons`
- `self.pokemons_por_id`
- `self.pokemons_ativos`
- `self.pokemons_reserva`

- `self.clima`
- `self.efeitos_area`
- `self.arena`
- `self.jogadas_recebidas`

- `self.coletor_acoes`
- `self.rodador_turno`
- `self.construtor_log`

- `self.vencedor`
- `self.perdedor`
- `self.finalizada`

### Métodos relevantes

#### `__init__(dados_inicializacao)`

Cria a partida com times, arena, rodada inicial e estado base.

#### `montar_estado_inicial()`

Gera o estado oficial que será devolvido ao cliente após a criação.

#### `receber_jogada(lado_id, jogada)`

Recebe jogada de um lado.

Se todos os lados necessários já jogaram, chama resolução da rodada.

#### `todos_lados_prontos()`

Verifica se a rodada já pode ser resolvida.

#### `resolver_rodada()`

Fluxo principal de rodada:

1. Coleta ações.
2. Valida ações.
3. Ordena ações.
4. Roda turno em passos, com uma ação por passo.
5. Ao final de cada passo, garante verificação dos Pokémon/construtos afetados e, preferencialmente, da partida inteira.
6. Verifica estado final.
7. Gera log.
8. Incrementa rodada se a batalha continuar.

#### `verificar_estado_partida()`

Verifica vitória, derrota, morte de todos os Pokémon de um lado ou outros critérios de fim.

#### `aplicar_diff_final()`

Consolida alterações finais depois da rodada.

#### `serializar_estado()`

Retorna estado completo ou resumido da partida.

#### `obter_pokemon(id_pokemon)`

Busca Pokémon por ID.

#### `obter_lado(lado_id)`

Busca dados de um lado/time.

#### `finalizar(vencedor, perdedor)`

Marca a partida como finalizada.

---

## 24. `SimuladorServerJogo/Batalha/PokemonBatalha.py`

### Atualização v7 — efeitos, energia, barreira e vampirismo

Regras fechadas na v7:

- `PokemonBatalha` no servidor deve impedir mais de 4 efeitos formais simultâneos no mesmo Pokémon.
- Tentativa de aplicar o 5º efeito formal deve retornar falha controlada e gerar evento de log.
- Duração de efeitos formais decrementa ao fim de cada passo global, preferencialmente por chamada centralizada feita pelo rodador/partida.
- Energia é descontada oficialmente na execução da ação, não na montagem.
- Dano absorvido por `BarreiraAtual` não conta como dano causado à vida.
- Vampirismo cura somente com base no dano efetivamente causado à vida do alvo.
- Dano absorvido por barreira não gera cura vampírica e não deve entrar no cálculo de XP por dano causado.


### Atualização v5 — energia, crítico, efeitos, morte e loops

Regras fechadas:

- `EnergiaAtual` começa em 75% de `EneM`.
- `CrC` é percentual de 0 a 100.
- `CrD` deve ser tratado como multiplicador de crítico.
- Barreira acumula sem limite inicial.
- Qualquer barreira ativa segura ao menos uma instância de dano.
- Dano absorvido por barreira dispara fluxo/evento de receber dano/impacto, mas não gera vampirismo.
- Vampirismo usa apenas dano real causado em `VidaAtual`.
- Cura não revive Pokémon morto.
- `Morrer()` limpa efeitos/estados de batalha do Pokémon.
- Efeitos positivos e negativos repetidos stackam.
- O limite inicial é 4 efeitos simultâneos por Pokémon.
- `Verificar()` roda por passo e pode controlar duração dos efeitos em passos, evitando redução duplicada dentro do mesmo passo.
- Executes/passivas podem fazer muita coisa, mas um mesmo execute não pode rodar dentro de um método que o próprio execute chamou, evitando loop infinito.


### Responsabilidade principal

Representar o Pokémon de batalha no servidor.

Diferente do cliente, aqui o `PokemonBatalha` possui métodos reais de regra e alteração de estado. Essa tende a ser uma das maiores classes do sistema de batalha.

### `selfs`/estado relevante

Identidade e vínculo:

- `self.id_batalha`
- `self.id_original`
- `self.nome`
- `self.especie`
- `self.lado_id`
- `self.time_id`
- `self.partida`

Atributos padrão:

- `self.atributos_base`
- `self.variacoes_temporarias`
- `self.variacoes_permanentes`
- `self.atributos_finais`

Essas estruturas devem conter os atributos:

- `Vida`, `Atk`, `SpA`, `Def`, `SpD`, `Mag`, `Ene`, `Vel`, `Per`, `Int`, `Vamp`, `CrC`, `CrD`, `Dur`, `Amp`, `EneM`, `Acuracia`, `Assertividade`.

Estados atuais:

- `self.VidaAtual`
- `self.EnergiaAtual`
- `self.BarreiraAtual`
- `self.efeitos_positivos`
- `self.efeitos_negativos`
- `self.Build`
- `self.posicao`
- `self.ativo`
- `self.reserva`
- `self.vivo`

Outros:

- `self.ataques`
- `self.tipos`
- `self.logs_pendentes`, se for usado para alimentar o construtor.

### Métodos relevantes

#### `ReceberDano(valor, origem=None, dados=None)`

Aplica dano recebido pelo Pokémon.

Regras iniciais:

- Deve ser chamado pelo execute ou por outro método oficial, nunca diretamente pelo cliente.
- Deve disparar flags como `AoReceberDano` e, quando a vida chegar a 0, `AoMorrer`.
- Deve respeitar `BarreiraAtual` antes de reduzir `VidaAtual`.
- `BarreiraAtual` é um valor numérico acumulado, normalmente grande, por exemplo `100`, e se desgasta com base no dano recebido.
- A barreira absorve dano antes da vida. Exemplo: se o alvo tem `BarreiraAtual = 100` e recebe `40` de dano, a barreira cai para `60` e a vida não é reduzida.
- Além da absorção normal por valor, a barreira possui uma proteção mínima de instância: se existir qualquer barreira ativa, ela segura ao menos 1 instância de dano antes da vida ser afetada.
- Exemplo extremo: se o alvo tem `BarreiraAtual = 1` e recebe `23848` de dano em uma única instância, a barreira é consumida e a vida não é reduzida nessa instância.
- Dano absorvido pela barreira não gera cura por `Vamp`.
- Apenas o dano que realmente reduzir `VidaAtual` pode gerar vampirismo e causar morte.

#### `AplicarDano(alvo, valor, dados=None)`

Usado quando este Pokémon causa dano em outro alvo.

Deve calcular ou receber do execute os dados necessários de dano e chamar `alvo.ReceberDano(...)`.

O cálculo conceitual de dano deve seguir a ordem inicial:

1. Começar pelo dano bruto definido pelo execute/ataque.
2. Aplicar amplificação `Amp` como bônus percentual.
   - Como `Amp` base é `0`, a interpretação correta deve ser:

```text
dano_amplificado = dano_bruto * (1 + Amp/100)
```

3. Aplicar multiplicador de tipo vindo de `FraquezasResistencia`.
4. Aplicar STAB: se o tipo do ataque for um dos tipos do usuário, aumenta 20% do dano.
5. Aplicar crítico quando ocorrer.
   - Chance vem de `CrC`.
   - Dano crítico adicional vem de `CrD`.
6. Escolher defesa do alvo:
   - `Def` para dano normal/físico;
   - `SpD` para dano especial.
7. Aplicar perfuração:

```text
defesa_efetiva = defesa - Per/2
```

8. Calcular dano pós-defesa:

```text
dano_pos_defesa = dano * (100 / (100 + defesa_efetiva))
```

9. Aplicar durabilidade `Dur` como redução direta no dano final.
10. Chamar `ReceberDano` no alvo.
11. Se a vida do alvo foi reduzida, aplicar cura por `Vamp` no atacante conforme percentual de vampirismo.

Observações:

- Por segurança de implementação, `defesa_efetiva` e dano final não devem ficar negativos, salvo se uma regra futura permitir explicitamente defesa negativa.
- Existem flags ao longo do processo para alterar o dano em instâncias específicas.
- A divisão entre `AplicarDano` e `ReceberDano` deve permitir flags antes/depois de aplicar, antes/depois de receber, ao matar e ao morrer.

#### `ReceberCura(valor, origem=None, dados=None)`

Aplica cura recebida, respeitando limite de `Vida` final.

#### `AplicarCura(alvo, valor, dados=None)`

Usado quando este Pokémon cura outro alvo ou a si mesmo.

#### `ReceberBarreira(valor, origem=None, dados=None)`

Adiciona barreira atual ao Pokémon.

#### `AplicarBarreira(alvo, valor, dados=None)`

Aplica barreira em outro alvo ou em si mesmo.

#### `ReceberEfeito(efeito, origem=None, dados=None)`

Recebe efeito positivo ou negativo.

Deve registrar o efeito ativo e disparar flags como `AoReceberEfeito`.

Duração de efeitos deve ser medida em **passos**.

Regras iniciais de duração:

```text
efeito positivo: duração = base_do_efeito + Mag/5 do aplicador

efeito negativo bruto: duração = base_do_efeito + Mag/5 do aplicador - Mag/5 do alvo

efeito negativo final: máximo entre duração negativa bruta e metade da base do efeito

efeito negativo em si mesmo: duração = base_do_efeito
```

Trava obrigatória para efeitos negativos:

```text
duração_mínima_negativa = base_do_efeito / 2
```

Ou seja, a defesa por `Mag` pode reduzir a duração de um efeito negativo, mas não pode reduzir abaixo de metade da duração base.

Subefeitos de duração curta como `recuado` e `protegido`, quando duram apenas 1 turno/passo de lógica, não entram nessa regra como efeitos formais. Eles devem ser tratados como estados transitórios simples no próprio Pokémon.

#### `AplicarEfeito(alvo, efeito, dados=None)`

Aplica efeito em alvo.

Deve calcular a duração conforme o tipo do efeito, o `Mag` do aplicador e o `Mag` do alvo, aplicando a trava de duração mínima para efeitos negativos, depois chamar `alvo.ReceberEfeito(...)`.

Deve disparar flags como `AoAplicarEfeito`.

#### `ReceberAtributos(modificadores, origem=None, duracao=None)`

Recebe modificações de atributos.

Pode afetar variação temporária ou permanente conforme regra do efeito.

#### `AplicarAtributos(alvo, modificadores, dados=None)`

Aplica modificadores em outro alvo.

#### `MudarClima(clima, dados=None)`

Solicita mudança de clima na partida.

#### `MudarArena(alteracao, dados=None)`

Solicita alteração na arena ou nos efeitos de área.

#### `GanharEnergia(valor, dados=None)`

Aumenta `EnergiaAtual`, respeitando `EneM` final, salvo exceções futuras.

Deve disparar flags como `AoGanharEnergia`.

#### `Mover(area_destino, dados=None)`

Move o Pokémon para uma área da arena.

#### `Trocar(pokemon_reserva, dados=None)`

Troca Pokémon ativo por Pokémon da reserva.

#### `Morrer(dados=None)`

Marca Pokémon como morto/desmaiado.

#### `SerMovido(area_destino, origem=None, dados=None)`

Move o Pokémon por efeito externo.

#### `Verificar()`

Método central.

Deve:

1. Resetar variações temporárias.
2. Reaplicar efeitos ativos.
3. Atualizar atributos finais.
4. Validar vida máxima e vida atual.
5. Validar energia máxima e energia atual.
6. Validar morte.
7. Validar posição.
8. Atualizar condições especiais.

#### `recalcular_atributos()`

Recalcula atributos finais com base na fórmula:

```text
valor final = valor base + variação temporária + variação permanente/fixa
```

#### `serializar()`

Gera dados para log/diff/cliente.

#### `esta_vivo()`

Retorna estado vivo/morto.

#### `esta_apto_para_agir()`

Retorna se pode executar ação.

#### `coletar_executes_por_flag(flag, contexto)`

Monta a lista de passivas/executes que devem ser testados em uma flag.

Deve considerar:

- grupo `self`;
- grupo `mesmo_lado`;
- grupo `lado_oposto`;
- grupo `qualquer_lado`/`todos`;
- passivas de habilidades;
- passivas de itens da `Build`;
- executes periféricos do ataque atual, quando o contexto da ação trouxer essa lista artificial.

#### `disparar_flag(flag, contexto)`

Executa os callbacks/executes compatíveis com a flag e o grupo.

Esse método deve ser chamado por métodos como `ReceberDano`, `AplicarDano`, `ReceberCura`, `AplicarCura`, `Morrer`, `GanharEnergia`, `ReceberEfeito`, `AplicarEfeito`, `Mover` e `Trocar`.

---

## 25. `SimuladorServerJogo/Batalha/ColetorAcoes.py`

### Atualização v7 — validação sem gastar energia

Regras fechadas na v7:

- O `ColetorAcoes` valida estrutura, limites, lado, estado básico, alvo e custo previsto, mas não desconta energia.
- O custo oficial ainda deve ser calculável aqui para ordenação/relatório, porém o gasto real pertence ao `RodadorTurno`.
- Movimento tem custo base `10`.
- Troca tem custo base `15`.
- Segunda ação do mesmo Pokémon aplica multiplicador `1.10`.
- Se a energia ficar insuficiente entre coleta e execução, a ação deve falhar no passo correspondente e entrar no log.


### Atualização v5 — falha de ação e validação

Regras fechadas:

- Se uma ação falhar por erro/invalidação, ela vira registro no log e a rodada segue sem ela.
- A jogada inteira não é invalidada apenas por uma ação falha.
- Energia real é gasta no `RodadorTurno`, não no coletor.
- O alvo oficial de ataque normalmente é área, não Pokémon.
- Se o alvo morrer/sair antes da ação, a ação vai para a área onde o alvo estava, salvo exceção muito específica de ataque que mire Pokémon.
- Se a área de movimento ficar ocupada antes da ação, o movimento vira troca de posição com o ocupante quando a regra permitir.
- Ordem oficial: maior `Int` primeiro; empate usa maior `Vel`; persistindo empate, usar critério estável baseado em seed/ID.
- Troca não tem prioridade especial inicial.


### Responsabilidade principal

Coletar, validar e ordenar as ações enviadas pelos lados da batalha.

### `selfs`/estado relevante

- `self.partida`
- `self.acoes_recebidas`
- `self.acoes_validas`
- `self.acoes_invalidas`
- `self.ordem_acoes`

### Métodos relevantes

#### `coletar(jogadas_recebidas)`

Extrai ações das jogadas dos lados.

#### `validar_acao(acao)`

Valida uma ação individual.

Validações iniciais:

- Pokémon existe na partida;
- Pokémon pertence ao lado correto;
- Pokémon está apto;
- Pokémon tem energia suficiente;
- ação respeita limite por jogada;
- ação respeita limite por Pokémon;
- alvo é válido conforme propriedades do ataque;
- área de movimento é válida;
- troca é possível com Pokémon da reserva;
- não há conflito básico de posição/ocupação.

#### `validar_acoes()`

Valida todas as ações coletadas.

#### `ordenar_acoes()`

Ordena ações para o `RodadorTurno`.

Regra inicial de ordenação:

- `Int` é o atributo principal de ordem das ações.
- `Vel` não define a ordem principal; ela atua como critério de desempate.
- Se duas ações continuarem empatadas depois de `Int` e `Vel`, o desempate pode usar critério estável da partida, como ID da ação, ID do Pokémon ou seed da partida.

A lista resultante deve representar a sequência de passos do `RodadorTurno`.

#### `calcular_custo_real(acao)`

Calcula custo oficial no servidor.

Deve conferir o aumento de 10% na segunda ação do mesmo Pokémon.

#### `validar_alvo_ataque(acao)`

Confere alvo com base no JSON de propriedades do ataque.

#### `validar_movimento(acao)`

Confere área destino.

#### `validar_troca(acao)`

Confere Pokémon ativo e reserva.

#### `resultado_validacao()`

Retorna relatório de validação.

---

## 26. `SimuladorServerJogo/Batalha/RodadorTurno.py`

### Atualização v7 — execução real, alvos dinâmicos e decremento de efeitos

Regras fechadas na v7:

- O `RodadorTurno` é o local oficial para gastar energia da ação.
- Antes de executar a ação, deve validar se o usuário ainda está vivo, apto, posicionado corretamente e com energia suficiente.
- Se a energia for insuficiente no momento da execução, registrar falha da ação no log e seguir a rodada.
- Ataques resolvem ocupantes de área somente no momento da execução.
- Ataques em linha/coluna recalculam os alvos no momento da execução.
- Ao final de cada passo global, o rodador deve chamar as verificações necessárias e acionar o decremento de duração dos efeitos formais.
- Falhas de ação não cancelam a rodada inteira.


### Atualização v5 — custo, bloqueios e encadeamento

Regras fechadas:

- O custo é aplicado no rodador, no momento da execução.
- Se o impedimento for anterior à tentativa de ação, pode não gastar energia.
- Se a ação foi tentada e depois bloqueada por algo como proteção, o custo pode ser gasto conforme a regra do bloqueio.
- Execute de alvificação pode mudar praticamente qualquer dado do contexto, inclusive criar acerto garantido, alterar alvo ou alterar assertividade/acurácia.
- Execute principal roda por alvo atingido, salvo execute explicitamente global.
- Executes periféricos rodam dentro dos métodos oficiais chamados pelo execute principal, tecnicamente durante o próprio fluxo do execute.
- Um execute pode gerar outras ações, desde que isso passe pelo contexto/partida e gere log.
- Ação falha ainda gera fim de passo e `Verificar`.
- Clima, efeitos e efeitos de área processam por passo quando sua duração for em passos.


### Responsabilidade principal

Executar a rodada/turno com base nas ações ordenadas.

O rodador funciona em **passos**: cada ação ordenada corresponde a um passo. Ele não deve tentar resolver a rodada inteira como um bloco único sem checkpoints, porque o `Verificar` dos Pokémon precisa rodar no fim de cada passo.

### `selfs`/estado relevante

- `self.partida`
- `self.acoes_ordenadas`
- `self.eventos_rodada`
- `self.construtor_log`
- `self.executador_ataques`, se houver adaptador para `ExecuteAtaques`.
- `self.passo_atual`
- `self.contexto_acao_atual`

### Métodos relevantes

#### `rodar(acoes_ordenadas)`

Executa a rodada completa.

Fluxo básico:

1. Receber ações ordenadas pelo `ColetorAcoes`.
2. Para cada ação, abrir um novo passo.
3. Executar a ação daquele passo.
4. Registrar eventos gerados.
5. Rodar verificações ao final do passo.
6. Passar para a próxima ação.
7. Ao fim de todas as ações, fechar a rodada e entregar eventos ao `ConstrutorLog`.

#### `executar_passo(acao)`

Executa uma única ação da lista ordenada.

Fluxo:

1. Monta contexto do passo.
2. Aplica custo da ação.
3. Executa ataque, movimento ou troca.
4. Registra eventos.
5. Chama `chamar_verificacoes_fim_passo()`.

#### `executar_acao(acao)`

Decide o tipo da ação e chama método específico.

Tipos iniciais:

- ataque;
- movimento;
- troca.

#### `executar_ataque(acao)`

Executa ataque via dados/propriedades/execute.

Fluxo obrigatório:

1. Obter usuário do ataque.
2. Obter propriedades do ataque.
3. Obter alvos declarados/preparados pela ação.
4. Montar contexto com execute principal, execute de alvificação e executes periféricos.
5. Rodar `executar_alvificacao(...)`, se existir.
6. Calcular acerto por alvo com `calcular_chance_acerto(...)`.
7. Separar alvos atingidos e alvos que falharam.
8. Para cada alvo atingido, chamar o execute principal.
9. Permitir que os métodos chamados pelo execute principal disparem flags e testem executes periféricos.
10. Registrar eventos de uso, acerto, falha, dano, cura, efeito, morte etc.

#### `executar_alvificacao(acao, contexto)`

Roda o execute de alvificação antes da decisão de acerto/falha.

Esse execute pode alterar:

- acurácia;
- assertividade;
- lista de alvos;
- prioridade de alvo;
- regras especiais de mira;
- outros dados usados no cálculo de acerto.

#### `calcular_chance_acerto(usuario, alvo, contexto)`

Calcula a chance de o ataque atingir um alvo.

Base:

```text
chance = (Acuracia_efetiva_do_usuario / 100) * (Assertividade_efetiva_do_alvo / 100)
```

Regra inicial de velocidade relativa:

1. Calcular a velocidade média do confronto entre usuário e alvo:

```text
vel_media = (Vel_usuario + Vel_alvo) / 2
```

2. Comparar cada Pokémon com essa média.
3. Existe um escudo de 10 pontos: diferenças de até 10 pontos em relação à média não alteram acurácia/assertividade.
4. A partir do que exceder esses 10 pontos:
   - o atacante mais lento perde acurácia;
   - o atacante mais rápido ganha acurácia;
   - o alvo mais rápido reduz sua assertividade, ficando mais difícil de acertar;
   - o alvo mais lento aumenta sua assertividade, ficando mais fácil de acertar.

Exemplo:

```text
Vel_usuario = 30
Vel_alvo = 60
vel_media = 45

diferença em relação à média = 15
escudo = 10
ajuste real = 5

Acuracia do usuário: 100 -> 95
Assertividade do alvo: 100 -> 95
chance = 0.95 * 0.95 = 0.9025 = 90,25%
```

Observações:

- `Acuracia` e `Assertividade` são percentuais.
- O valor mínimo efetivo deve ser 0 para evitar chance negativa.
- Valores acima de 100 são permitidos, porque buffs podem aumentar acerto ou tornar um alvo mais fácil de acertar.

#### `sortear_acerto(chance, contexto)`

Usa a seed/RNG oficial da partida para decidir se o alvo foi atingido.

O sorteio deve ser determinístico dentro da partida, evitando divergência entre cliente e servidor.

#### `executar_movimento(acao)`

Executa movimento.

Deve chamar método oficial do Pokémon, como `Mover(...)`, para que flags e logs sejam respeitados.

#### `executar_troca(acao)`

Executa troca.

Deve chamar método oficial do Pokémon, como `Trocar(...)`, para que flags, estado de ativo/reserva e logs sejam respeitados.

#### `aplicar_custo(acao)`

Remove energia/custo da ação.

Deve ocorrer dentro do passo, antes da execução principal da ação, salvo exceção explícita futura.

#### `chamar_verificacoes_fim_passo()`

Chama `Verificar` ao fim de cada passo.

Ordem recomendada:

1. Pokémon afetados diretamente pela ação.
2. Demais Pokémon ativos.
3. Pokémon da reserva, se efeitos/passivas puderem afetá-los.
4. Construtos.
5. Partida/arena/clima.

Em caso de dúvida, preferir verificar todos os Pokémon e construtos para evitar estado temporário sujo.

#### `registrar_evento(evento)`

Acumula evento para o log.

#### `finalizar_rodada()`

Fecha a execução da rodada e entrega eventos ao `ConstrutorLog`.

## 27. `SimuladorServerJogo/Batalha/ConstrutorLog.py`

### Atualização v5 — estrutura do log

O log deve conter:

- `id_log`;
- `rodada`;
- `historico`;
- `resultado`;
- `alertas`/`erros` quando necessário.

Cada evento/registro do histórico deve ter ID próprio com prefixo `3`.

O HUD não deve depender de texto pronto vindo do log. O log fornece dados estruturados; o cliente monta mensagens mais vivas no visualizador.

Eventos recomendados:

- dano: origem, alvo, ataque, dano bruto, dano final, barreira absorvida, crítico, tipo de dano e flags relevantes;
- movimento: Pokémon, origem, destino, sucesso/falha, forçado ou voluntário;
- troca: Pokémon que sai, Pokémon que entra, lado, área e sucesso/falha.


### Responsabilidade principal

Construir o log oficial da rodada.

O log é a ponte entre o servidor e o cliente. Ele deve permitir que o cliente reproduza visualmente a rodada sem recalcular as regras.

### `selfs`/estado relevante

- `self.partida`
- `self.historico`
- `self.resultado`
- `self.eventos`
- `self.diffs`

### Métodos relevantes

#### `iniciar_log_rodada(rodada)`

Prepara estrutura do log da rodada.

#### `registrar_evento(tipo, dados)`

Adiciona evento ao histórico.

Eventos possíveis:

- Pokémon usou ataque;
- Pokémon se moveu;
- Pokémon trocou;
- Pokémon sofreu dano;
- Pokémon recebeu cura;
- Pokémon recebeu efeito;
- Pokémon morreu/desmaiou;
- clima mudou;
- arena mudou;
- rodada terminou;
- batalha terminou.

#### `registrar_diff(entidade, antes, depois)`

Registra diferença para resultado final.

#### `montar_historico()`

Gera histórico ordenado.

#### `montar_resultado()`

Gera diffs finais da rodada.

Resultado deve registrar:

- vida final;
- energia final;
- posição final;
- efeitos finais;
- Pokémon ativos;
- Pokémon na reserva;
- estado da partida;
- vencedor/perdedor, se houver.

#### `conferir_consistencia()`

Permite conferência especial para garantir que o cliente não termine com estado incoerente.

#### `gerar_log()`

Retorna estrutura final com:

- `historico`;
- `resultado`.

---

## 28. `SimuladorServerJogo/Batalha/FraquezasResistencia.py`

### Atualização v5 — multitype/tritype e normalização

Regras fechadas:

- Tipos múltiplos multiplicam entre si.
- Tritype existe e deve ser suportado.
- Multiplicador 0 anula dano, salvo regra futura explícita.
- STAB pode ser aplicado na ordem já definida no cálculo: dano base → Amp → tipo → STAB → crítico → defesa → Dur.
- Tipos devem ser normalizados internamente, inclusive variações com/sem acento.


### Responsabilidade principal

Carregar e aplicar a tabela de fraquezas e resistências.

Esse arquivo deve centralizar a leitura e consulta da tabela de tipos.

### `selfs`/estado relevante, caso seja classe

- `self.tabela_tipos`
- `self.multiplicadores`

### Métodos relevantes

#### `carregar_tabela()`

Carrega a tabela de fraquezas e resistências.

#### `obter_multiplicador(tipo_ataque, tipos_defensor)`

Retorna multiplicador final de dano por tipo.

#### `eh_fraco(tipo_defensor, tipo_ataque)`

Consulta fraqueza.

#### `resiste(tipo_defensor, tipo_ataque)`

Consulta resistência.

#### `eh_imune(tipo_defensor, tipo_ataque)`

Consulta imunidade, caso esse conceito exista no sistema.

### Regra importante

Esse módulo deve ser usado pelo servidor durante cálculo de dano. O cliente pode até exibir informações, mas a regra oficial deve ser aplicada no servidor.

---

## 29. `SimuladorServerJogo/Batalha/Construto.py`

### Atualização v7 — escopo mínimo dos construtos

Na v7, construtos entram apenas como classe/contrato mínimo.

Regras:

- Criar ou manter uma base `Construto` compatível com IDs, serialização e chamada de `Verificar`.
- Não implementar regras complexas de construtos nesta etapa.
- Não exigir que construtos ocupem área, criem ações, recebam dano ou apliquem efeitos reais na primeira implementação, salvo se isso já for necessário para um ataque inicial específico.
- O objetivo é evitar bloquear a arquitetura futura sem inflar a fase inicial.


### Atualização v5 — construtos como entidades de batalha

Regras fechadas:

- Construto pode entrar na fila se tiver ação própria.
- Construto tem `lado_id`, podendo ser neutro.
- Construtos podem fazer praticamente tudo que um Pokémon faz, quando suas propriedades permitirem.
- Construto pode receber dano e morrer se tiver vida.
- Alguns construtos ocupam área; outros permitem ocupação conjunta, conforme propriedades.


### Responsabilidade principal

Representar objetos de batalha que não são Pokémon, mas possuem propriedades similares.

O `Construto` é uma classe filha da classe `PokemonBatalha` ou reaproveita sua estrutura base, conforme o desenho final do código.

### `selfs`/estado relevante

- `self.id_construto`
- `self.tipo_construto`
- `self.partida`
- `self.lado_id`
- `self.posicao`
- `self.duracao`
- `self.efeitos_emitidos`
- `self.vivo`

Caso use a estrutura de `PokemonBatalha`, pode reaproveitar:

- vida;
- efeitos;
- verificação;
- posição;
- interações com área.

### Métodos relevantes

#### `Verificar()`

Atualiza duração, efeitos e estado do construto.

#### `ativar()`

Ativa comportamento principal.

#### `aplicar_efeito_area()`

Aplica efeito em área, se for o caso.

#### `ReceberDano(valor, origem=None, dados=None)`

Permite construtos com vida sofrerem dano.

#### `Morrer(dados=None)`

Remove/desativa construto.

#### `serializar()`

Envia estado do construto ao cliente/log.

### Escopo inicial

Construto não é foco principal nesta primeira fase. A arquitetura apenas deve reservar espaço para esse conceito, porque ele será importante futuramente.

---

# SERVIDOR — EXECUTES E PASSIVAS

---

## 30. `SimuladorServerJogo/Logica/Executes/ExecuteAtaques.py`

### Atualização v5 — executes e restrições atuais

Regras fechadas:

- Executes devem ser resolvidos por código/ID estável, não por nome visual.
- Execute principal recebe contexto e alvo atual; ataques globais/listados devem declarar isso explicitamente.
- Execute não altera atributo diretamente: chama métodos oficiais do Pokémon/Partida.
- Executes periféricos pertencem ao ataque atual, mas entram artificialmente no contexto de flags.
- Executes podem criar novas ações.
- Não adicionar regra antiga de ricochete, parede ou colisão física de projétil neste modelo.
- O modelo de `execute de estado de projétil` não fica fechado nesta versão; só deve ser criado se uma propriedade real do ataque exigir depois.


### Responsabilidade principal

Armazenar funções de execução de ataques.

Essas funções são chamadas pelo sistema de batalha quando um ataque precisa aplicar seu efeito real.

### Tipos de execute neste arquivo

#### Execute principal

Todo ataque deve possuir um execute principal.

Esse execute aplica o efeito principal do ataque e deve chamar métodos oficiais do `PokemonBatalha`.

Exemplos do que um execute principal pode fazer:

- `usuario.AplicarDano(alvo, valor, dados)`;
- `usuario.AplicarCura(alvo, valor, dados)`;
- `usuario.AplicarEfeito(alvo, efeito, dados)`;
- `usuario.AplicarBarreira(alvo, valor, dados)`;
- `usuario.MudarClima(clima, dados)`;
- `usuario.MudarArena(alteracao, dados)`.

#### Execute de alvificação

Execute opcional que roda antes da definição de acerto/falha.

Pode alterar dados como:

- acurácia;
- assertividade;
- lista de alvos;
- regras de mira;
- exceções de alvo;
- modificadores do sorteio de acerto.

#### Executes periféricos

Executes opcionais chamados por flags durante o curso da ação.

Eles não são chamados diretamente pelo `RodadorTurno` como efeito principal. Em vez disso, entram na lista de executes testados quando algum método oficial dispara uma flag compatível.

Exemplo conceitual:

```text
Ataque: Lâmina Noturna
Execute principal: causar dano
Execute periférico: se matar o alvo, curar 40 de vida
Flag do periférico: AoMatar ou AoMorrer
```

### Funções/métodos conceituais relevantes

#### `executar_ataque(partida, usuario, alvos, propriedades, dados_ataque)`

Entrada genérica para executar um ataque quando houver roteamento por ID.

#### `executar_alvificacao(partida, usuario, alvos, propriedades, contexto)`

Entrada genérica para executar o execute de alvificação, quando existir.

#### `obter_execute_principal(id_ataque_ou_nome)`

Resolve o nome/código do execute principal declarado nos dados.

#### `obter_execute_alvificacao(id_ataque_ou_nome)`

Resolve o execute de alvificação declarado nos dados, se existir.

#### `obter_executes_perifericos(id_ataque_ou_nome)`

Retorna executes periféricos declarados para o ataque.

#### Funções específicas por ataque ou comportamento

Cada ataque especial pode ter uma função própria, mas comportamentos comuns devem ser reaproveitados.

Exemplos conceituais:

- `executar_arranhar(...)`
- `executar_proteger(...)`
- `executar_hiper_raio(...)`
- `causar_dano_normal(...)`
- `curar_usuario_ao_matar(...)`

O nome real deve seguir o padrão já usado no projeto.

### Tipos de lógica esperada

- causar dano;
- curar;
- aplicar efeito;
- alterar clima;
- alterar arena;
- gerar projétil;
- gerar comportamento especial;
- alterar alvificação antes do acerto;
- registrar executes periféricos para flags.

### Regra importante

O execute deve atuar no servidor. O cliente não deve executar a lógica real do ataque.

## 31. `SimuladorServerJogo/Logica/Executes/PassivaAtaques.py`

### Atualização v5 — interface e poder das passivas

Passivas de ataque devem seguir interface compatível com executes periféricos: recebem contexto, flag, grupo/relação e retornam alterações/eventos.

Elas podem cancelar ação, alterar dano em diferentes momentos, disparar efeitos e criar ações, desde que tudo passe por métodos oficiais e gere log.

Novas flags podem ser criadas quando a mecânica exigir.


### Responsabilidade principal

Armazenar funções relacionadas a passivas de ataques.

Passivas de ataques são comportamentos que não são necessariamente o efeito direto principal, mas podem influenciar a batalha.

### Funções/métodos conceituais relevantes

#### `processar_passivas_ataque(evento, partida, pokemon, dados=None)`

Entrada genérica para processar passivas ligadas a ataques.

#### Funções específicas por passiva

Exemplos conceituais:

- efeito ativado quando ataque acerta;
- efeito ativado quando ataque falha;
- efeito ativado ao receber dano;
- efeito ativado no fim da rodada;
- efeito que modifica atributos temporariamente.

### Relação com flags

Passivas de ataques devem ser compatíveis com o sistema de flags.

Cada passiva precisa declarar ou permitir descobrir:

- flag de ativação;
- grupo de ativação (`self`, `mesmo_lado`, `lado_oposto`, `qualquer_lado`, `todos`);
- função execute/passiva a chamar;
- condições extras.

### Relação com `PokemonBatalha.Verificar`

Muitas passivas podem depender da verificação dos Pokémon ou da partida. A arquitetura deve permitir que passivas sejam chamadas no momento correto sem espalhar lógica duplicada.

---

## 32. `SimuladorServerJogo/Logica/Executes/PassivaItens.py`

### Atualização v5 — itens e bloqueios

Passivas de itens seguem a mesma ideia geral de flags/contexto.

Efeitos negativos podem desativar passivas quando a regra do efeito disser. Habilidades, itens e efeitos podem ter prioridade própria se necessário.


### Responsabilidade principal

Armazenar funções relacionadas a passivas de itens.

Itens podem alterar comportamento de Pokémon, dano, cura, energia, atributos ou efeitos.

### Funções/métodos conceituais relevantes

#### `processar_passivas_itens(evento, partida, pokemon, dados=None)`

Entrada genérica para processar passivas de itens equipados.

#### Funções específicas por item

Cada item pode ter uma função própria, seguindo padrão já existente no projeto.

### Relação com `Build`

As funções devem ler a `Build`/lista de itens equipáveis do Pokémon para decidir quais passivas podem ativar.

Assim como as passivas de ataques, passivas de itens devem declarar flag e grupo de ativação.

Exemplo conceitual:

```text
Item: amuleto de cura
Flag: AoReceberCura
Grupo: self
Função: aumentar Atk temporariamente ao receber cura
```

### Escopo inicial

A implementação inicial pode deixar isso apenas preparado, caso itens ainda não sejam foco.

---

# SERVIDOR — GERADORES

---

## 33. `SimuladorServerJogo/Gerais/Geradores/GeradorPokemon.py`

### Responsabilidade principal

Gerar e materializar Pokémon.

No desenho ideal, esse arquivo pertence ao servidor e não deveria ser importado pelo cliente. Porém, nesta fase, o `InicializadorBatalha` pode usá-lo temporariamente para montar o bando selvagem.

### Funções relevantes

#### `GerarPokemon(...)`

Gera um Pokémon bruto conforme espécie, nível, regras ou parâmetros do encontro.

#### `MaterializarPokemon(...)`

Transforma o Pokémon gerado em estrutura pronta para uso no sistema.

### Uso temporário no novo sistema de batalha

O `InicializadorBatalha` usará essas funções para:

- gerar membros do bando selvagem;
- materializar os Pokémon antes de enviar a inicialização ao servidor.

### Dívida técnica

Essa dependência deve ser isolada e removida futuramente, porque mistura cliente e servidor.

---

# FLUXOS PRINCIPAIS

---

## 34. Fluxo inicial de uma batalha de confronto

### Atualização v5 — fluxo ajustado

Neste fluxo, a posição inicial é definida pelo cliente, serializada em JSON e aceita como posição oficial inicial pelo servidor após criação da partida.

O clima do mundo não entra automaticamente na batalha.

Se a batalha nascer em dimensão sem contexto visual próprio, o contexto pode ser fundo preto com as áreas/botões da arena.

A IA selvagem, quando existir, será gerada no cliente e enviada como jogada do respectivo `lado_id`.


1. Jogador encontra Pokémon selvagem no mundo.
2. O sistema chama `InicializadorBatalha`.
3. O inicializador define tipo `Confronto`.
4. O inicializador recebe o Pokémon selvagem base.
5. O inicializador gera/materializa possíveis membros do bando.
6. O inicializador monta o time selvagem.
7. O inicializador procura um time apto do jogador.
8. O inicializador monta o time do jogador.
9. O inicializador define posições iniciais aleatórias na arena.
10. O inicializador monta pacote de inicialização.
11. O inicializador chama `Codigo/Server/ServerBatalha.py`.
12. `ServerBatalha.py` chama a rota de inicialização no servidor.
13. A rota chama `GerenciadorPartidas.criar_partida(...)`.
14. O servidor cria a `Partida`.
15. O servidor retorna estado inicial oficial.
16. O cliente cria `ControladorBatalha`.
17. O cliente cria/organiza `Arena`, Pokémon, HUD e controladores.
18. A batalha entra no estado de montagem de jogada.

---

## 35. Fluxo de montagem de jogada do jogador

### Atualização v5 — montagem por seleção e arraste

A montagem não depende de botão específico de preparar ação.

- Ataque: selecionar Pokémon, escolher habilidade/ataque na ficha e escolher área/alvo conforme alvificação.
- Movimento: arrastar Pokémon ativo até área livre.
- Troca de posição: arrastar Pokémon ativo até área ocupada por outro aliado.
- Troca com reserva: arrastar Pokémon ativo até Pokémon no banco/reserva.
- Fuga: clicar repetidas vezes no botão de fugir até a tela escurecer o suficiente.


1. Jogador seleciona um Pokémon aliado ativo.
2. HUD exibe ficha do Pokémon.
3. Jogador escolhe ataque ou arrasta o Pokémon.
4. Se escolher ataque:
   - `MontadorJogadas` lê propriedades do ataque.
   - Indicadores mostram alvos válidos.
   - Jogador seleciona alvo.
   - Ação de ataque é preparada.
5. Se arrastar para área aliada:
   - ação de movimento é preparada.
6. Se arrastar para Pokémon do banco:
   - ação de troca é preparada.
7. HUD mostra painel da ação preparada.
8. Energia prevista é atualizada.
9. Jogador pode preparar até 5 ações.
10. Jogador clica em pronto.
11. `ControladorBatalha` pega pacote do `MontadorJogadas`.
12. `ControladorBatalha` chama `ServerBatalha.enviar_jogada(...)`.
13. `ServerBatalha.py` envia para a rota de jogada no servidor.

---

## 36. Fluxo de resolução da rodada

### Atualização v5 — resolução com falhas registradas

Durante a resolução, uma ação inválida/falha não cancela a rodada inteira. Ela gera registro no log e a rodada segue para o próximo passo.

O alvo padrão de ataques é área. Se o Pokémon originalmente esperado saiu/morreu, o ataque continua mirando a área, salvo ataque raro explicitamente direcionado a Pokémon.


1. Servidor recebe jogadas dos lados pela rota.
2. Rota encaminha para `GerenciadorPartidas.receber_jogada(...)`.
3. `GerenciadorPartidas` localiza a `Partida`.
4. `Partida` armazena a jogada.
5. Se necessário, IA gera jogada do lado bot.
6. Quando todos os lados estão prontos, `ColetorAcoes` coleta e valida ações.
7. `ColetorAcoes` ordena as ações por `Int`, usando `Vel` como desempate.
8. `RodadorTurno` executa a rodada em passos.
9. Cada passo executa uma ação.
10. Em ação de ataque, o rodador calcula alvificação/assertividade/acerto por alvo.
11. Alvos atingidos recebem o execute principal do ataque.
12. O execute chama métodos oficiais do `PokemonBatalha`.
13. Os métodos alteram Pokémon/partida e disparam flags.
14. Executes periféricos, passivas de itens e passivas de habilidades podem ser testados por flag e grupo.
15. Ao fim de cada passo, `Verificar` roda nos Pokémon/construtos necessários.
16. Pokémon, construtos, efeitos, clima e arena são atualizados.
17. `ConstrutorLog` registra histórico.
18. `ConstrutorLog` gera resultado/diff final.
19. Servidor retorna log ao cliente.
20. Cliente entra em estado de leitura de log.

---

## 37. Fluxo de leitura e animação da rodada

### Atualização v5 — leitura por ticks visuais

A leitura/animação da rodada usa ticks visuais no cliente. Esses ticks não alteram a lógica oficial; eles apenas controlam ritmo de reprodução dos eventos do histórico.


1. Cliente recebe log do servidor.
2. `LeitorLogs` começa a ler o histórico.
3. Visualizador de logs exibe os acontecimentos.
4. `ControladorAnimacoes` executa animações correspondentes.
5. `PokemonAnimator` anima Pokémon, projéteis, dano, cura, morte, troca etc.
6. Ao fim da leitura, o cliente aplica/consolida o resultado final.
7. Se a batalha não terminou, volta para montagem de jogada.
8. Se a batalha terminou, chama `FinalizadorBatalha`.

---

## 38. Fluxo de finalização da batalha

### Atualização v7 — sem captura e sem troca automática

Regras fechadas na v7:

- Captura não entra nesta versão.
- Fuga continua como fluxo próprio de encerramento, mas captura não deve ser implementada nem simulada.
- A batalha termina normalmente quando um lado não possui nenhum Pokémon vivo apto.
- A morte de um Pokémon ativo não gera troca automática.
- Se ainda houver reserva viva, a entrada dessa reserva deve depender de ação de troca preparada em rodada posterior.


### Atualização v5 — finalização e persistência

O encerramento normal ocorre quando um lado fica sem Pokémon com vida. Fuga também encerra, reduz XP pela metade e não abre subtela de resultados.

Ao voltar ao fluxo normal, apenas vida e XP persistem.


1. Log indica que a batalha terminou.
2. `LeitorLogs` identifica evento de finalização.
3. `ControladorBatalha` chama `FinalizadorBatalha`.
4. `FinalizadorBatalha` aplica resultado oficial.
5. Subtela de resultados é exibida.
6. XP é concedido aos Pokémon do jogador.
7. Vida final dos Pokémon do jogador é atualizada.
8. Batalha é fechada.
9. Jogador retorna ao fluxo normal do jogo.

---

# CÁLCULOS OFICIAIS INICIAIS

## 39. Assertividade, acurácia e velocidade relativa

A chance de acerto de um ataque é calculada por alvo.

Base:

```text
chance = (Acuracia_efetiva_do_atacante / 100) * (Assertividade_efetiva_do_alvo / 100)
```

Valores padrão:

- `Acuracia = 100`;
- `Assertividade = 100`.

Logo, sem modificadores:

```text
1 * 1 = 1 = 100% de chance
```

A velocidade não é o atributo principal de ordem das ações. A ordem usa `Int`, e `Vel` entra como desempate. Porém, `Vel` altera a chance de acerto por meio da velocidade relativa entre atacante e alvo.

Regra da velocidade relativa:

```text
vel_media = (Vel_atacante + Vel_alvo) / 2
```

A diferença de cada Pokémon em relação à média tem um escudo de 10 pontos. Só o excedente altera acurácia/assertividade.

Exemplo:

```text
Atacante: Vel 30
Alvo: Vel 60
Média: 45
Diferença: 15
Escudo: 10
Ajuste real: 5

Acuracia do atacante: 100 - 5 = 95
Assertividade do alvo: 100 - 5 = 95
Chance final: 0.95 * 0.95 = 0.9025 = 90,25%
```

Interpretação:

- atacante abaixo da média perde acurácia;
- atacante acima da média ganha acurácia;
- alvo acima da média reduz assertividade, ficando mais difícil de acertar;
- alvo abaixo da média aumenta assertividade, ficando mais fácil de acertar.

## 40. Duração de efeitos

### Atualização v7 — decremento por passo global

Regra fechada:

- Efeitos formais decrementam duração no fim de cada passo global.
- O decremento acontece depois da execução da ação do passo e depois das verificações essenciais daquele passo.
- Efeitos aplicados durante um passo passam a existir imediatamente, mas sua duração só deve ser reduzida no fechamento daquele passo se essa for a política comum adotada na implementação. Para evitar sumiço instantâneo de efeito recém-aplicado, recomenda-se marcar o passo de criação e começar o decremento no próximo fechamento de passo.
- Estados transitórios não seguem essa regra e podem durar apenas o passo, a rodada ou o evento que os criou.


### Atualização v5 — efeitos simultâneos e stack

Efeitos formais duram em passos.

Além das fórmulas de duração, ficam fechadas as regras:

- máximo de 4 efeitos simultâneos por Pokémon;
- efeitos positivos repetidos stackam;
- efeitos negativos repetidos stackam;
- estados transitórios curtos como proteção/recuo podem continuar fora da lista formal de efeitos quando a regra exigir.


Efeitos formais duram em passos.

Aplicar efeito positivo:

```text
duracao = base_do_efeito + Mag_do_aplicador/5
```

Aplicar efeito negativo:

```text
duracao = base_do_efeito + Mag_do_aplicador/5 - Mag_do_alvo/5
```

Aplicar efeito negativo em si mesmo:

```text
duracao = base_do_efeito
```

Subefeitos como `recuado` e `protegido`, quando forem estados de 1 turno/passo, não entram como efeitos formais. Eles devem ser tratados como estados transitórios simples do Pokémon.

## 41. Dano, defesa, barreira e vampirismo

### Atualização v7 — barreira não alimenta XP nem vampirismo

Regras fechadas na v7:

- Dano absorvido por barreira não conta como dano causado à vida.
- XP por dano causado considera apenas dano efetivamente aplicado em `VidaAtual`.
- Vampirismo cura apenas com base no dano aplicado em `VidaAtual`.
- Se uma instância de dano for totalmente absorvida pela barreira, ela pode quebrar ou reduzir a barreira, mas não gera cura vampírica e não aumenta XP por dano.
- A proteção mínima de uma instância pela barreira continua valendo quando `BarreiraAtual > 0`.


### Atualização v5 — detalhes fechados de dano

Complementos fechados:

- `CrD` é multiplicador de crítico.
- `EnergiaAtual` não interfere diretamente no dano salvo execute/regra específica.
- Barreira ativa segura ao menos uma instância inteira, mesmo se o dano for muito maior que o valor restante.
- Dano absorvido pela barreira não gera vampirismo.
- Dano real em vida gera vampirismo.


Ordem conceitual do dano:

1. Dano bruto definido pelo ataque/execute.
2. Amplificação `Amp`.
3. Multiplicador de tipo.
4. STAB, se o tipo do ataque for tipo do usuário.
5. Crítico, se ocorrer.
6. Defesa (`Def` ou `SpD`).
7. Perfuração `Per`.
8. Fórmula de redução pela defesa.
9. Durabilidade `Dur`.
10. Barreira.
11. Vida.
12. Vampirismo `Vamp`.

### Amplificação

Como `Amp` começa em `0`, ela deve ser tratada como bônus percentual:

```text
dano_amplificado = dano_bruto * (1 + Amp/100)
```

### Tipo e STAB

O multiplicador de tipo vem de `FraquezasResistencia`.

STAB:

```text
se tipo_ataque pertence aos tipos do usuario:
    dano *= 1.20
```

### Crítico

A chance de crítico vem de `CrC`.

O dano crítico adicional vem de `CrD`.

Interpretação inicial recomendada:

```text
se critico:
    dano *= (1 + CrD/100)
```

### Defesa e perfuração

A defesa usada depende do estilo do dano:

- dano normal/físico usa `Def`;
- dano especial usa `SpD`.

Perfuração reduz metade do seu valor da defesa usada:

```text
defesa_efetiva = defesa - Per/2
```

Depois:

```text
dano_pos_defesa = dano * (100 / (100 + defesa_efetiva))
```

### Durabilidade

`Dur` reduz diretamente o dano final:

```text
dano_final = dano_pos_defesa - Dur
```

O dano final não deve ficar negativo, salvo regra futura explícita.

### Barreira

`BarreiraAtual` é um valor numérico acumulado que absorve dano antes da vida.

Exemplo comum:

```text
BarreiraAtual = 100
Dano = 40
Resultado: BarreiraAtual cai para 60 e a vida não recebe dano
```

Além disso, a barreira possui uma proteção mínima de instância: se existir qualquer barreira ativa, ela segura ao menos 1 instância de dano antes da vida ser afetada.

Exemplo extremo:

```text
BarreiraAtual = 1
Dano = 23848
Resultado: a barreira é consumida e a vida não recebe dano nessa instância
```

Dano absorvido pela barreira não ativa cura por `Vamp`.

### Vampirismo

`Vamp` cura o atacante com base no dano que realmente atingiu a vida do alvo.

Não funciona em dano absorvido por barreira.

---


---

# ATAQUES INICIAIS E EFEITOS EXISTENTES — V7

## 42. Camada inicial de ataques e efeitos

### Atualização v7 — escopo mantido sem captura

A v7 mantém a camada inicial de ataques e efeitos da v6, mas fecha que captura não deve entrar nesta versão. Ataques, efeitos e propriedades devem ser suficientes para dano, cura, barreira, energia, efeitos formais, movimentação, troca, log e resolução básica de confronto.


### Atualização v6 — objetivo desta seção

Esta seção transforma os CSVs atuais de ataques e efeitos em diretrizes práticas para a primeira implementação.

A intenção não é criar balanceamento definitivo. A intenção é impedir que a implementação comece sem saber como interpretar os ataques iniciais, quais efeitos já existem, quais efeitos são formais, quais são climas, quais são terrenos e quais decisões mínimas o JSON de propriedades precisa carregar desde o começo.

Fontes consideradas nesta versão:

```text
Dados/Pokemon Global Server - Ataques.csv
Dados/Pokemon Global Server - Efeitos.csv
```

Regras gerais fechadas para esta versão:

- O CSV de ataques atual possui 18 ataques iniciais.
- O CSV de efeitos atual possui 51 registros.
- Os ataques iniciais devem ser todos cobertos pelo JSON de propriedades antes de rodarem na batalha.
- Ataques sem JSON continuam proibidos de executar.
- O `Code` do CSV identifica o ataque/effect no catálogo de dados.
- O `ID` único em batalha continua sendo gerado pelo servidor conforme a família de IDs da partida.
- No catálogo de dados, se um arquivo ainda não tiver coluna `ID`, o loader pode espelhar `ID = Code` apenas para consulta estática; isso não substitui o ID único de instância gerado na batalha.
- Nomes repetidos em efeitos não são erro. O que diferencia de verdade é `Code` + `escopo`.
- Climas e terrenos não contam no limite de 4 efeitos simultâneos do Pokémon.
- O limite de 4 efeitos simultâneos vale para efeitos formais presos ao Pokémon.
- Estados transitórios curtos, como `protegido` e `recuado`, continuam fora da lista formal de efeitos, salvo se futuramente virarem efeitos do CSV.

---

## 43. Ataques iniciais do CSV

### 43.1 Regra geral dos ataques iniciais

Todo ataque inicial deve ter uma entrada no JSON de propriedades com, no mínimo:

```json
{
  "schema_version": 1,
  "code": 1,
  "nome": "Investida",
  "tipo": "normal",
  "custo": 40,
  "estilo": "alvo",
  "modo": "ativo",
  "alvificacao": {},
  "execucao": {},
  "visual": {},
  "flags": []
}
```

Campos mínimos esperados por ataque:

- `code`: código do CSV.
- `nome`: nome legível.
- `tipo`: tipo elemental do ataque.
- `custo`: custo base, podendo sobrescrever o CSV se o JSON declarar regra especial.
- `estilo`: valor do CSV, usado como orientação visual/dados simples.
- `modo`: `ativo` ou `passivo`.
- `alvificacao`: como o alvo/área é escolhido.
- `execucao`: qual execute principal e quais parâmetros ele recebe.
- `visual`: animação, projétil genérico, avanço, salto ou nenhum.
- `flags`: executes periféricos, passivas ou ativações especiais.

### 43.2 Interpretação de alvo nos ataques iniciais

Regra padrão:

- Ataques podem mirar área vazia.
- Ataques que exigem Pokémon na área devem declarar `exige_area_ocupada = true`.
- O alvo primário da maioria dos ataques é uma **área**, não diretamente um Pokémon.
- Se a área estiver vazia no momento da execução e o ataque depender de Pokémon atingido, o ataque registra evento sem efeito real.
- Ataques em fileira/coluna escolhem uma área de referência, e o servidor calcula a forma a partir dessa área.
- Ataques de cura/suporte normalmente exigem área ocupada, pois não há alvo para receber cura/efeito em área vazia.

### 43.3 Tabela interpretada dos 18 ataques iniciais

| Code | Ataque | Custo | Estilo | Interpretação inicial |
|---:|---|---:|---|---|
| 1 | Investida | 40 | alvo | Dano normal em alvo/área ocupada: `120% de Atk`. Depois, o usuário recebe recuo equivalente a `20% do dano causado`. |
| 2 | Biscoito | 25 | alvo | Cura alvo aliado/ocupado em `55% de Mag`; aplica stack de Biscoito no alvo e no usuário; cada stack no alvo aumenta a cura. |
| 3 | Enraivecer | 20 | ativa | Ação ativa no próprio usuário. Se `VidaAtual < 40% da Vida final`, aplica `Amplificado` no usuário. |
| 4 | Provocar | 20 | ativa | Ação ativa no próprio usuário. Aplica `Provocando` no usuário. |
| 5 | Proteger | 30 | alvo | Aplica estado transitório `protegido` no alvo ocupado. Não é efeito formal do CSV nesta versão. |
| 6 | Arranhar | 35 | alvo | Dano normal em alvo/área ocupada: `135% de Atk`. |
| 7 | Recarga | 25 | ativa | Ação ativa no próprio usuário. Após pagar custo, recupera `200% da Ene gasta neste ataque`. |
| 8 | Energia | 30 | alvo | Dano especial em alvo/área ocupada: `115% de SpA`. |
| 9 | Hiper Raio | 100 | alvo | Dano especial em fileira/linha: base `150% de SpA`; cada alvo adicional atingido reduz o dano base em `15% de SpA`. |
| 10 | Guilhotina | 80 | alvo | Dano normal: `80% de Atk`; se for crítico, executa alvo inimigo com `VidaAtual < 25% da Vida final` após o dano. |
| 11 | Disparo | 35 | alvo | Dano normal em alvo/área ocupada: `100% de Atk`; visual preferencial de projétil genérico. |
| 12 | Chifrada | 45 | alvo | Dano normal em alvo/área ocupada: `90% de Atk + 40% de Per`. |
| 13 | Resetar | 30 | alvo | Remove todas as variações permanentes de atributos do alvo ocupado. Pode mirar qualquer lado, conforme JSON. |
| 14 | Tankar | 60 | ativa | Aplica `Fortificado` no usuário e adiciona `20% de Mag` à menor defesa. Se crítico, também cria barreira de `20% de Mag`. |
| 15 | Estocada | 35 | alvo | Dano normal: `105% de Atk`; se for a primeira ação de ataque executada na rodada, recebe `+25% de dano`. |
| 16 | Bola Climática | 50 | alvo | Dano especial: `105% de SpA`; se houver clima ativo, usa `130% de SpA`. Causa splash de `50% do dano causado` em inimigos adjacentes. |
| 17 | Hiper Presa | 45 | alvo | Dano normal: `140% de Atk`; se crítico, alvo recua. Este ataque limita `CrC` efetivo a no máximo `80%`. |
| 18 | Acumulador | 0 | passivo | Passiva: o usuário ganha `+4 de Amplificação` toda vez que for atacado, conforme regra de flag definida no JSON/passiva. |

### 43.4 Regras específicas por ataque

#### `Investida` — Code 1

Regra inicial:

```text
dano_bruto = Atk_usuario * 1.20
```

Depois do dano:

```text
recuo_usuario = dano_causado * 0.20
```

Interpretação de `dano_causado` nesta versão:

- usar o dano que realmente reduziu `VidaAtual` do alvo;
- dano totalmente absorvido por barreira não gera recuo;
- se o ataque errar ou atingir área vazia, não há recuo.

#### `Biscoito` — Code 2

Regra inicial:

```text
cura_base = Mag_usuario * 0.55
bonus_por_stack = Mag_usuario * 0.10
bonus_por_stack_critico = Mag_usuario * 0.15
```

Fluxo:

1. Escolhe alvo ocupado, preferencialmente do mesmo `lado_id`.
2. Calcula cura com base na quantidade de stacks de Biscoito no alvo.
3. Se o evento for crítico, cada stack aumenta a cura em `15% de Mag` em vez de `10% de Mag`.
4. Aplica cura pelo método oficial `AplicarCura`.
5. Aplica 1 stack no alvo e 1 stack no usuário.
6. Se o usuário for o próprio alvo, aplicar apenas 1 stack para evitar duplicação acidental.

`Biscoito` precisa de estado próprio de stack. Esse stack pode ser armazenado como efeito/contador interno ligado ao `code` do ataque, mas não precisa ocupar uma das 4 vagas de efeitos formais se a implementação preferir tratá-lo como contador especial de ataque.

#### `Enraivecer` — Code 3

Regra inicial:

```text
se VidaAtual / Vida_final < 0.40:
    aplicar efeito Amplificado no usuário
senão:
    registrar evento sem efeito
```

Mesmo se a condição falhar, a ação foi tentada e deve poder consumir energia conforme regra normal do rodador.

#### `Provocar` — Code 4

Aplica o efeito formal `Provocando` no próprio usuário.

Regra de conflito:

```text
Provocando e Furtivo não devem coexistir no mesmo Pokémon.
```

Se um Pokémon receber `Provocando` enquanto possui `Furtivo`, a regra inicial recomendada é remover `Furtivo` e aplicar `Provocando`, pois `Provocando` tem função de exposição/atração.

#### `Proteger` — Code 5

`Proteger` aplica um estado transitório curto, não um efeito formal do CSV.

Regra inicial:

- estado: `protegido`;
- duração: até bloquear uma instância relevante ou até o fim do passo/rodada definido pelo ataque;
- função: impedir ou reduzir o efeito principal de uma próxima agressão conforme o execute;
- não ocupa uma das 4 vagas de efeitos formais.

O estado `protegido` deve aparecer no log para o cliente animar/mostrar, mesmo não sendo efeito formal.

#### `Arranhar` — Code 6

Regra inicial:

```text
dano_bruto = Atk_usuario * 1.35
```

Dano normal usa `Def` do alvo depois de tipo/STAB/crítico/perfuração conforme a ordem geral de dano.

#### `Recarga` — Code 7

Regra inicial:

```text
energia_recuperada = energia_gasta_no_ataque * 2.00
```

Como o custo inicial é `25`, o comportamento comum será:

```text
paga 25 de EnergiaAtual
recupera 50 de EnergiaAtual
```

A recuperação respeita `EneM`, salvo se o usuário estiver sob efeito que permite excedente, como `Energizado`.

Após o fim de `Energizado`, energia excedente já existente pode persistir, mas o Pokémon não deve continuar ganhando energia acima do limite normal enquanto não houver efeito ativo permitindo isso.

#### `Energia` — Code 8

Regra inicial:

```text
dano_bruto = SpA_usuario * 1.15
```

Dano especial usa `SpD` do alvo depois de tipo/STAB/crítico/perfuração conforme a ordem geral de dano.

#### `Hiper Raio` — Code 9

Ataque em fileira/linha.

Regra inicial de dano:

```text
alvos_atingidos = quantidade de Pokémon realmente atingidos na fileira
penalidade = max(0, alvos_atingidos - 1) * (SpA_usuario * 0.15)
dano_bruto_por_alvo = max(0, SpA_usuario * 1.50 - penalidade)
```

Interpretação:

- 1 alvo atingido: `150% de SpA`;
- 2 alvos atingidos: `135% de SpA` por alvo;
- 3 alvos atingidos: `120% de SpA` por alvo.

Essa regra evita que o primeiro alvo reduza o próprio dano só por existir.

#### `Guilhotina` — Code 10

Regra inicial:

```text
dano_bruto = Atk_usuario * 0.80
```

Se o ataque for crítico:

```text
se alvo é de lado oposto e VidaAtual_alvo < Vida_final_alvo * 0.25:
    alvo.Morrer()
```

A verificação de execução deve ocorrer depois do dano normal da Guilhotina, para permitir que o próprio dano coloque o alvo abaixo de 25%.

A execução deve gerar evento próprio no log, separado do evento de dano comum.

#### `Disparo` — Code 11

Regra inicial:

```text
dano_bruto = Atk_usuario * 1.00
```

Visual recomendado:

- `visual.tipo = "projetil_generico"`;
- sem ricochete;
- sem colisão de parede;
- o projétil apenas anima o evento já decidido pelo servidor.

#### `Chifrada` — Code 12

Regra inicial:

```text
dano_bruto = Atk_usuario * 0.90 + Per_usuario * 0.40
```

Esse valor entra como dano normal antes da aplicação de tipo, STAB, crítico, defesa e durabilidade.

#### `Resetar` — Code 13

Remove todas as variações permanentes/fixas de atributos do alvo.

Regra inicial:

- não remove `VidaAtual` perdida;
- não remove `EnergiaAtual` gasta;
- não remove efeitos formais;
- não remove stacks especiais, salvo se a propriedade do stack declarar que é variação permanente;
- recalcula atributos do alvo ao final do passo via `Verificar`.

#### `Tankar` — Code 14

Regra inicial:

1. Usuário ganha `Fortificado`.
2. Descobre a menor defesa final atual entre `Def` e `SpD`.
3. Aplica bônus de `20% de Mag` nessa defesa.
4. Se o ataque/ação for crítico, aplica barreira de `20% de Mag`.

Interpretação do bônus de defesa:

- deve ser uma variação temporária associada ao efeito/ação de Tankar, não alteração permanente infinita;
- se a implementação ainda não tiver duração específica para esse bônus, vincular à duração de `Fortificado`.

Como `Tankar` é ação ativa sem alvo ofensivo, seu crítico deve ser permitido apenas porque a descrição do ataque exige esse comportamento. O JSON deve declarar algo como:

```json
"pode_critico_sem_alvo": true
```

#### `Estocada` — Code 15

Regra inicial:

```text
dano_bruto = Atk_usuario * 1.05
```

Bônus:

```text
se esta for a primeira ação de ataque executada na rodada:
    dano_bruto *= 1.25
```

Movimentos e trocas antes dela não contam como ataques para essa condição.

#### `Bola Climática` — Code 16

Regra inicial:

```text
se partida.clima is None:
    dano_bruto = SpA_usuario * 1.05
senão:
    dano_bruto = SpA_usuario * 1.30
```

Depois do dano principal:

```text
dano_splash = dano_real_que_atingiu_vida_do_alvo_principal * 0.50
```

O splash atinge inimigos em áreas adjacentes à área alvo.

Regra inicial de adjacência:

- usar as 8 casas ao redor da área em uma grade 3x3 quando existirem;
- incluir diagonais;
- não atingir aliados;
- se a área principal estiver vazia ou não houver dano real no alvo principal, não há splash.

#### `Hiper Presa` — Code 17

Regra inicial:

```text
dano_bruto = Atk_usuario * 1.40
CrC_efetivo = min(CrC_usuario, 80)
```

Se for crítico, aplicar estado transitório `recuado` no alvo.

Regra inicial de `recuado`:

- não é efeito formal do CSV;
- cancela ações futuras ainda não executadas daquele Pokémon na rodada atual;
- não ocupa uma das 4 vagas de efeitos formais;
- deve gerar evento no log.

#### `Acumulador` — Code 18

`Acumulador` é o único ataque passivo do CSV inicial.

Regra inicial conforme CSV atual:

```text
ao ser atacado:
    usuário ganha +4 de Amplificação
```

Interpretação de flag:

- criar/usar uma flag própria como `AoSerAtacado` ou `AoSerAlvoDeAtaque`;
- essa flag deve disparar quando o Pokémon for alvo de uma ação de ataque executada contra sua área ou diretamente contra ele;
- se a implementação preferir limitar ao acerto real, usar `AoReceberDano`, mas isso muda a leitura de “ser atacado”; por isso a diretriz recomendada é `AoSerAtacado`.

A amplificação concedida deve entrar como variação permanente/fixa durante a batalha, salvo se a propriedade da passiva declarar duração futura.

---

## 44. Efeitos existentes do CSV

### 44.1 Separação por escopo

O CSV de efeitos atual mistura três categorias diferentes:

1. **Efeitos formais de Pokémon** — ficam presos ao Pokémon e contam no limite de 4 efeitos simultâneos.
2. **Climas** — ficam na `Partida`, em `self.clima`, e afetam regras globais enquanto ativos.
3. **Terrenos/efeitos de área** — ficam em `Partida.efeitos_area` e afetam Pokémon enquanto estiverem naquela área.

Classificação inicial por `Code`:

| Escopo | Codes | Observação |
|---|---|---|
| Efeitos formais de Pokémon | 1–34 | Entram na lista de efeitos positivos/negativos do Pokémon e contam no limite de 4. |
| Climas | 35–43 | Não contam como efeito do Pokémon; pertencem à partida. |
| Terrenos/efeitos de área | 44–51 | Não contam como efeito do Pokémon; pertencem às áreas da arena. |

### 44.2 Nomes repetidos

Existem nomes repetidos entre efeitos formais e terrenos:

- `Amaldiçoado` aparece como efeito formal no `Code 16` e como terreno no `Code 46`.
- `Energizado` aparece como efeito formal no `Code 26` e como terreno no `Code 48`.
- `Abençoado` aparece como efeito formal no `Code 19` e como terreno no `Code 50`.

Regra obrigatória:

```text
Nunca identificar efeito apenas pelo nome.
Usar sempre Code + escopo.
```

Exemplo:

```text
Energizado/code 26 = efeito formal no Pokémon.
Energizado/code 48 = terreno/efeito de área.
```

### 44.3 Efeitos negativos formais — Codes 1 a 17

| Code | Efeito | Regra inicial |
|---:|---|---|
| 1 | Queimado | Perde `1% da Vida final` por passo e recebe `35% menos cura`. |
| 2 | Dormindo | Não pode agir. Remove o efeito após sofrer um ataque. |
| 3 | Envenenado | Perde `2% da Vida final` por passo. |
| 4 | Intoxicado | Perde `3% da Vida final` por passo; a cada 2 passos libera gás ao redor, causando `2% da Vida final` a aliados no alcance. |
| 5 | Paralisado | Não pode preparar/executar ataques. Movimento e troca ainda podem ser permitidos se não houver outro bloqueio. |
| 6 | Vampirico | Inimigos que atacarem este Pokémon curam `25% do dano causado` a ele. |
| 7 | Encharcado | Ataques custam `20% mais Ene` e o Pokémon se move `20% mais devagar`. |
| 8 | Quebrado | Recebe `50% menos Durabilidade`. |
| 9 | Enfraquecido | Recebe `50% menos Amplificação`. |
| 10 | Confuso | Recebe `50% menos Assertividade`, aplicado literalmente sobre o atributo. |
| 11 | Congelado | Não pode agir e recebe `30% menos dano`. |
| 12 | Atordoado | Não pode usar passivas de itens ou habilidades. |
| 13 | Cauterizado | Não pode causar acertos críticos. |
| 14 | Descarregado | Recupera `50% menos Ene`. |
| 15 | Bloqueado | Não pode receber efeitos positivos. |
| 16 | Amaldiçoado | Efeitos negativos aplicados neste Pokémon duram `50% mais tempo`. |
| 17 | Enraizado | Não pode se mover. |

### 44.4 Efeitos positivos/formais especiais — Codes 18 a 34

| Code | Efeito | Regra inicial |
|---:|---|---|
| 18 | Regeneração | Cura `4% da Vida perdida` por passo. |
| 19 | Abençoado | Cura `3% da Vida perdida` por passo e recebe `35% mais cura`. |
| 20 | Imortal | Não pode morrer. Se receber dano mortal, fica com pelo menos 1 de vida e o efeito é removido. |
| 21 | Fortificado | Recebe `50% mais Durabilidade`. |
| 22 | Amplificado | Recebe `50% mais Amplificação`. |
| 23 | Voando | Ataques que atingiriam este Pokémon têm `40% de chance de errar`. |
| 24 | Flutuando | Ataques normais têm `40% menos assertividade` contra este Pokémon. |
| 25 | Imune | Não pode receber efeitos negativos. |
| 26 | Energizado | Recupera `50% mais Ene` e pode ultrapassar `EneM` enquanto ativo. |
| 27 | Preparado | Recebe apenas `40% do dano` e devolve dano equivalente a `40% da Vel`. |
| 28 | Provocando | É sempre alvo preferencial de ataques únicos. |
| 29 | Furtivo | Não pode ser alvo direto. |
| 30 | Encantado | Efeitos positivos aplicados neste Pokémon duram `50% mais tempo`. |
| 31 | Refletindo | Ao sofrer dano, recebe apenas `35% dele` e devolve `50% do dano original` ao atacante. |
| 32 | Evasivo | Desvia do próximo dano recebido e é removido após ativar. |
| 33 | Focado | O próximo ataque recebe bônus de acerto/assertividade conforme JSON e o efeito é removido após ativar. |
| 34 | Imparavel | Não pode recuar nem ser movido por ataques. |

### 44.5 Regras de conflito entre efeitos formais

Regras iniciais obrigatórias:

- `Provocando` e `Furtivo` não podem coexistir.
- `Bloqueado` impede entrada de efeitos positivos, salvo se o novo efeito declarar que ignora bloqueio.
- `Imune` impede entrada de efeitos negativos, salvo se o novo efeito declarar que ignora imunidade.
- `Atordoado` bloqueia passivas de itens e habilidades, mas não deve bloquear executes periféricos do ataque atual salvo regra específica.
- `Cauterizado` zera a chance de crítico do Pokémon enquanto ativo.
- `Imortal` não impede dano, apenas impede que o resultado final da instância mate o Pokémon.
- `Evasivo` deve ser consumido pela próxima instância de dano que efetivamente atingiria o Pokémon.
- `Energizado` permite ultrapassar `EneM` enquanto ativo; quando acaba, o excedente permanece, mas novas recuperações acima do limite deixam de ocorrer sem outro efeito permissivo.

### 44.6 Stack e limite de efeitos

Regras fechadas:

- Um Pokémon pode ter no máximo 4 efeitos formais simultâneos.
- Efeitos positivos repetidos stackam.
- Efeitos negativos repetidos stackam.
- O stack deve ser registrado por `code`, não apenas por nome.
- Se o Pokémon já tiver 4 efeitos formais e receber um novo efeito formal, o comportamento inicial deve ser definido no JSON do efeito/ataque.

Regra padrão para lotação:

```text
se não houver regra específica:
    bloquear entrada do novo efeito
    registrar evento de efeito_bloqueado_por_limite
```

Essa regra evita remoção acidental de efeitos importantes sem decisão explícita.

### 44.7 Climas — Codes 35 a 43

Climas pertencem à `Partida`.

Eles não entram na lista de efeitos do Pokémon e não contam no limite de 4 efeitos.

| Code | Clima | Regra inicial |
|---:|---|---|
| 35 | Chuva | Água causa `30% mais dano`; Fogo causa `30% menos dano`; `Encharcado` não perde duração; `Queimado` perde 2 passos por passo; Pokémon de Gelo curam `1% da Vida máxima` por passo. |
| 36 | Sol Forte | Água causa `30% menos dano`; Fogo causa `30% mais dano`; `Queimado` não perde duração; `Encharcado` perde 2 passos por passo; Pokémon de Gelo perdem `1% da Vida máxima` por passo. |
| 37 | Nevasca | Pokémon de Gelo recebem `30% mais Def` e `30% mais SpD`. |
| 38 | Tempestade de Areia | Pokémon que não sejam Terrestre, Metal ou Pedra perdem `1% da Vida` por passo; Terrestres recebem `20% mais Vel`. |
| 39 | Nevoa | Ataques de alvo direto recebem `30% menos assertividade`; Fantasmas recebem `25% mais Vel`. |
| 40 | Gravidade Anomala | Cósmicos recebem `15% mais Vel`; todos recebem bônus de Def/SpD por peso; Voando perde vida por passo; deslocamentos voluntários têm `50% menos Vel`. |
| 41 | Chuva Acida | Envenenado/Intoxicado não perdem duração; não-Venenosos perdem `1% da Vida` por passo; Venenosos curam `1% da Vida máxima` por passo. |
| 42 | Tempestade de Raios | Elétricos ganham Energizado; a cada 2 passos, 1 casa aleatória em cada campo recebe raio que causa `35% da Vida` como dano. |
| 43 | Noite densa | Não-Sombrios recebem `25% menos assertividade`; Sombrios recebem `20% mais Vel`. |

Regra de duração de clima:

- O CSV atual não traz `Passos Base` para clima.
- Portanto, a duração de clima deve vir do ataque/execute que criou o clima ou de regra própria da partida.
- Se um clima for aplicado sem duração explícita, usar duração padrão temporária definida em config de batalha, não no CSV.

### 44.8 Terrenos/efeitos de área — Codes 44 a 51

Terrenos pertencem a `Partida.efeitos_area`.

Eles não entram na lista de efeitos formais do Pokémon e não contam no limite de 4 efeitos.

| Code | Terreno | Regra inicial |
|---:|---|---|
| 44 | Incendiado | Enquanto estiver na área, perde `2% da Vida` por passo e recebe `50% menos cura`. |
| 45 | Contaminado | Enquanto estiver na área, perde `1% da Vida` por passo e recebe `Envenenado`; Envenenado não diminui enquanto permanecer ali. |
| 46 | Amaldiçoado | Efeitos negativos aplicados enquanto estiver na área duram `100% mais tempo`. |
| 47 | Destruido | Enquanto estiver na área, causa `20% menos dano` e recebe `20% mais dano`. |
| 48 | Energizado | Enquanto estiver na área, recupera `100% mais Ene`. |
| 49 | Sagrado | Enquanto estiver na área, causa `25% mais dano`. |
| 50 | Abençoado | Enquanto estiver na área, cura `3% da Vida perdida` por passo e recebe `50% mais cura`. |
| 51 | Elevado | Enquanto estiver na área, recebe `30% mais assertividade`; inimigos que atacarem este Pokémon recebem `30% menos assertividade`. |

Regra de aplicação:

- O terreno é avaliado no `Verificar` do Pokémon e/ou no fim do passo.
- Se o Pokémon sair da área, deixa de receber o efeito contínuo do terreno.
- Efeitos formais aplicados pelo terreno, como `Envenenado` em `Contaminado`, entram normalmente no limite de 4 efeitos do Pokémon.
- O terreno em si não ocupa vaga de efeito formal.

---

## 45. Contrato mínimo para JSON de propriedades v7

### Atualização v7 — contrato mínimo ajustado

O contrato mínimo do JSON nesta versão deve refletir as decisões fechadas:

- alvo padrão por `area_id`;
- `exige_area_ocupada` apenas quando o ataque não puder mirar área vazia;
- resolução de ocupante no servidor durante a execução;
- recálculo dinâmico de linha/coluna no momento da execução;
- custo sobrescrito no JSON quando necessário;
- ausência de captura;
- nenhum comportamento complexo de construto obrigatório.


### 45.1 Formato recomendado para alvificação

A alvificação precisa ser configurável o suficiente para cobrir os ataques iniciais e os ataques futuros sem voltar a conceitos antigos de cone, círculo, parede ou ricochete.

Formato recomendado:

```json
"alvificacao": {
  "tipo": "area",
  "quantidade_areas": 1,
  "lados_permitidos": ["qualquer_lado"],
  "exige_area_ocupada": false,
  "forma": {
    "tipo": "unica"
  }
}
```

Exemplo de alvo aliado ocupado:

```json
"alvificacao": {
  "tipo": "area",
  "quantidade_areas": 1,
  "lados_permitidos": ["mesmo_lado"],
  "exige_area_ocupada": true,
  "forma": {"tipo": "unica"}
}
```

Exemplo de fileira:

```json
"alvificacao": {
  "tipo": "area",
  "quantidade_areas": 1,
  "lados_permitidos": ["lado_oposto"],
  "exige_area_ocupada": false,
  "forma": {
    "tipo": "fileira",
    "quantidade_fileiras": 1,
    "lado_da_forma": "lado_oposto"
  }
}
```

Exemplo de forma combinada:

```json
"alvificacao": {
  "tipo": "area",
  "quantidade_areas": 1,
  "lados_permitidos": ["qualquer_lado"],
  "exige_area_ocupada": false,
  "forma": {
    "tipo": "combinada",
    "fileiras": [{"lado": "lado_oposto", "quantidade": 1}],
    "colunas": [{"lado": "qualquer_lado", "quantidade": 2}]
  }
}
```

### 45.2 Formato recomendado para execução

Exemplo de execução de dano simples:

```json
"execucao": {
  "execute_principal": "causar_dano",
  "parametros": {
    "categoria_dano": "normal",
    "formula": [
      {"atributo": "Atk", "multiplicador": 1.35}
    ]
  }
}
```

Exemplo de dano com dois atributos:

```json
"execucao": {
  "execute_principal": "causar_dano",
  "parametros": {
    "categoria_dano": "normal",
    "formula": [
      {"atributo": "Atk", "multiplicador": 0.90},
      {"atributo": "Per", "multiplicador": 0.40}
    ]
  }
}
```

Exemplo de ação ativa sem alvo ofensivo:

```json
"execucao": {
  "execute_principal": "aplicar_efeito_self",
  "pode_critico_sem_alvo": true,
  "parametros": {
    "efeito_code": 21
  }
}
```

### 45.3 Formato recomendado para efeitos no JSON

Quando um ataque aplica efeito formal:

```json
"efeitos": [
  {
    "efeito_code": 22,
    "escopo": "pokemon",
    "alvo": "usuario",
    "tipo": "positivo"
  }
]
```

Quando aplica estado transitório:

```json
"estados_transitorios": [
  {
    "nome": "recuado",
    "alvo": "alvo_principal",
    "duracao": "rodada_atual",
    "conta_como_efeito_formal": false
  }
]
```

### 45.4 Eventos mínimos de log para ataques e efeitos

Além dos eventos já previstos na v5, a v6 recomenda estes tipos mínimos:

- `ataque_usado`;
- `ataque_sem_alvo_real`;
- `ataque_errou`;
- `dano_aplicado`;
- `dano_bloqueado_por_barreira`;
- `cura_aplicada`;
- `efeito_aplicado`;
- `efeito_bloqueado`;
- `efeito_bloqueado_por_limite`;
- `efeito_stackado`;
- `efeito_removido`;
- `estado_transitorio_aplicado`;
- `estado_transitorio_consumido`;
- `clima_alterado`;
- `terreno_alterado`;
- `passiva_ativada`;
- `acao_cancelada_por_estado`;
- `execucao_por_guilhotina`;
- `splash_bola_climatica`;
- `recuo_investida`.

O HUD continua responsável por transformar esses eventos em texto visual. O servidor não deve depender de texto pronto para explicar o evento.

---

# PONTOS AINDA ABERTOS PARA VERSÕES FUTURAS

---

## 46. Detalhes que ainda serão aprofundados

### Atualização v6 — pontos que deixaram de estar totalmente abertos

Alguns pontos abaixo foram parcialmente ou totalmente fechados nesta versão:

- Formato geral do log: `historico`, `resultado`, `alertas/erros`.
- Regras iniciais de fuga: cliques repetidos escurecem a tela; fuga reduz XP pela metade e não abre subtela de resultados.
- Regra inicial de XP: dano causado + energia gasta + rodadas * 10, com multiplicador individual de 0.75 a 1.5.
- IA inicial: fica no cliente, recebe partida/estado e devolve jogada para um `lado_id`.
- Cancelamento/edição de ações preparadas: painel permite remover ação e recalcular energia.
- Visual do indicador: prévia/preparado, cores padrão e múltiplos indicadores por ação.


Este documento ainda não fecha todos os detalhes. Pontos para versões futuras:

- Schema final do JSON de propriedades dos ataques, pois a v6 já define um contrato mínimo inicial.
- Campos finais do CSV de ataques, pois a v6 já interpreta os campos atuais e aceita `Code` como base de catálogo.
- Detalhes finos dos tipos de evento do log, pois a v6 já lista eventos mínimos para ataques e efeitos.
- Balanceamento fino dos multiplicadores de dano.
- Cálculo detalhado de cura fora de efeitos simples.
- Balanceamento fino de energia, já que a v7 fecha gasto na execução, custo de movimento/troca e recuperação no fim da rodada.
- Critérios finais de desempate após `Int` e `Vel`.
- Refinamento visual e numérico da fuga.
- Balanceamento fino do XP e dos multiplicadores individuais, já usando `rodadas` no lugar de `turnos`.
- Regras de captura ficam fora da v7 e só devem ser discutidas em versão futura, se voltarem ao escopo.
- Regras de bando selvagem mais refinadas.
- Estratégia e inteligência da IA, já que a localização dela no cliente ficou fechada.
- Regras de treinador.
- Regras de PVP.
- Regras completas e balanceadas de clima, pois a v6 já classifica os climas existentes.
- Regras completas e balanceadas de efeitos de área, pois a v6 já classifica os terrenos existentes.
- Regras completas de construtos, pois a v7 mantém apenas classe/contrato mínimo.
- Refinamento visual do cancelamento/edição de ações preparadas.
- UI final dos painéis de ação.
- Polimento final do indicador de ataque/movimento/troca.

---

## 47. Diretriz final desta versão

Esta versão do documento serve como base inicial atualizada, agora já considerando os ataques iniciais, os efeitos existentes e os fechamentos da v7 sobre energia, efeitos, alvos, barreira, XP, escopo de captura e construtos.

A implementação deve respeitar a separação entre:

- cliente visual/interativo;
- arquivo único de comunicação client-servidor em `Codigo/Server/ServerBatalha.py`;
- rotas de servidor;
- servidor autoritativo;
- dados declarativos;
- executes/passivas como lógica especializada.

Além disso, a implementação desta versão deve respeitar:

- rodada em passos;
- uma ação por passo;
- `Verificar` no fim de cada passo;
- ataques com execute principal obrigatório;
- execute de alvificação antes do acerto, quando existir;
- executes periféricos por flags;
- grupos de flags `self`, `mesmo_lado`, `lado_oposto`, `qualquer_lado` e `todos`;
- cálculo de acerto por `Acuracia`, `Assertividade` e `Vel` relativa;
- ordenação principal por `Int`, com `Vel` como desempate;
- barreira como valor acumulado de absorção de dano, com proteção mínima de 1 instância quando ativa.
- energia oficial gasta na execução pelo servidor;
- movimento com custo `10`;
- troca com custo `15`;
- recuperação de energia no fim da rodada;
- duração de efeitos formais decrementada no fim de cada passo global;
- limite total de 4 efeitos formais por Pokémon;
- 5º efeito formal bloqueado, sem substituição automática;
- ataques mirando área por padrão;
- ocupante da área resolvido no momento da execução;
- linha/coluna recalculadas no momento da execução;
- dano em barreira fora do cálculo de XP e vampirismo;
- sem troca automática após morte na v7;
- sem captura na v7;
- construtos apenas como classe/contrato mínimo na v7;
- XP usando `rodadas`, não `turnos`.

A exceção temporária do `InicializadorBatalha` importando o `GeradorPokemon` do servidor deve ficar isolada e marcada como dívida técnica.

O sistema deve começar pelo modo **Confronto**, mantendo **Treinador** e **PVP** apenas previstos para expansão futura.
