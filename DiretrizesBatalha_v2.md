# DiretrizesBatalha v2

## 1. Objetivo do documento

Este arquivo define a arquitetura inicial do novo sistema de batalha do jogo.

A intenção desta versão é organizar os arquivos, responsabilidades, métodos conceituais e `selfs` relevantes antes da implementação completa. O documento ainda não fecha todos os detalhes de balanceamento, dano, IA, propriedades de ataques, logs ou efeitos, mas estabelece uma base clara para que o sistema cresça sem misturar cliente, servidor e dados.

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
Codigo/Servidor/ServerBatalha.py
```

Esse arquivo funciona como adaptador de comunicação do cliente. Nenhum outro arquivo do cliente deve sair chamando diretamente `GerenciadorPartidas`, `Partida`, `RodadorTurno` ou qualquer classe interna da batalha no servidor.

Nesta versão inicial, esse arquivo precisa expor apenas duas rotas/chamadas conceituais:

1. **Inicialização de batalha**
   - Envia ao servidor os dados necessários para criar/registrar a batalha.
   - Usada pelo `InicializadorBatalha`.

2. **Envio de jogada**
   - Envia ao servidor as ações preparadas pelo jogador.
   - Usada pelo `ControladorBatalha`/`MontadorJogadas` quando o jogador clica em pronto.

As duas chamadas passam pelo arquivo de rotas no servidor antes de chegarem à lógica real da batalha.

Fluxo obrigatório:

```text
Cliente
  Codigo/ModulosBatalha/InicializadorBatalha.py
  Codigo/ModulosBatalha/ControladorBatalha.py
        ↓
  Codigo/Servidor/ServerBatalha.py
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

Observações importantes:

- `Vida` representa a **vida máxima**, não a vida atual.
- `EneM` representa a **energia máxima**, não a energia atual.
- `Ene` é o atributo usado para recuperação/geração de energia, não o estoque atual de energia.
- Alterações temporárias e permanentes devem ser armazenadas separadamente para permitir recálculo limpo no `Verificar`.

### 3.2 Estados atuais

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

Estrutura conceitual inicial:

```text
Codigo/
  Servidor/
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

## 5. `Codigo/Servidor/ServerBatalha.py`

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

#### `enviar_jogada(id_partida, lado, jogada)`

Responsável por enviar ao servidor as ações preparadas pelo jogador.

Entrada conceitual:

- `id_partida`;
- lado/time do jogador;
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

## 6. `Codigo/ModulosBatalha/InicializadorBatalha.py`

### Responsabilidade principal

Inicializar a batalha no cliente, montar os dados iniciais do confronto e chamar `Codigo/Servidor/ServerBatalha.py` para registrar/criar a partida no servidor.

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
  - Referência ao adaptador `Codigo/Servidor/ServerBatalha.py`.

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
- `self.lado`
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
- alvo aliado;
- alvo inimigo;
- aliado e inimigo;
- 1 aliado e 2 inimigos;
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
- alvo aliado;
- alvo inimigo;
- alvo aliado ou inimigo;
- combinação de aliados e inimigos;
- linha;
- coluna;
- duas linhas;
- duas colunas;
- variações específicas por lado.

### Regra importante

A execução real dos efeitos deve acontecer no servidor. O cliente usa o JSON para montar jogada e visualização, mas não para aplicar resultado oficial.

---

# SERVIDOR — ROTAS

---

## 21. `SimuladorServerJogo/Rotas/RotasBatalha.py`

### Responsabilidade principal

Receber as duas chamadas de batalha vindas do client através de `Codigo/Servidor/ServerBatalha.py` e encaminhar para `GerenciadorPartidas`.

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

## 22. `SimuladorServerJogo/Batalha/GerenciadorPartidas.py`

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

#### `receber_jogada(id_partida, lado, jogada)`

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

#### `receber_jogada(lado, jogada)`

Recebe jogada de um lado.

Se todos os lados necessários já jogaram, chama resolução da rodada.

#### `todos_lados_prontos()`

Verifica se a rodada já pode ser resolvida.

#### `resolver_rodada()`

Fluxo principal de rodada:

1. Coleta ações.
2. Valida ações.
3. Ordena ações.
4. Roda turno.
5. Verifica estado final.
6. Gera log.
7. Incrementa rodada se a batalha continuar.

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

### Responsabilidade principal

Representar o Pokémon de batalha no servidor.

Diferente do cliente, aqui o `PokemonBatalha` possui métodos reais de regra e alteração de estado. Essa tende a ser uma das maiores classes do sistema de batalha.

### `selfs`/estado relevante

Identidade e vínculo:

- `self.id_batalha`
- `self.id_original`
- `self.nome`
- `self.especie`
- `self.lado`
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

Deve considerar barreira, defesa, redução, efeitos e morte conforme as regras detalhadas futuras.

#### `AplicarDano(alvo, valor, dados=None)`

Usado quando este Pokémon causa dano em outro alvo.

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

#### `AplicarEfeito(alvo, efeito, dados=None)`

Aplica efeito em alvo.

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

---

## 25. `SimuladorServerJogo/Batalha/ColetorAcoes.py`

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

A regra exata de ordenação pode ser detalhada depois, mas o coletor deve preparar uma lista organizada e confiável para execução.

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

### Responsabilidade principal

Executar a rodada/turno com base nas ações ordenadas.

O rodador é quem percorre as ações e chama os métodos corretos nos Pokémon, construtos, partida e executes.

### `selfs`/estado relevante

- `self.partida`
- `self.acoes_ordenadas`
- `self.eventos_rodada`
- `self.construtor_log`
- `self.executador_ataques`, se houver adaptador para `ExecuteAtaques`.

### Métodos relevantes

#### `rodar(acoes_ordenadas)`

Executa a rodada completa.

Fluxo básico:

1. Receber ações ordenadas pelo `ColetorAcoes`.
2. Executar cada ação na ordem definida.
3. Aplicar custos.
4. Aplicar dano, cura, movimento, troca ou efeitos.
5. Atualizar clima/arena quando necessário.
6. Chamar verificações.
7. Gerar eventos para o log.
8. Informar o resultado ao `ConstrutorLog`.

#### `executar_acao(acao)`

Decide o tipo da ação e chama método específico.

#### `executar_ataque(acao)`

Executa ataque via dados/propriedades/execute.

#### `executar_movimento(acao)`

Executa movimento.

#### `executar_troca(acao)`

Executa troca.

#### `aplicar_custo(acao)`

Remove energia/custo da ação.

#### `chamar_verificacoes()`

Chama `Verificar` em Pokémon, construtos e partida conforme ordem definida futuramente.

#### `registrar_evento(evento)`

Acumula evento para o log.

#### `finalizar_rodada()`

Fecha a execução da rodada e entrega eventos ao `ConstrutorLog`.

---

## 27. `SimuladorServerJogo/Batalha/ConstrutorLog.py`

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

### Responsabilidade principal

Representar objetos de batalha que não são Pokémon, mas possuem propriedades similares.

O `Construto` é uma classe filha da classe `PokemonBatalha` ou reaproveita sua estrutura base, conforme o desenho final do código.

### `selfs`/estado relevante

- `self.id_construto`
- `self.tipo_construto`
- `self.partida`
- `self.lado`
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

### Responsabilidade principal

Armazenar funções de execução de ataques.

Essas funções são chamadas pelo sistema de batalha quando um ataque precisa aplicar seu efeito real.

### Funções/métodos conceituais relevantes

#### `executar_ataque(partida, usuario, alvos, propriedades, dados_ataque)`

Entrada genérica para executar um ataque quando houver roteamento por ID.

#### Funções específicas por ataque

Cada ataque especial pode ter uma função própria.

Exemplos conceituais:

- `executar_arranhar(...)`
- `executar_proteger(...)`
- `executar_hiper_raio(...)`

O nome real deve seguir o padrão já usado no projeto.

### Tipos de lógica esperada

- causar dano;
- curar;
- aplicar efeito;
- alterar clima;
- alterar arena;
- gerar projétil;
- gerar comportamento especial.

### Regra importante

O execute deve atuar no servidor. O cliente não deve executar a lógica real do ataque.

---

## 31. `SimuladorServerJogo/Logica/Executes/PassivaAtaques.py`

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

### Relação com `PokemonBatalha.Verificar`

Muitas passivas podem depender da verificação dos Pokémon ou da partida. A arquitetura deve permitir que passivas sejam chamadas no momento correto sem espalhar lógica duplicada.

---

## 32. `SimuladorServerJogo/Logica/Executes/PassivaItens.py`

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
11. O inicializador chama `Codigo/Servidor/ServerBatalha.py`.
12. `ServerBatalha.py` chama a rota de inicialização no servidor.
13. A rota chama `GerenciadorPartidas.criar_partida(...)`.
14. O servidor cria a `Partida`.
15. O servidor retorna estado inicial oficial.
16. O cliente cria `ControladorBatalha`.
17. O cliente cria/organiza `Arena`, Pokémon, HUD e controladores.
18. A batalha entra no estado de montagem de jogada.

---

## 35. Fluxo de montagem de jogada do jogador

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

1. Servidor recebe jogadas dos lados pela rota.
2. Rota encaminha para `GerenciadorPartidas.receber_jogada(...)`.
3. `GerenciadorPartidas` localiza a `Partida`.
4. `Partida` armazena a jogada.
5. Se necessário, IA gera jogada do lado bot.
6. Quando todos os lados estão prontos, `ColetorAcoes` coleta e valida ações.
7. `ColetorAcoes` ordena as ações.
8. `RodadorTurno` executa as ações.
9. Pokémon, construtos, efeitos, clima e arena são atualizados.
10. `ConstrutorLog` registra histórico.
11. `ConstrutorLog` gera resultado/diff final.
12. Servidor retorna log ao cliente.
13. Cliente entra em estado de leitura de log.

---

## 37. Fluxo de leitura e animação da rodada

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

## 39. Detalhes que ainda serão aprofundados

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

## 40. Diretriz final desta versão

Esta versão do documento serve como base inicial para organizar a arquitetura do novo sistema de batalha.

A implementação deve respeitar a separação entre:

- cliente visual/interativo;
- arquivo único de comunicação client-servidor em `Codigo/Servidor/ServerBatalha.py`;
- rotas de servidor;
- servidor autoritativo;
- dados declarativos;
- executes/passivas como lógica especializada.

A exceção temporária do `InicializadorBatalha` importando o `GeradorPokemon` do servidor deve ficar isolada e marcada como dívida técnica.

O sistema deve começar pelo modo **Confronto**, mantendo **Treinador** e **PVP** apenas previstos para expansão futura.
