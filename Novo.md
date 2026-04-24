# DiretrizesBatalha

## 1. Objetivo do documento

Este arquivo define a estrutura inicial do novo sistema de batalha do jogo.

A intenção desta versão é organizar os arquivos, responsabilidades e fluxos principais antes da implementação completa. O documento ainda não fecha todos os detalhes de balanceamento, propriedades de ataques, IA, logs ou efeitos, mas estabelece a arquitetura base para que o sistema cresça sem virar uma mistura entre cliente, servidor e dados.

Nesta fase, o foco real é o modo **Confronto**, ou seja, a batalha iniciada quando o jogador encontra um Pokémon selvagem no mundo e colide/interage com ele. Os modos **Treinador** e **PVP** devem existir como conceitos no sistema, mas não são o foco da implementação inicial.

---

## 2. Princípios gerais do sistema de batalha

### 2.1 Separação entre cliente, servidor e dados

O sistema de batalha deve ser dividido em três grandes áreas:

- **Cliente**
  - Renderiza arena, Pokémon, HUD, indicadores, animações e interação do jogador.
  - Monta a intenção da jogada do jogador.
  - Envia ações preparadas para o servidor.
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

### 2.3 Exceção temporária proibida: importação direta do servidor no cliente

Como exceção provisória, o arquivo `InicializadorBatalha` do cliente poderá importar funções do servidor para gerar/materializar Pokémon selvagens.

Isso é considerado uma solução proibida no desenho ideal, porque mistura responsabilidades entre cliente e servidor. Porém, nesta fase inicial, será aceito para não aumentar a complexidade antes da estrutura principal estar pronta.

A exceção deve ficar bem isolada e documentada para ser removida futuramente.

### 2.4 Confronto é o foco inicial

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


### 2.5 Modelo oficial de atributos do `PokemonBatalha`

Todo `PokemonBatalha` deve separar claramente **atributos padrão modificáveis** de **estados atuais**.

Essa separação é importante porque alguns valores representam a capacidade/base do Pokémon, enquanto outros representam a situação momentânea dele dentro da batalha.

### Atributos padrão

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

Observações importantes:

- `Vida` representa a **vida máxima**, não a vida atual.
- `EneM` representa a **energia máxima**, não a energia atual.
- `Ene` é o atributo usado para recuperação/geração de energia, não o estoque atual de energia.
- Alterações temporárias e permanentes devem ser armazenadas separadamente para permitir recálculo limpo no `Verificar`.

### Estados atuais

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

## 3. Mapa inicial de arquivos e áreas

Estrutura conceitual inicial:

```text
Codigo/
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

Dados/
  CSV de ataques
  JSON de propriedades dos ataques

SimuladorServerJogo/
  Batalha/
    GerenciadorPartidas.py
    Partida.py
    PokemonBatalha.py
    ColetorAcoes.py
    RodadorTurno.py
    ConstrutorLog.py
    FraquezasResistencia.py
    Construto.py

SimuladorServerJogo/
  Logica/
    Executes/
      ExecuteAtaques.py
      PassivaAtaques.py
      PassivaItens.py

SimuladorServerJogo/
  Gerais/
    Geradores/
      GeradorPokemon.py
```

Os nomes acima representam a organização lógica inicial. Caso algum nome real do projeto já exista com leve diferença, a implementação deve respeitar o padrão já usado no repositório, evitando criar duplicatas desnecessárias.

---

# CLIENTE

---

## 4. `Codigo/ModulosBatalha/InicializadorBatalha.py`

### Responsabilidade principal

Inicializar a batalha no cliente e comunicar o servidor para registrar/criar a partida.

Esse arquivo é o ponto de entrada do sistema de batalha no cliente. Ele prepara os dados iniciais necessários para a batalha começar, define o tipo de batalha e monta os times envolvidos.

### Tipos de batalha conhecidos pelo inicializador

O inicializador deve reconhecer conceitualmente:

- **Confronto**
- **Treinador**
- **PVP**

Nesta fase, a implementação deve focar em **Confronto**.

### Confronto

Confronto é o caso em que o jogador encontra um Pokémon selvagem no mundo e entra em batalha contra ele.

Fluxo básico:

1. O jogador colide/interage com um Pokémon selvagem no mundo.
2. O cliente chama o `InicializadorBatalha`.
3. O inicializador identifica que o tipo da batalha é `Confronto`.
4. O inicializador monta o time do jogador.
5. O inicializador monta o time selvagem.
6. O inicializador envia os dados para o servidor criar/registrar a partida.
7. O servidor cria a `Partida`.
8. O cliente monta arena, controlador e HUD da batalha.
9. A batalha começa.

### Montagem do time selvagem

O Pokémon encontrado no mundo é o ponto de partida do time selvagem.

No confronto, o Pokémon selvagem pode estar sozinho ou acompanhado por um bando.

A montagem do bando deve usar a tabela CSV de Pokémon em `Dados` para encontrar Pokémon da mesma linhagem evolutiva, respeitando estas regras iniciais:

- O Pokémon base do confronto sempre participa.
- O bando pode conter Pokémon da mesma linhagem.
- Os Pokémon gerados devem ter estágio evolutivo menor ou igual ao estágio do Pokémon encontrado.
  - Exemplo: se o Pokémon encontrado é `Charmeleon`, o bando pode conter `Charmander` e `Charmeleon`, mas não `Charizard`.
- O limite máximo de uma equipe é de 6 Pokémon.
- O gerador de bando só pode gerar até 3 Pokémon iguais.
- A geração do bando deve respeitar o limite total de 6 membros.
- Os Pokémon gerados para o bando devem ser materializados antes de serem enviados para a batalha.

### Uso temporário do `GeradorPokemon`

Por enquanto, o `InicializadorBatalha` poderá importar funções do servidor:

```text
SimuladorServerJogo/Gerais/Geradores/GeradorPokemon.py
```

Funções envolvidas:

- `GerarPokemon`
- `MaterializarPokemon`

Essa importação é temporária e deve ficar concentrada no inicializador, sem espalhar dependência do servidor pelo cliente.

### Montagem do time do jogador

O inicializador deve procurar uma equipe disponível do jogador.

Ordem de busca:

1. Procurar um time completo do jogador.
2. Validar se os Pokémon do time estão aptos.
3. Caso não exista time completo apto, procurar um time incompleto.
4. Caso também não exista time incompleto adequado, procurar diretamente na lista geral de Pokémon do jogador.
5. Selecionar os primeiros Pokémon aptos encontrados.
6. Montar um time temporário com esses Pokémon.

Um Pokémon é considerado apto quando:

- Possui vida maior que 0.
- Está em condição mínima de entrar em batalha.

Se o jogador não tiver nenhum Pokémon apto, a batalha não deve iniciar normalmente. Esse caso deve ser tratado de forma segura pelo inicializador ou por uma camada superior.

### Posições iniciais na arena

Após montar os dois times, o inicializador deve definir as posições iniciais dos Pokémon ativos.

Regras iniciais:

- As posições devem ser escolhidas aleatoriamente dentro das áreas disponíveis da arena.
- Apenas Pokémon ativos começam posicionados nas áreas da arena.
- Pokémon da reserva ficam fora da arena, desenhados como banco/reserva.
- A escolha aleatória não deve colocar dois Pokémon na mesma área.

---

## 5. `Codigo/ModulosBatalha/Arena.py`

### Responsabilidade principal

Representar visualmente e logicamente o contexto da arena no cliente.

A arena usa um recorte do mundo como contexto visual, mas cria uma área central própria para a batalha.

### Contexto do mundo

A arena deve pegar um contexto de:

```text
80 x 40 tiles
```

Esse contexto vem do mundo ao redor do local onde a batalha foi iniciada.

### Centro livre da arena

O centro da arena deve ter:

```text
40 x 20 tiles
```

Esse centro deve ficar livre de estruturas naturais, como:

- Árvores
- Pedras
- Plantas
- Outras estruturas naturais que atrapalhem a leitura da batalha

Essa região central é onde ficam as áreas reais de batalha.

### Áreas selecionáveis

No centro da arena devem existir dois lados de áreas.

Cada lado possui:

```text
3 x 3 áreas
```

Ou seja:

- 9 áreas para um lado.
- 9 áreas para o outro lado.
- 18 áreas selecionáveis no total.

Cada área deve funcionar como um botão selecionável.

### Relação entre área e Pokémon

Cada área pode:

- Estar vazia.
- Conter um Pokémon.

Quando uma área contém um Pokémon:

- Clicar na área seleciona o Pokémon.
- A área passa a representar o estado daquele Pokémon.
- O `MontadorJogadas` pode usar essa área como origem ou alvo de ações.

### Papel da arena no cliente

A arena deve fornecer informações para:

- Renderização do chão/contexto.
- Conversão entre posição de mundo e posição de tela.
- Seleção de áreas.
- Verificação visual de áreas ocupadas.
- Apoio ao `MontadorJogadas`.
- Apoio aos indicadores de ataque, movimento e troca.

A arena não deve decidir resultado de ataque, dano, cura ou efeito. Isso é responsabilidade do servidor.

---

## 6. `Codigo/ModulosBatalha/PokemonBatalha.py`

### Responsabilidade principal

Representar o Pokémon da batalha no cliente.

No cliente, `PokemonBatalha` é principalmente um container visual e de estado local refletido do servidor. Ele não deve ser a autoridade real das regras de batalha.

### Funções principais no cliente

O Pokémon de batalha no cliente deve:

- Guardar atributos recebidos do servidor.
- Serializar dados quando necessário.
- Atualizar dados a partir de diffs/logs.
- Renderizar o sprite do Pokémon.
- Rodar frames de animação base.
- Exibir barra de vida.
- Exibir barra de energia.
- Exibir círculos/indicadores de efeitos acima do Pokémon.
- Ser desenhado na arena quando ativo.
- Ser desenhado fora da arena quando estiver na reserva.

### Carregamento de frames

A renderização dos frames deve usar função auxiliar de carregamento de frames já existente no projeto.

O `PokemonBatalha` do cliente não deve duplicar lógica pesada de carregamento se já houver módulo auxiliar apropriado.

### Pokémon ativo e Pokémon da reserva

O mesmo tipo de objeto pode representar:

- Pokémon ativo em uma área da arena.
- Pokémon no banco/reserva fora da arena.

Diferenças:

- Pokémon ativo é desenhado em posição de mundo/arena.
- Pokémon da reserva é desenhado em painel/área de banco.
- Pokémon ativo pode ser origem de ataques e movimentos.
- Pokémon da reserva pode ser alvo de troca.

### Estado visual

O estado visual do Pokémon deve refletir o servidor e seguir o modelo oficial de atributos/estados da seção 2.5.

O cliente deve exibir ou guardar localmente, conforme necessário:

- `VidaAtual` e o atributo final `Vida`.
- `EnergiaAtual` e o atributo final `EneM`.
- `BarreiraAtual`.
- Efeitos positivos ativos.
- Efeitos negativos ativos.
- Posição na arena ou na reserva.
- Time/lado.
- Estado vivo/morto.
- Dados de `Build`/itens equipáveis quando forem necessários para ficha, ícones ou efeitos visuais.

O cliente não recalcula a regra oficial desses valores. Ele apenas reflete o estado vindo do servidor e anima as mudanças recebidas em log/diff.

---

## 7. `Codigo/ModulosGerais/PokemonAnimator.py`

### Responsabilidade principal

Controlar animações relacionadas aos Pokémon.

Esse módulo é compartilhado e deve concentrar as animações visuais envolvendo Pokémon, evitando espalhar efeitos visuais diretamente em `PokemonBatalha`, `LeitorLogs` ou `ControladorAnimacoes`.

### Animações previstas

O `PokemonAnimator` deve ser responsável por animações como:

- Morrer.
- Tomar dano.
- Receber cura.
- Exibir cartucho.
- Lançar projétil.
- Avanço.
- Salto.
- Trocar.
- Sofrer ataque.

### Relação com o sistema de batalha

O `PokemonAnimator` não decide regra.

Ele apenas executa a animação pedida pelo sistema de batalha.

Exemplo:

1. O servidor informa no log que um Pokémon sofreu dano.
2. O `LeitorLogs` lê esse evento.
3. O `ControladorAnimacoes` interpreta que precisa animar dano.
4. O `ControladorAnimacoes` chama o `PokemonAnimator`.
5. O `PokemonAnimator` executa a animação visual.

### Cartucho

O cartucho deve ser usado para exibir números ou mensagens flutuantes relacionadas a acontecimentos da batalha, como:

- Dano.
- Cura.
- Ganho de energia.
- Perda de energia.
- Texto especial de efeito, se necessário.

---

## 8. `Codigo/ModulosBatalha/PlayerBatalha.py`

### Responsabilidade principal

Controlar a interação do jogador com a batalha.

Esse arquivo deve lidar com inputs, keybinds e comandos do jogador durante a batalha.

### Responsabilidades esperadas

O `PlayerBatalha` deve controlar:

- Seleção de Pokémon.
- Seleção de ataques.
- Cancelamento de seleção.
- Confirmação de ações.
- Interação com áreas da arena.
- Interação com Pokémon da reserva.
- Atalhos de teclado.
- Estados de input durante leitura de logs.
- Bloqueio de ações quando não for momento de montar jogada.

### Relação com o `MontadorJogadas`

O `PlayerBatalha` interpreta inputs e repassa intenções para o `MontadorJogadas`.

Exemplo:

- Clique em Pokémon aliado ativo.
- Seleciona ataque na ficha.
- Move mouse sobre área.
- Solta clique no alvo.
- `MontadorJogadas` tenta preparar ação.

### Relação com o HUD

O `PlayerBatalha` também deve conversar com o HUD quando o input vier de botões, painéis ou ficha.

Ele não deve misturar regra de dano, cura ou execução real da batalha.

---

## 9. `Codigo/ModulosBatalha/ElementosHudBatalha.py`

### Responsabilidade principal

Renderizar e organizar os elementos fixos da interface da batalha.

A batalha possui câmera móvel. Por isso, arena e Pokémon ativos são desenhados no mundo e sofrem influência de posição/zoom da câmera.

O HUD, por outro lado, fica acoplado à tela.

### Elementos principais do HUD

O HUD de batalha deve incluir:

- Ficha do Pokémon selecionado.
- Botão de pronto no canto inferior direito.
- Barra de tempo no canto superior esquerdo.
- Texto indicando a rodada atual.
- Painéis de ações já preparadas na lateral esquerda.
- Visualizador de logs na lateral direita.
- Botão de fugir no canto inferior esquerdo.

### Ficha do Pokémon selecionado

Quando um Pokémon estiver selecionado, a ficha deve mostrar suas informações relevantes.

Para Pokémon aliado ativo, a ficha também deve permitir seleção de ataques.

A seleção de ataques deve alimentar o `MontadorJogadas`.

### Botão de pronto

O botão de pronto deve ser usado quando o jogador terminou de preparar sua jogada.

Ao clicar em pronto:

1. As ações preparadas são enviadas ao servidor.
2. O jogador entra em estado de espera.
3. Quando o outro lado também estiver pronto, o servidor resolve a rodada.
4. O cliente recebe e lê o log da rodada.

### Barra de tempo e rodada

A barra de tempo deve ficar no canto superior esquerdo.

Ela deve indicar o tempo restante ou estado da fase atual da rodada, conforme o modelo final for definido.

O texto de rodada deve deixar claro em qual rodada a batalha está.

### Painéis de ações preparadas

Na lateral esquerda devem aparecer as ações já preparadas pelo jogador.

Cada painel deve representar uma ação preparada, como:

- Ataque.
- Movimento.
- Troca.

Esses painéis ajudam o jogador a entender a jogada antes de confirmar.

### Visualizador de logs

Na lateral direita deve existir um painel que mostra os acontecimentos da batalha.

Esse painel é alimentado pelo `LeitorLogs`.

Ele deve exibir de forma legível os eventos relevantes da rodada.

### Botão de fugir

O botão de fugir fica no canto inferior esquerdo.

Nesta fase, ele apenas precisa existir conceitualmente como ação de saída da batalha. As regras finais de fuga podem ser detalhadas depois.

---

## 10. `Codigo/ModulosBatalha/MontadorJogadas.py`

### Responsabilidade principal

Montar as ações que compõem a jogada do jogador.

Esse arquivo controla o estado de preparação da jogada antes de ela ser enviada ao servidor.

### Conceito de jogada

Uma jogada é um conjunto de ações preparadas pelo jogador durante uma rodada.

Regras iniciais:

- O jogador pode preparar até 5 ações em uma jogada.
- Um Pokémon pode fazer até 2 ações na mesma jogada.
- A segunda ação do mesmo Pokémon tem custo aumentado em 10%.
- Preparar ação já mostra previsão de gasto de energia.
- Não é permitido preparar ação se o Pokémon não tiver energia suficiente.

### Ataques

Fluxo básico de ataque:

1. O jogador seleciona um Pokémon aliado ativo.
2. O jogador seleciona um ataque na ficha.
3. O `MontadorJogadas` entra em estado de preparação de ataque.
4. O sistema exibe indicadores de alvo.
5. O jogador escolhe o alvo permitido.
6. A ação é preparada automaticamente.

### Alvos

A seleção de alvo é altamente personalizável e depende do JSON de propriedades do ataque.

Exemplos de formatos possíveis:

- 1 alvo.
- 2 alvos.
- Alvo aliado.
- Alvo inimigo.
- Aliado e inimigo.
- 1 aliado e 2 inimigos.
- Linha.
- Coluna.
- Duas linhas.
- Duas colunas.
- Variações conforme o lado e o tipo de ataque.

O `MontadorJogadas` deve usar as propriedades do ataque para saber quais áreas/Pokémon podem ser selecionados.

### Feedback visual durante preparação

Enquanto o jogador prepara um ataque:

- Deve aparecer um fluxo de setas saindo do Pokémon até o mouse.
- Alvos disponíveis devem ter borda brilhando.
- Alvos inválidos devem ser indicados visualmente.
- Quando o mouse passa sobre uma área válida, o fluxo deve se prender ao centro da área.
- Ao soltar/clicar em uma área válida, a ação é preparada.

### Movimento

Movimento é preparado por arrastar o Pokémon.

Fluxo básico:

1. O jogador arrasta um Pokémon aliado ativo.
2. Se soltar em uma área aliada válida, prepara uma ação de movimento.
3. A ação de movimento move o Pokémon para aquela área.

### Troca

Troca também é preparada por arrastar o Pokémon.

Fluxo básico:

1. O jogador arrasta um Pokémon aliado ativo.
2. Se arrastar/soltar sobre um Pokémon do banco, prepara uma ação de troca.
3. A troca substitui o Pokémon ativo pelo Pokémon da reserva.

### Energia

O montador deve exibir prévia do gasto de energia.

Regras iniciais:

- Cada ação consome energia conforme o custo definido.
- Se o mesmo Pokémon preparar uma segunda ação, o custo da segunda ação aumenta em 10%.
- A prévia de energia deve considerar ações já preparadas.
- Não deve ser possível preparar ação se a energia projetada ficar insuficiente.

### Cancelamento e edição

A forma final de cancelar/remover ações ainda pode ser detalhada depois.

Porém, o montador deve ser preparado para permitir que ações preparadas sejam removidas ou substituídas sem quebrar o estado da jogada.

---

## 11. `Codigo/ModulosBatalha/IndicadorAtaque.py`

### Responsabilidade principal

Renderizar indicadores visuais de ações durante a preparação e depois que a ação foi preparada.

Apesar do nome inicial ser `IndicadorAtaque`, esse arquivo deve representar visualmente não apenas ataques, mas também movimento e troca, caso não seja criado outro arquivo específico para indicadores de ações.

### Estilo visual dos indicadores

Os indicadores devem ser fluxos de setas simples, com aparência parecida com:

```text
>>>>>
```

As setas devem ser levemente arredondadas, transparentes e com sensação de fluxo.

### Estados do indicador

O indicador deve ter pelo menos dois estados:

- **Preparando**
  - Mais visível.
  - Animado.
  - Segue o mouse ou se encaixa em uma área.
  - Indica se o alvo atual é válido ou inválido.

- **Preparado**
  - Mais transparente.
  - Sem animação de fluxo.
  - Representa uma ação já adicionada à jogada.

### Cores iniciais

Cores conceituais:

- Inválido: vermelho.
- Movimento: azul.
- Ataque: laranja.
- Troca: verde.

### Encaixe em áreas

Durante a preparação:

- Se o mouse estiver livre, o fluxo acompanha o mouse.
- Se o mouse passar sobre uma área válida ou relevante, o fluxo se prende ao centro da área.
- Esse encaixe deve deixar claro onde a ação será preparada se o jogador soltar/clicar.

### Relação com o `MontadorJogadas`

O `IndicadorAtaque` não decide se a ação é válida.

Ele recebe do `MontadorJogadas` as informações necessárias para desenhar:

- Origem.
- Destino.
- Tipo de ação.
- Estado de validade.
- Estado preparando/preparado.

---

## 12. `Codigo/ModulosBatalha/ControladorBatalha.py`

### Responsabilidade principal

Organizar o sistema de batalha no cliente.

O `ControladorBatalha` é o maestro da batalha no cliente. Ele conecta arena, HUD, Pokémon, jogador, montador, logs, animações e finalização.

### Responsabilidades esperadas

O controlador deve:

- Manter referência da partida client-side.
- Manter referência da arena.
- Manter referência dos Pokémon de batalha do cliente.
- Coordenar o `PlayerBatalha`.
- Coordenar o `MontadorJogadas`.
- Coordenar o `ElementosHudBatalha`.
- Coordenar o `LeitorLogs`.
- Coordenar o `ControladorAnimacoes`.
- Chamar o `FinalizadorBatalha` quando necessário.
- Controlar estados gerais da batalha.

### Estados gerais possíveis

Estados conceituais:

- Inicializando.
- Montando jogada.
- Aguardando o outro lado.
- Lendo log.
- Animando rodada.
- Finalizando.
- Encerrada.

### Papel do controlador

O controlador deve evitar que cada módulo chame todos os outros diretamente.

Ele deve funcionar como ponto central de orquestração no cliente.

---

## 13. `Codigo/ModulosBatalha/LeitorLogs.py`

### Responsabilidade principal

Ler o log retornado pelo servidor e aplicar os acontecimentos no cliente em ordem.

O servidor resolve a rodada e devolve um log. O cliente não recalcula a rodada; ele lê o que aconteceu e reproduz.

### O que o leitor deve fazer

O `LeitorLogs` deve:

- Ler eventos em ordem.
- Atualizar o estado visual/local dos Pokémon.
- Alimentar o visualizador de logs do HUD.
- Informar ao `ControladorAnimacoes` quais animações devem ocorrer.
- Aplicar diffs recebidos do servidor.
- Detectar eventos de final de batalha.

### Histórico e resultado

O log vindo do servidor deve possuir duas partes conceituais:

- **Histórico**
  - Lista ordenada do que aconteceu.
  - Serve para animação e visualização narrativa da rodada.

- **Resultado**
  - Diffs finais da rodada.
  - Serve para conferência e atualização segura do estado.

### Ritmo de leitura

O leitor deve processar os eventos com um certo tempo entre eles, para que o jogador consiga acompanhar visualmente a rodada.

A velocidade final da leitura pode ser ajustada depois.

---

## 14. `Codigo/ModulosBatalha/ControladorAnimacoes.py`

### Responsabilidade principal

Controlar a execução das animações da rodada no cliente.

Esse arquivo trabalha junto com o `LeitorLogs` e chama o `PokemonAnimator` quando necessário.

### Relação com o `LeitorLogs`

O `LeitorLogs` identifica o evento.

O `ControladorAnimacoes` decide como esse evento será animado.

Exemplo:

- Evento: Pokémon sofreu dano.
- `LeitorLogs` lê o evento.
- `ControladorAnimacoes` solicita animação de dano.
- `PokemonAnimator` executa a animação.

### Responsabilidades esperadas

O controlador de animações deve:

- Gerenciar fila de animações.
- Evitar conflito entre animações simultâneas.
- Permitir animações em sequência.
- Permitir animações paralelas quando fizer sentido.
- Avisar quando uma animação terminou.
- Manter a leitura do log sincronizada com o visual.

### Animações possíveis

Exemplos de eventos animáveis:

- Ataque.
- Projétil.
- Avanço.
- Salto.
- Dano.
- Cura.
- Morte.
- Troca.
- Aplicação de efeito.
- Movimento.

---

## 15. `Codigo/ModulosBatalha/FinalizadorBatalha.py`

### Responsabilidade principal

Finalizar a batalha no cliente quando o servidor indicar que ela terminou.

O fim da batalha deve vir do log/resultado oficial do servidor.

### Responsabilidades esperadas

O finalizador deve:

- Detectar vencedor/perdedor a partir do log.
- Chamar a subtela de resultados.
- Fechar a batalha.
- Aplicar XP aos Pokémon do jogador.
- Atualizar a vida final dos Pokémon do jogador conforme o estado pós-batalha.
- Retornar o jogador ao fluxo correto do jogo.

### Vida pós-batalha

A vida dos Pokémon do jogador após a batalha deve ser condizente com a vida restante no fim da batalha.

O cliente não deve inventar a vida final. Ele deve usar o resultado oficial retornado pelo servidor.

### XP

O ganho de XP deve ser tratado no encerramento.

Os detalhes de cálculo de XP ainda podem ser aprofundados depois.

---

## 16. `Codigo/ModulosBatalha/IA/`

### Responsabilidade principal

Guardar os arquivos de IA relacionados à batalha.

A IA ainda não é foco desta etapa, mas a arquitetura deve reservar uma pasta própria para ela.

### Uso inicial

A IA será usada principalmente em:

- Confronto contra Pokémon selvagem.
- Futuramente, batalha contra treinador.

### Função mais importante da IA

Deve existir um arquivo/função principal que:

1. Recebe a partida.
2. Recebe o lado que será controlado pela IA.
3. Analisa o estado atual.
4. Devolve as jogadas desse lado.

### Escopo inicial

A IA inicial pode ser simples.

Ela não precisa ser inteligente ou complexa nesta fase.

O importante é que a batalha consiga funcionar contra um lado controlado automaticamente.

---

# DADOS

---

## 17. CSV de ataques

### Responsabilidade principal

Listar os ataques existentes e suas informações mais diretas.

O CSV de ataques deve conter dados mais simples e visuais dos ataques.

Exemplos de informações esperadas:

- Nome.
- Descrição.
- Tipo.
- Estilo.
- Custo.
- Dados simples usados pela ficha/HUD.
- Identificador usado para conectar o ataque às propriedades e executes.

### Papel do CSV

O CSV serve como base direta para exibição e identificação dos ataques.

Ele não deve carregar toda a complexidade de alvos, animações, propriedades especiais e funcionamento detalhado.

Essas informações mais complexas pertencem ao JSON de propriedades do ataque e aos executes do servidor.

---

## 18. JSON de propriedades dos ataques

### Responsabilidade principal

Definir o comportamento detalhado dos ataques.

Esse JSON é mais intenso que o CSV e determina como o ataque funciona em termos de alvificação, animação, projétil e efeitos.

### Alvificação

A alvificação define como o jogador pode escolher os alvos do ataque.

Formatos possíveis:

- Alvo regular.
- Número definido de alvos.
- Alvo aliado.
- Alvo inimigo.
- Alvo aliado ou inimigo.
- Combinação de aliados e inimigos.
- Linha.
- Coluna.
- Duas linhas.
- Duas colunas.
- Variações específicas por lado.

### Exemplos de alvos

O JSON deve permitir casos como:

- Ataque em 1 inimigo.
- Ataque em 2 inimigos.
- Ataque em 1 aliado.
- Ataque em 1 aliado e 2 inimigos.
- Ataque em uma fileira inimiga.
- Ataque em uma coluna aliada.
- Ataque em duas colunas.
- Ataque que aceita aliados e inimigos.

### Animação de contato

O JSON também deve definir a animação de contato do ataque.

Exemplos:

- Tiro.
- Avanço.
- Salto.
- Nenhum.

### Sprite do tiro/projétil

Quando o ataque usa projétil, o JSON pode definir o sprite do tiro.

Esse sprite será usado pelo cliente para animar visualmente o ataque.

### Efeitos aplicados

O JSON pode definir:

- Efeito aplicado ao Pokémon atingido.
- Efeito aplicado ao Pokémon que utiliza o ataque.

A execução real desses efeitos deve acontecer no servidor.

O cliente apenas representa visualmente o que o servidor informar.

---

# SERVIDOR — BATALHA

---

## 19. `SimuladorServerJogo/Batalha/GerenciadorPartidas.py`

### Responsabilidade principal

Gerenciar as partidas de batalha abertas no servidor.

Esse arquivo recebe pedidos de inicialização e registra partidas.

### Responsabilidades esperadas

O gerenciador deve:

- Criar novas partidas.
- Registrar partidas por ID.
- Guardar partidas ativas.
- Localizar uma partida existente.
- Encerrar/remover partidas finalizadas.
- Servir como ponto de entrada do servidor para o início da batalha.

### Relação com o cliente

O `InicializadorBatalha` do cliente deve contatar o `GerenciadorPartidas` para criar/registrar a partida no servidor.

O servidor deve devolver as informações necessárias para o cliente montar a batalha visualmente.

---

## 20. `SimuladorServerJogo/Batalha/Partida.py`

### Responsabilidade principal

Representar a partida de batalha oficial no servidor.

Essa é a classe central do estado real da batalha.

### Dados que a partida deve guardar

A partida deve armazenar:

- ID da partida.
- Tipo da batalha.
- Lados/times.
- Pokémon de cada lado.
- Pokémon ativos.
- Pokémon na reserva.
- Clima.
- Efeitos nas áreas.
- Estado da arena.
- Rodada atual.
- Jogadas recebidas.
- Estado de finalização.
- Referências necessárias para validação e execução.

### Papel da partida

A `Partida` do servidor é a fonte da verdade.

Ela deve ser usada por:

- `ColetorAcoes`.
- `RodadorTurno`.
- `ConstrutorLog`.
- IA.
- Finalização.

---

## 21. `SimuladorServerJogo/Batalha/PokemonBatalha.py`

### Responsabilidade principal

Representar o Pokémon de batalha no servidor.

Diferente do cliente, aqui o `PokemonBatalha` possui métodos reais de regra e alteração de estado.

Essa tende a ser uma das maiores classes do sistema de batalha.

### Atributos

O Pokémon de batalha do servidor deve armazenar todos os atributos e estados relevantes para a batalha seguindo a seção 2.5 deste documento.

A lista oficial de atributos padrão é:

- `Vida`
- `Atk`
- `SpA`
- `Def`
- `SpD`
- `Mag`
- `Ene`
- `Vel`
- `Per`
- `Int`
- `Vamp`
- `CrC`
- `CrD`
- `Dur`
- `Amp`
- `EneM`
- `Acuracia`
- `Assertividade`

Além disso, o servidor deve armazenar os estados atuais:

- `VidaAtual`
- `EnergiaAtual`
- `BarreiraAtual`
- Efeitos positivos ativos.
- Efeitos negativos ativos.
- `Build`/itens equipáveis relevantes para a batalha.
- Posição.
- Time/lado.
- Estado ativo/reserva.
- Estado vivo/morto.
- Dados originais do Pokémon materializado.

### Sistema de atributos

Cada atributo padrão deve considerar três camadas:

- **Base**
  - Valor original vindo do Pokémon/materialização.

- **Variação temporária**
  - Resetada a cada verificação.
  - Reaplicada conforme efeitos ativos, condições e estados temporários.

- **Variação permanente/fixa**
  - Não é resetada normalmente.
  - Representa alterações persistentes durante a batalha, quando existirem.

Os estados atuais, como `VidaAtual`, `EnergiaAtual`, `BarreiraAtual`, posição e vivo/morto, não devem ser tratados como atributos padrão com base/variação temporária/variação permanente. Eles são valores de estado da partida.

### Verificação

O método `Verificar` é central.

Ele deve recalcular e validar estados do Pokémon, incluindo:

- Reset de variações temporárias.
- Reaplicação de efeitos.
- Validação de vida.
- Validação de energia.
- Validação de morte.
- Atualização de atributos finais.
- Checagem de condições especiais.

### Métodos esperados

Métodos principais:

- `ReceberDano`
- `AplicarDano`
- `ReceberCura`
- `AplicarCura`
- `ReceberBarreira`
- `AplicarBarreira`
- `ReceberEfeito`
- `AplicarEfeito`
- `ReceberAtributos`
- `AplicarAtributos`
- `MudarClima`
- `MudarArena`
- `GanharEnergia`
- `Mover`
- `Trocar`
- `Morrer`
- `SerMovido`
- `Verificar`

### Diferença entre receber e aplicar

A nomenclatura inicial separa:

- **Receber**
  - Algo está sendo recebido pelo Pokémon.
  - Exemplo: receber dano, receber cura, receber efeito.

- **Aplicar**
  - O Pokémon está aplicando algo em outro alvo ou em si mesmo.
  - Exemplo: aplicar dano, aplicar cura, aplicar efeito.

A implementação deve manter essa diferença clara para evitar confusão entre origem e alvo.

---

## 22. `SimuladorServerJogo/Batalha/ColetorAcoes.py`

### Responsabilidade principal

Coletar, validar e ordenar as ações enviadas pelos lados da batalha.

### O que ele recebe

O coletor recebe as ações preparadas pelos jogadores/bots.

Essas ações podem incluir:

- Ataque.
- Movimento.
- Troca.

### Validação

O coletor deve verificar se as ações são válidas antes de permitir a execução.

Validações iniciais:

- O Pokémon existe na partida.
- O Pokémon pertence ao lado correto.
- O Pokémon está apto.
- O Pokémon tem energia suficiente.
- A ação respeita o limite por jogada.
- A ação respeita o limite por Pokémon.
- O alvo é válido conforme as propriedades do ataque.
- A área de movimento é válida.
- A troca é possível com o Pokémon da reserva.
- Não há conflito básico de posição/ocupação.

### Ordenação

Depois de validar, o coletor deve ordenar as ações para o `RodadorTurno`.

A regra exata de ordenação pode ser detalhada depois, mas o coletor deve preparar uma lista organizada e confiável para execução.

---

## 23. `SimuladorServerJogo/Batalha/RodadorTurno.py`

### Responsabilidade principal

Executar a rodada/turno com base nas ações ordenadas.

O rodador é quem percorre as ações e chama os métodos corretos nos Pokémon, construtos, partida e executes.

### Fluxo básico

1. Receber ações ordenadas pelo `ColetorAcoes`.
2. Executar cada ação na ordem definida.
3. Aplicar custos.
4. Aplicar dano, cura, movimento, troca ou efeitos.
5. Atualizar clima/arena quando necessário.
6. Chamar verificações.
7. Gerar eventos para o log.
8. Informar o resultado ao `ConstrutorLog`.

### Papel do rodador

O rodador não deve ser apenas uma lista de ifs soltos.

Ele deve organizar a execução da rodada, mantendo a partida consistente.

---

## 24. `SimuladorServerJogo/Batalha/ConstrutorLog.py`

### Responsabilidade principal

Construir o log oficial da rodada.

O log é a ponte entre o servidor e o cliente.

Ele deve permitir que o cliente reproduza visualmente a rodada sem recalcular as regras.

### Estrutura conceitual do log

O log deve ser dividido em:

- **Histórico**
  - Eventos em ordem.
  - Usado pelo cliente para animação e visualização.

- **Resultado**
  - Diffs finais da rodada.
  - Usado para atualizar o estado do cliente e conferir consistência.

### Histórico

O histórico deve registrar acontecimentos como:

- Pokémon usou ataque.
- Pokémon se moveu.
- Pokémon trocou.
- Pokémon sofreu dano.
- Pokémon recebeu cura.
- Pokémon recebeu efeito.
- Pokémon morreu/desmaiou.
- Clima mudou.
- Arena mudou.
- Rodada terminou.
- Batalha terminou.

### Resultado

O resultado deve registrar o estado final relevante depois da rodada, como:

- Vida final.
- Energia final.
- Posição final.
- Efeitos finais.
- Pokémon ativos.
- Pokémon na reserva.
- Estado da partida.
- Vencedor/perdedor, se houver.

### Conferência especial

O construtor deve permitir uma conferência especial para garantir que o cliente não termine com estado incoerente.

O cliente pode animar pelo histórico, mas deve confiar no resultado final para corrigir qualquer divergência visual.

---

## 25. `SimuladorServerJogo/Batalha/FraquezasResistencia.py`

### Responsabilidade principal

Carregar e aplicar a tabela de fraquezas e resistências.

Esse arquivo deve centralizar a leitura e consulta da tabela de tipos.

### Responsabilidades esperadas

Deve permitir consultar:

- Se um tipo é fraco contra outro.
- Se um tipo resiste a outro.
- Se há imunidade, caso esse conceito exista no sistema.
- Multiplicador final de dano por tipo.

### Uso

Esse módulo deve ser usado pelo servidor durante cálculo de dano.

O cliente pode até exibir informações, mas a regra oficial deve ser aplicada no servidor.

---

## 26. `SimuladorServerJogo/Batalha/Construto.py`

### Responsabilidade principal

Representar objetos de batalha que não são Pokémon, mas possuem propriedades similares.

O `Construto` é uma classe filha da classe `PokemonBatalha` ou reaproveita sua estrutura base, conforme o desenho final do código.

### Conceito

Construtos são coisas criadas na arena que podem ter comportamento próprio.

Exemplos futuros possíveis:

- Barreira.
- Totem.
- Invocação.
- Objeto temporário.
- Estrutura com vida.
- Fonte de efeito.

### Escopo inicial

Construto não é foco principal nesta primeira fase.

A arquitetura apenas deve reservar espaço para esse conceito, porque ele será importante futuramente.

### Relação com Pokémon

Como construtos podem ter propriedades similares às de Pokémon, eles podem aproveitar parte da estrutura de:

- Vida.
- Efeitos.
- Verificação.
- Posição.
- Interações com área.

Mas construtos não devem ser tratados como Pokémon comuns quando isso quebrar regras de batalha.

---

# SERVIDOR — EXECUTES E PASSIVAS

---

## 27. `SimuladorServerJogo/Logica/Executes/ExecuteAtaques.py`

### Responsabilidade principal

Armazenar funções de execução de ataques.

Essas funções são chamadas pelo sistema de batalha quando um ataque precisa aplicar seu efeito real.

### Papel dos executes

O JSON/CSV identifica o ataque e suas propriedades.

O execute aplica a lógica específica.

Exemplos de lógica:

- Causar dano.
- Curar.
- Aplicar efeito.
- Alterar clima.
- Alterar arena.
- Gerar projétil.
- Gerar comportamento especial.

### Regra importante

O execute deve atuar no servidor.

O cliente não deve executar a lógica real do ataque.

---

## 28. `SimuladorServerJogo/Logica/Executes/PassivaAtaques.py`

### Responsabilidade principal

Armazenar funções relacionadas a passivas de ataques.

Passivas de ataques são comportamentos que não são necessariamente o efeito direto principal, mas podem influenciar a batalha.

### Exemplos de uso

- Efeito ativado quando o ataque acerta.
- Efeito ativado quando o ataque falha.
- Efeito ativado ao receber dano.
- Efeito ativado no fim da rodada.
- Efeito que modifica atributos temporariamente.

### Relação com `PokemonBatalha.Verificar`

Muitas passivas podem depender da verificação dos Pokémon ou da partida.

A arquitetura deve permitir que passivas sejam chamadas no momento correto sem espalhar lógica duplicada.

---

## 29. `SimuladorServerJogo/Logica/Executes/PassivaItens.py`

### Responsabilidade principal

Armazenar funções relacionadas a passivas de itens.

Itens podem alterar comportamento de Pokémon, dano, cura, energia, atributos ou efeitos.

### Escopo inicial

A implementação inicial pode deixar isso apenas preparado, caso itens ainda não sejam foco.

Mas o arquivo deve existir ou ser previsto para evitar misturar passivas de itens dentro de ataques ou da classe principal do Pokémon.

---

# FLUXOS PRINCIPAIS

---

## 30. Fluxo inicial de uma batalha de confronto

1. Jogador encontra Pokémon selvagem no mundo.
2. O sistema chama `InicializadorBatalha`.
3. O inicializador define tipo `Confronto`.
4. O inicializador recebe o Pokémon selvagem base.
5. O inicializador gera/materializa possíveis membros do bando.
6. O inicializador monta o time selvagem.
7. O inicializador procura um time apto do jogador.
8. O inicializador monta o time do jogador.
9. O inicializador define posições iniciais aleatórias na arena.
10. O inicializador contata o `GerenciadorPartidas`.
11. O servidor cria a `Partida`.
12. O cliente cria `ControladorBatalha`.
13. O cliente cria/organiza `Arena`, Pokémon, HUD e controladores.
14. A batalha entra no estado de montagem de jogada.

---

## 31. Fluxo de montagem de jogada do jogador

1. Jogador seleciona um Pokémon aliado ativo.
2. HUD exibe ficha do Pokémon.
3. Jogador escolhe ataque ou arrasta o Pokémon.
4. Se escolher ataque:
   - `MontadorJogadas` lê propriedades do ataque.
   - Indicadores mostram alvos válidos.
   - Jogador seleciona alvo.
   - Ação de ataque é preparada.
5. Se arrastar para área aliada:
   - Ação de movimento é preparada.
6. Se arrastar para Pokémon do banco:
   - Ação de troca é preparada.
7. HUD mostra painel da ação preparada.
8. Energia prevista é atualizada.
9. Jogador pode preparar até 5 ações.
10. Jogador clica em pronto.
11. A jogada é enviada ao servidor.

---

## 32. Fluxo de resolução da rodada

1. Servidor recebe jogadas dos lados.
2. `ColetorAcoes` coleta e valida ações.
3. IA gera jogada do lado bot, quando necessário.
4. `ColetorAcoes` ordena as ações.
5. `RodadorTurno` executa as ações.
6. Pokémon, construtos, efeitos, clima e arena são atualizados.
7. `ConstrutorLog` registra histórico.
8. `ConstrutorLog` gera resultado/diff final.
9. Servidor envia log ao cliente.
10. Cliente entra em estado de leitura de log.

---

## 33. Fluxo de leitura e animação da rodada

1. Cliente recebe log do servidor.
2. `LeitorLogs` começa a ler o histórico.
3. Visualizador de logs exibe os acontecimentos.
4. `ControladorAnimacoes` executa animações correspondentes.
5. `PokemonAnimator` anima Pokémon, projéteis, dano, cura, morte, troca etc.
6. Ao fim da leitura, o cliente aplica/consolida o resultado final.
7. Se a batalha não terminou, volta para montagem de jogada.
8. Se a batalha terminou, chama `FinalizadorBatalha`.

---

## 34. Fluxo de finalização da batalha

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

# PONTOS AINDA ABERTOS PARA VERSÕES FUTURAS

---

## 35. Detalhes que ainda serão aprofundados

Este documento ainda não fecha todos os detalhes. Pontos para versões futuras:

- Schema exato do JSON de propriedades dos ataques.
- Campos exatos do CSV de ataques.
- Formato final do log.
- Cálculo detalhado de dano.
- Cálculo detalhado de cura.
- Regras completas de energia.
- Ordem exata das ações.
- Critérios de desempate.
- Regras de fuga.
- Regras de XP.
- Regras de captura, se houver no confronto.
- Regras de bando selvagem mais refinadas.
- Regras de IA.
- Regras de treinador.
- Regras de PVP.
- Regras completas de clima.
- Regras completas de efeitos de área.
- Regras completas de construtos.
- Cancelamento/edição de ações preparadas.
- UI final dos painéis de ação.
- Visual final do indicador de ataque/movimento/troca.

---

## 36. Diretriz final desta versão

Esta versão do documento serve como base inicial para organizar a arquitetura do novo sistema de batalha.

A implementação deve respeitar a separação entre:

- Cliente visual/interativo.
- Servidor autoritativo.
- Dados declarativos.
- Executes/passivas como lógica especializada.

A exceção temporária do `InicializadorBatalha` importando o `GeradorPokemon` do servidor deve ficar isolada e marcada como dívida técnica.

O sistema deve começar pelo modo **Confronto**, mantendo **Treinador** e **PVP** apenas previstos para expansão futura.
