# Arquitetura da Batalha

**Projeto:** Pokemon Global Server  
**Base de verdade:** Diretrizes de Batalha consolidadas em 2026-04-22  
**Objetivo deste arquivo:** definir a arquitetura-alvo enxuta da nova batalha, com foco em arquivos, classes, responsabilidades e métodos principais, sem código real.

---

## 1. Critério usado para esta arquitetura

Esta arquitetura foi montada cruzando:

1. as diretrizes consolidadas da batalha, que definem o modelo novo como **servidor autoritativo por ticks**, com **Partida** como dona do estado, **cliente como montador/animação**, **JSON técnico como fonte de verdade**, **ações como objetos temporais**, **objetos de batalha com vida própria**, e **histórico rico por eventos**;
2. a estrutura real atual do projeto, onde já existem peças reaproveitáveis importantes como `MontadorJogada.py`, `LeitorLogs.py`, `PokemonAnimator.py`, `PokemonBatalha.py`, `ObjetoBatalha.py`, `SimuladorFisica.py`, `GerenciadorBatalhas.py` e `SistemaBatalha.py`.

A ideia aqui **não** é inflar o projeto com dezenas de arquivos desnecessários.  
A ideia é manter uma árvore **compacta, implementável e fiel às diretrizes**.

---

## 2. Arquivos extras que valem a pena existir

A estrutura proposta por você já está boa. Eu só julgo que **2 arquivos extras** melhoram bastante a clareza sem burocratizar:

### 2.1. `SimuladorServerJogo/Batalha/FisicaBatalha.py`

**Motivo:** a física da nova batalha é relevante demais para ficar espalhada entre `MotorAcoes` e `DetectorColisoes`.  
O projeto atual já tem `SimuladorFisica.py`, então faz sentido manter um arquivo equivalente no novo modelo, mas mais limpo e com as fórmulas oficiais novas.

### 2.2. `SimuladorServerJogo/Batalha/EstadosPartida.py`

**Motivo:** as diretrizes exigem estado macro formal da partida (`montando`, `aguardando`, `rodando`, `animando`, `encerrada`).  
Centralizar isso evita string solta espalhada no client e no server.

Fora esses dois, **eu não adicionaria mais nada agora**.

---

## 3. Visão geral da árvore final

```text
Dados/
├── Pokemon Global Server - Ataques.csv
├── Pokemon Global Server - PropriedadesAtaque.json
└── Pokemon Global Server - Efeitos.csv

Codigo/
├── ModulosGerais/
│   └── PokemonAnimator.py
├── ModulosBatalha/
│   ├── Arena.py
│   ├── ElementosHudBatalha.py
│   ├── InicializadorBatalha.py
│   ├── FinalizadorBatalha.py
│   ├── ControladorBatalha.py
│   ├── MontadorJogada.py
│   ├── LeitorLogs.py
│   ├── PlayerBatalha.py
│   ├── ExecutorAnimacao.py
│   ├── IndicadoresAcoes.py
│   └── IA/
│       ├── BotBatalha.py
│       ├── AvaliadorAcoesIA.py
│       └── GeradorJogadasIA.py
├── Geradores/
│   └── PokemonBatalha.py
└── Paineis/
    ├── FichaPokemonBatalha.py
    └── PainelAcoes.py

SimuladorServerJogo/
├── Batalha/
│   ├── EstadosPartida.py
│   ├── GerenciadorPartidas.py
│   ├── Partida.py
│   ├── InicializadorPartida.py
│   ├── ObjetoBatalha.py
│   ├── PokemonBatalha.py
│   ├── ProjetilBatalha.py
│   ├── ParedeBatalha.py
│   ├── ConstrutoBatalha.py
│   ├── FraquezasResistencias.py
│   ├── FisicaBatalha.py
│   ├── MotorAcoes.py
│   ├── DetectorColisoes.py
│   ├── ExecutorTurnos.py
│   ├── ColetorJogadas.py
│   ├── LogBatalha.py
│   ├── ConstrutorAcao.py
│   └── ConstrutorAtaque.py
└── Logica/
    └── Executes/
        └── ExecuteAtaques.py
```

---

## 4. Regras de fronteira entre os arquivos

Antes de listar classe e método, estas fronteiras precisam ficar fechadas:

### 4.1. Ataque não é Ação
- **Ataque** é a definição técnica lida do JSON.
- **Ação** é a ocorrência concreta daquele uso dentro do turno.

### 4.2. Partida é dona do estado
- `Partida` guarda estado vivo.
- `ExecutorTurnos` só roda o ciclo.
- `LogBatalha` só registra.

### 4.3. Cliente não decide resultado
- cliente prepara;
- servidor valida e simula;
- cliente anima e aplica diff final.

### 4.4. Execute é ponte obrigatória
- ação dispara execute;
- existem apenas **execute principal**, **execute de estado** e **executes periféricos**;
- execute principal resolve o núcleo do ataque, inclusive colisão com Pokémon quando for o caso;
- execute de estado cuida de mudança interna da própria ação/objeto ou de ação derivada quando isso não deve poluir o principal;
- executes periféricos são enviados junto ao método chamado e rodam depois da flag correspondente dentro desse método;
- existe um conjunto único de flags do sistema;
- execute chama métodos do pokémon/objeto;
- método altera estado.

### 4.5. Fluxos antigos deixam de ser base da batalha
- `LeitorFluxos.py` e `Fluxos.json` deixam de ser base do combate;
- preview nasce do JSON técnico do ataque;
- o legado de fluxo só pode sobreviver fora do núcleo da nova batalha.

---

# 5. DADOS

## 5.1. `Dados/Pokemon Global Server - Ataques.csv`

### Papel
Arquivo humano e informativo para leitura do jogador e UI.

### Conteúdo esperado
- nome do ataque;
- tipo elemental;
- custo;
- estilo visível;
- intervalo;
- descrição simples.

### Observação
Este arquivo **não** decide a execução real do golpe.

---

## 5.2. `Dados/Pokemon Global Server - PropriedadesAtaque.json`

### Papel
Fonte de verdade das propriedades técnicas que entram no construtor dos ataques.

### Conteúdo esperado
- id técnico do ataque;
- code textual opcional;
- tipo;
- estilo;
- custo;
- intervalo de ativação;
- multiplicador de dano;
- dados de alvo/alcance;
- dados físicos;
- propriedades de colisão;
- propriedades de ricochete;
- propriedades de atravessar;
- comportamento de fim por tipo de colisão quando o estilo usar projétil;
- dados visuais mínimos para preview e animação;
- gif/efeito visual do ataque sobre o alvo, quando houver;
- imagem de projétil, quando o estilo usar tiro;
- execute principal;
- execute de estado, quando houver;
- lista de executes periféricos, quando houver.

### Observação crítica
Flags internas do fluxo não precisam viver nesse JSON base.
O construtor continua responsável por ler os nomes declarados no dado técnico e acoplar o comportamento real da ação.

### Leitura arquitetural
`PropriedadesAtaque` + envio do jogador (direção, alvos quando couber, intensidade quando couber) entram no construtor.  
O construtor monta a ação com seu tick de ativação/construção, soma o intervalo e define o tick de início da ação antes de colocá-la na fila simples do turno.  
Quando a ação roda, os executes podem chamar métodos, mutar a própria ação, criar novas ações e criar objetos.

---

# 6. CLIENTE

## 6.1. `Codigo/ModulosGerais/PokemonAnimator.py`

### Classe: `PokemonAnimator`
Responsável por animar o pokémon visual a partir do histórico da batalha.

### Métodos principais
- `atualizar()`: avança estados internos de animação.
- `renderizar()`: desenha corpo, flashes, projéteis e efeitos em tela.
- `tomar_dano()`: toca animação de dano recebido.
- `tomar_cura()`: toca animação de cura.
- `cartucho()`: mostra números flutuantes de dano, cura ou informação.
- `buffar()`: anima ganho de atributo/estado positivo.
- `nerfar()`: anima perda de atributo/estado negativo.
- `mover()`: anima deslocamento entre posições do histórico.
- `animar_morte()`: anima derrota/morte do pokémon.
- `lancar_projetil()`: anima criação visual de projétil.
- `animar_area()`: anima impacto/efeito de ataques em área.
- `animar_zona()`: anima impacto/efeito de ataques de zona.
- `animar_laser()`: anima faixa e impacto de ataques de laser.
- `sofrer_ataque_efeito()`: reproduz gif ou efeito especial sobre o pokémon.
- `esta_movendo()`: informa se ainda há deslocamento visual em andamento.
- `restaurar_visual_corpo()`: limpa deformações temporárias após animações.

### Observação
Este arquivo já existe e deve sobreviver.

---

## 6.2. `Codigo/Geradores/PokemonBatalha.py`

### Classe: `PokemonBatalha`
Representação visual do pokémon em campo no client.

### Papel
- guardar sprite, posição visual, dados públicos e estado visual;
- conversar com `PokemonAnimator`;
- expor dados para ficha, HUD e clique do jogador.

### Métodos principais
- `atualizar()`: sincroniza estado visual atual.
- `renderizar()`: desenha o pokémon em campo.
- `renderizar_construto()`: desenha fantasma/construto visual quando necessário.
- `montar_dados_ficha()`: devolve dados prontos para a ficha.
- `obter_ataques_ficha()`: devolve ataques já no formato da UI.
- `obter_itens_ficha()`: devolve itens já no formato da UI.
- `obter_valor_base_ficha()`: lê atributo base visível.
- `obter_valor_ficha()`: lê atributo visível com modificações locais de apresentação.
- `definir_variacao_ficha()`: aplica previsão visual de alteração de atributo.
- `alterar_variacao_ficha()`: soma variação visual temporária.
- `raio_px()`: devolve o raio visual em pixels.
- `centro_tela()`: devolve centro visual atual para clique/animação.

---

## 6.3. `Codigo/ModulosBatalha/Arena.py`

### Classe: `Arena`
Responsável pela arena visual do client.

### Papel
- desenhar chão, grid e limites;
- renderizar efeitos de tile;
- oferecer referência espacial para preview, clique e animação.

### Métodos principais
- `__init__()`: recebe dimensões, centro, tiles e visual base.
- `_montar()`: monta estruturas internas da arena.
- `_carregar_sprite()`: carrega imagens da arena e do piso.
- `_desenhar_grid_arena()`: desenha grid visual.
- `_retangulo_arena()`: devolve área útil da arena.
- `renderizar()`: desenha a arena pronta.

---

## 6.4. `Codigo/ModulosBatalha/ElementosHudBatalha.py`

### Classe: `ElementosHudBatalha`
Camada de HUD específica da batalha.

### Papel
- mostrar tempo, botões, confirmações e fugas;
- mediar a interface de montagem das jogadas sem botão separado de preparar;
- integrar com ficha, painel de ações e botão de pronto.

### Métodos principais
- `filtrar_eventos_camera()`: filtra eventos relevantes para a HUD.
- `_garantir_layout()`: monta ou atualiza layout.
- `_processar_selecao()`: processa clique de seleção vindo da HUD.
- `_enviar_pronto()`: envia as ações prontas ao controlador quando o jogador confirmar o turno.
- `_atualizar_tempo_rodada()`: controla cronômetro local de rodada.
- `_sincronizar_tempo_rodada()`: ajusta cronômetro com o servidor.
- `desenhar()`: renderiza a HUD inteira.

---

## 6.5. `Codigo/ModulosBatalha/InicializadorBatalha.py`

### Classe: `InicializadorBatalha`
Cria o estado local inicial da batalha a partir do snapshot autoritativo.

### Papel
- materializar o estado local a partir do snapshot autoritativo;
- escolher/renderizar os ativos locais quando isso fizer parte do fluxo de entrada do client;
- criar pokémons visuais;
- definir posições iniciais na arena.

### Métodos principais
- `inicializar()`: rotina principal de montagem inicial.
- `escolher_time_confronto()`: decide time usado no confronto.
- `escolher_time_confronto_com_indice()`: mesma lógica com índice explícito.
- `times_completos()`: garante integridade mínima dos times.
- `time_tem_pokemon_vivo()`: valida se time ainda está utilizável.
- `pokemon_tem_vida()`: utilitário rápido de validação.
- `_carregar_base_pokemons()`: busca base necessária para materialização visual.
- `_materializar_confrontado()`: monta pokémon visual do oponente.
- `criar_bando()`: cria formações extras quando necessário.

### Função auxiliar
- `pontos_lados_arena()`: calcula pontos iniciais de cada lado na arena.

---

## 6.6. `Codigo/ModulosBatalha/FinalizadorBatalha.py`

### Classe: `FinalizadorBatalha`
Fecha o turno ou a batalha do lado do client aplicando o resultado recebido.

### Papel
- preparar resumo final;
- aplicar diff local;
- ajustar inventário visual, times e estado final;
- abrir subtela final quando a batalha acabar.

### Métodos principais
- `pronto()`: informa se já existe resultado pronto para aplicação.
- `preparar_resumo()`: monta resumo de vitória, derrota e estado final.
- `criar_subtela()`: cria a interface final/resumo.
- `concluir()`: executa o fechamento completo local.
- `_aplicar_resultado_local()`: aplica resultado ao estado do client usando diff apenas do que mudou.
- `_pokemon_com_resultado()`: encontra pokémon final correspondente.
- `_mapa_resumo_final()`: organiza resumo completo da batalha.
- `_montar_itens_lado()`: prepara itens do lado para exibição final.

---

## 6.7. `Codigo/ModulosBatalha/ControladorBatalha.py`

### Classe: `ControladorBatalha`
Maestro do lado client.

### Papel
- segurar o ciclo local da batalha;
- coordenar arena, HUD, seleção, montagem, replay, leitura de logs e aplicação de estado;
- ser o único ponto de integração entre UI e rede.

### Métodos principais
- `obter_regras_batalha()`: lê regras públicas necessárias ao client.
- `_inicializar_times()`: monta times visuais locais.
- `_criar_reservas_visuais()`: materializa reservas do lado do jogador.
- `_criar_pokemon_visual_inicial()`: cria ativos iniciais em campo.
- `selecionar_pokemon()`: seleciona pokémon por objeto ou id.
- `selecionar_por_mouse()`: seleciona por clique na arena.
- `limpar_selecao()`: limpa seleção atual.
- `pokemon_no_ponto()`: identifica pokémon sob o cursor.
- `pokemon_eh_controlavel()`: verifica se o pokémon pode ser controlado localmente.
- `mapa_pokemons()`: devolve mapa atual dos pokémons visuais.
- `atualizar_estado_servidor()`: sincroniza estado novo vindo do server.
- `aplicar_snapshot_replay()`: aplica snapshot de replay/log.
- `esta_reproduzindo_logs()`: informa se o turno está em animação.
- `listar_logs_publicos()`: devolve logs públicos já traduzidos.
- `obter_log_publico()`: devolve log específico.
- `atualizar()`: tick geral do controlador.
- `renderizar()`: desenha a cena de batalha completa.
- `batalha_encerrada()`: informa se a batalha terminou.
- `resultado_batalha_atual()`: devolve resultado final atual.

---

## 6.8. `Codigo/ModulosBatalha/MontadorJogada.py`

### Classe: `MontadorJogada`
Responsável por montar a intenção local de jogadas do turno.

### Papel
- limitar ações por lado e por pokémon;
- impedir ações repetidas inválidas;
- reservar energia visual;
- ordenar ações por criação;
- calcular posição fantasma para previews posteriores.

### Métodos principais
- `pode_adicionar()`: verifica se a nova ação é válida localmente.
- `adicionar()`: adiciona ação preparada.
- `listar()`: devolve ações atuais do turno.
- `listar_referencias()`: devolve ids/refs úteis para UI.
- `limpar()`: limpa todas as ações preparadas.
- `remover()`: remove ação específica.
- `selecionar()`: marca ação do painel como selecionada.
- `selecionado_id()`: devolve id da ação selecionada.
- `custo_reservado()`: calcula energia já comprometida.
- `quantidade_executor()`: conta quantas ações o pokémon já preparou.
- `possui_acao_executor()`: informa se o executor já tem certa ação.
- `posicao_virtual_executor()`: calcula origem fantasma prevista.
- `resolver_visuais()`: devolve dados prontos para indicadores e painel.

---

## 6.9. `Codigo/ModulosBatalha/LeitorLogs.py`

### Classe: `LeitorLogs`
Lê o histórico técnico enviado pelo servidor e transforma isso em animação local.

### Papel
- reproduzir o turno após o pacote final do server;
- alimentar animadores;
- sincronizar vida, barreira, energia, movimento e efeitos;
- aplicar apenas os valores finais já calculados pelo servidor, sem refazer contas locais;
- finalizar a reprodução e devolver o controle ao jogador.

### Métodos principais
- `reproduzir()`: inicia reprodução do turno.
- `atualizar()`: avança a reprodução.
- `cancelar()`: interrompe leitura atual.
- `esta_ativo()`: informa se ainda está lendo.
- `estado_visualizacao()`: devolve progresso e estado.
- `_processar_eventos_ate_tick()`: processa eventos até o tick atual.
- `_processar_evento()`: roteia o tipo do evento.
- `_processar_acao()`: aplica início/fim/cancelamento de ação.
- `_processar_movimento()`: sincroniza deslocamento.
- `_processar_dano()`: aplica dano visual.
- `_processar_cura()`: aplica cura visual.
- `_processar_barreira()`: ajusta barreira visual.
- `_processar_energia()`: ajusta energia visual.
- `_processar_efeito()`: aplica ou remove efeito visual.
- `_processar_objeto()`: sincroniza projéteis/construtos.
- `_processar_fim_turno()`: encerra reprodução e prepara diff final.

---

## 6.10. `Codigo/ModulosBatalha/PlayerBatalha.py`

### Classe: `PlayerBatalha`
Representa o lado local na fase de preparação.

### Papel
- organizar slots controláveis;
- apontar ativos e reservas do lado do jogador;
- servir de apoio para montagem de jogadas, IA e seleção.

### Métodos principais
- `preparar_slots()`: organiza slots do lado local.
- `definir_ativos()`: define quais pokémons estão em campo.

### Observação
Este arquivo deve permanecer simples. Não deve virar controlador geral da batalha.

---

## 6.11. `Codigo/ModulosBatalha/ExecutorAnimacao.py`

### Classe: `ExecutorAnimacao`
Arquivo novo do client para isolar a timeline visual do turno.

### Papel
- tocar a animação do turno com base no `LeitorLogs`;
- controlar velocidade de reprodução;
- saber quando o turno animado terminou;
- acionar o `FinalizadorBatalha` quando for a hora.

### Métodos principais
- `iniciar()`: começa a animação do turno.
- `atualizar()`: avança timeline visual.
- `finalizar()`: encerra a animação atual.
- `esta_ativo()`: informa se o turno ainda está animando.
- `velocidade_atual()`: devolve velocidade de reprodução.
- `definir_velocidade()`: altera velocidade da animação.

---

## 6.12. `Codigo/ModulosBatalha/IndicadoresAcoes.py`

### Classe: `IndicadoresAcoes`
Arquivo novo do client para centralizar previews e indicadores.

### Papel
- desenhar alcance, área, zona, alvo, laser, impulso, dash e posição fantasma;
- separar a parte visual do preview do `MontadorJogada`;
- manter dois modos por indicador: **preparando** e **preparado**.

### Métodos principais
- `limpar()`: remove todos os indicadores do turno.
- `definir_alvo_preparando()`: prepara o indicador de alvo enquanto o jogador ainda está montando.
- `definir_alvo_preparado()`: mantém o indicador de alvo já confirmado na lista.
- `definir_area_preparando()`: prepara o indicador de área durante a montagem.
- `definir_area_preparada()`: mantém a área já preparada.
- `definir_zona_preparando()`: prepara o indicador de zona durante a montagem.
- `definir_zona_preparada()`: mantém a zona já preparada.
- `definir_laser_preparando()`: prepara o corredor de laser durante a montagem.
- `definir_laser_preparado()`: mantém o laser já preparado.
- `definir_movimento_preparando()`: prepara arrasto e fantasma de movimento.
- `definir_movimento_preparado()`: mantém o movimento já preparado.
- `definir_dash_preparando()`: prepara o dash durante a montagem.
- `definir_dash_preparado()`: mantém o dash já preparado.
- `definir_impulso_preparando()`: mostra seta e intensidade durante a montagem.
- `definir_impulso_preparado()`: mantém a seta/intensidade já preparadas.
- `atualizar()`: atualiza animações leves dos indicadores.
- `renderizar()`: desenha indicadores na arena.

---

## 6.13. `Codigo/ModulosBatalha/IA/BotBatalha.py`

### Classe: `BotBatalha`
Camada principal da IA local.

### Métodos principais
- `pensar_turno()`: decide o conjunto de jogadas do turno.
- `definir_dificuldade()`: aplica perfil de dificuldade.
- `limpar_estado()`: limpa memória entre turnos, se necessário.

---

## 6.14. `Codigo/ModulosBatalha/IA/AvaliadorAcoesIA.py`

### Classe: `AvaliadorAcoesIA`
Avalia o valor relativo de cada ação possível.

### Métodos principais
- `avaliar_acao()`: pontua uma ação específica.
- `avaliar_alvo()`: pontua melhor alvo de uma ação.
- `avaliar_posicionamento()`: pontua movimento e posicionamento.
- `avaliar_risco()`: calcula risco da ação.

---

## 6.15. `Codigo/ModulosBatalha/IA/GeradorJogadasIA.py`

### Classe: `GeradorJogadasIA`
Transforma as escolhas da IA em ações no mesmo formato do jogador humano.

### Métodos principais
- `gerar()`: cria a lista final de jogadas.
- `listar_acoes_validas()`: coleta ações possíveis.
- `montar_jogada_movimento()`: gera ação de movimento.
- `montar_jogada_ataque()`: gera ação de ataque.
- `montar_jogada_troca()`: gera ação de troca.

---

## 6.16. `Codigo/Paineis/FichaPokemonBatalha.py`

### Classe: `FichaPokemonBatalha`
Ficha detalhada do pokémon em batalha.

### Papel
- mostrar atributos, ataques, itens, energia e tipos;
- permitir seleção de ataque;
- mostrar previsão de custo/efeito quando necessário.

### Métodos principais
- `render()`: desenha a ficha.
- `selecionar_ataque()`: seleciona ataque por objeto.
- `selecionar_ataque_indice()`: seleciona por índice.
- `ataque_selecionado()`: devolve ataque atual.
- `limpar_ataque_selecionado()`: limpa seleção.
- `atualizar_previsao()`: aplica dados de previsão visual.
- `definir_controle_inimigo()`: muda modo de render para inimigo.
- `contem_ponto()`: informa se clique atingiu a ficha.

---

## 6.17. `Codigo/Paineis/PainelAcoes.py`

### Classe: `PainelAcoes`
Painel lateral das ações preparadas.

### Observação
O legado atual usa `PainelJogada.py`; no alvo novo ele pode ser renomeado ou adaptado para `PainelAcoes.py`.

### Papel
- listar ações em ordem;
- permitir seleção e remoção;
- exibir nome, custo e resumo da ação.

### Métodos principais
- `sincronizar()`: recebe lista nova de ações.
- `atualizar()`: atualiza hover e estado interno.
- `processar_eventos()`: processa clique, hover e remoção.
- `coletar_comandos()`: devolve comandos disparados pelo painel.
- `recalcular_layout()`: organiza posições internas.
- `retangulos_interativos()`: expõe áreas clicáveis.
- `jogada_hover()`: devolve item sob o mouse.
- `desenhar()`: renderiza o painel.

---

# 7. SERVIDOR

## 7.1. `SimuladorServerJogo/Batalha/EstadosPartida.py`

### Classe/Enum: `EstadosPartida`
Arquivo extra recomendado.

### Papel
Centralizar os estados macro da partida.

### Estados mínimos
- `MONTANDO_JOGADAS`
- `AGUARDANDO_ENVIO`
- `RODANDO_TURNO`
- `ANIMANDO_TURNO`
- `ENCERRADA`

### Uso
Este estado deve ser lido pela `Partida`, pelo `GerenciadorPartidas` e pelo client.

### Observação
`ENCERRADA` representa a fase final de conferência entre resultado/log e o estado real da partida antes do fechamento definitivo.

---

## 7.2. `SimuladorServerJogo/Batalha/GerenciadorPartidas.py`

### Classe: `GerenciadorPartidas`
Camada externa de ciclo de vida das partidas.

### Papel
- criar;
- registrar;
- buscar;
- encerrar;
- limpar;
- receber jogadas e disparar turno quando pronto.

### Métodos principais
- `iniciar_partida()`: cria e registra uma nova partida.
- `obter_partida()`: devolve partida por id.
- `obter_partida_ativa()`: devolve partida ativa de um contexto/jogador.
- `snapshot_batalha_ativa()`: devolve snapshot público atual.
- `receber_jogadas()`: entrega jogadas à partida correta.
- `encerrar_partida()`: fecha a partida por motivo definido.
- `limpar_encerradas()`: remove partidas já concluídas da memória, se necessário.

---

## 7.3. `SimuladorServerJogo/Batalha/Partida.py`

### Classe: `Partida`
Coração do servidor de batalha.

### Papel
- ser dona do estado vivo da batalha;
- guardar a arena como grid de tiles dentro da própria `Partida`, normalmente `40 x 20`;
- guardar o clima como atributo próprio da `Partida`, iniciando em `None` quando não houver clima ativo;
- guardar turno, `TickGlobal`, ativos, reservas, objetos e log geral;
- receber jogadas;
- finalizar turno;
- verificar encerramento.

### Métodos principais
- `receber_jogadas()`: registra ações enviadas por um lado.
- `normalizar_payload_jogada()`: garante leitura única do payload por estilo/ação.
- `coletar_jogadas_pendentes_turno()`: devolve jogadas do turno atual.
- `listar_ativos()`: devolve ativos de um lado.
- `listar_todos_lado()`: devolve todos os pokémons de um lado.
- `obter_pokemon()`: encontra pokémon por id.
- `listar_objetos()`: devolve objetos atuais da batalha.
- `adicionar_objeto()`: registra novo projétil/construto/parede.
- `remover_objeto()`: remove objeto quando finalizado.
- `substituir_ativo_por_reserva()`: resolve troca concluída.
- `lado_tem_pokemon_vivo()`: verifica se lado ainda vive.
- `Verificar()`: chama as verificações da própria partida, incluindo estado dos lados, arena e encerramento.
- `detectar_encerramento()`: verifica vitória, derrota ou empate.
- `finalizar_turno()`: fecha turno, resolve rotinas de fim de turno como chance de saída do clima e recuperação de energia, atualiza `TickGlobal`, consolida diff e prepara o próximo ciclo.
- `finalizar_batalha()`: fecha estado final da partida.
- `snapshot()`: devolve snapshot público autoritativo.
- `gerar_id_global()`: gera id único de entidade ou evento respeitando o primeiro dígito de classe (`1` projétil, `2` construto, `3` parede, `4` ação, `5` evento, `6` turno, `7` ataque).

### Observação de ids
Os Pokémon usam esquema fixo de 3 dígitos no formato `0LS`, onde `L` representa o lado e `S` o slot normal daquele lado.

---

## 7.4. `SimuladorServerJogo/Batalha/InicializadorPartida.py`

### Classe: `InicializadorPartida`
Cria a `Partida` inicial já com tudo preparado.

### Papel
- carregar ataques, efeitos e dados necessários;
- copiar pokémons para o estado de batalha;
- posicionar ativos iniciais;
- montar arena e clima inicial.

### Métodos principais
- `criar_partida()`: cria a partida completa.
- `_carregar_ataques()`: carrega ataques base do dado técnico.
- `_carregar_efeitos()`: carrega a base de efeitos a partir do CSV já existente do jogo.
- `_copiar_pokemon_dict()`: cria cópia de batalha do pokémon.
- `_inicializar_pokemons()`: cria `PokemonBatalha` autoritativos.
- `_registrar_aliases_pokemon()`: registra ids/aliases úteis.
- `_pontos_lado_arena()`: calcula posições iniciais por lado.
- `_centro_arena_local()`: calcula centro útil da arena.

---

## 7.5. `SimuladorServerJogo/Batalha/ObjetoBatalha.py`

### Classe: `ObjetoBatalha`
Classe base de tudo que existe na batalha e participa do ciclo do turno.

### Papel
- fornecer contrato mínimo comum para pokémons, projéteis, paredes e construtos.

### Campos conceituais mínimos
- id;
- tipo do objeto;
- posição;
- área de colisão;
- ativo/inativo;
- velocidade atual, quando aplicável;
- massa, quando aplicável.

### Métodos principais
- `avancar_tick()`: comportamento básico por tick.
- `serializar()`: devolve estado público do objeto.
- `esta_ativo()`: informa se o objeto ainda existe na batalha.

---

## 7.6. `SimuladorServerJogo/Batalha/PokemonBatalha.py`

### Classe: `PokemonBatalha`
Objeto autoritativo do pokémon dentro da partida.

### Papel
- guardar atributos, estados, efeitos, posição, ações e passivas;
- ser a interface oficial de alteração do estado;
- executar `Verifica()` no fim do tick.

### Métodos principais
- `obter_atributo()`: devolve atributo atual do pokémon.
- `serializar()`: devolve estado público ou completo.
- `Verifica()`: rotina principal de verificação do tick.
- `ModificarStatus()`: altera atributo ou estado estruturado.
- `ReceberBarreira()`: adiciona barreira ao pokémon.
- `Curar()`: cura o próprio pokémon.
- `ReceberCura()`: recebe cura de outra origem.
- `GanharEnergia()`: recupera energia.
- `gastar_energia()`: consome energia.
- `AplicarEfeito()`: aplica efeito por iniciativa própria.
- `ReceberEfeito()`: recebe efeito de outra origem.
- `TomarDano()`: recebe dano seguindo a ordem oficial do sistema.
- `AplicarDano()`: causa dano estruturado a um alvo.
- `Mover()`: atualiza posição autoritativa.
- `AlterarClima()`: altera clima da partida quando permitido.
- `ModificarArena()`: cria/remove/edita efeito de tile ou arena.
- `passar_ticks()`: consome ticks internos quando necessário.
- `passivas_habilidade_ativas()`: lista passivas de habilidade válidas.
- `passivas_equipaveis_ativas()`: lista passivas de item válidas.
- `_registrar_passivas()`: registra disparos de passiva no histórico.
- `_consumir_efeito()`: consome ou expira efeito quando necessário.
- `finalizar_resultado_batalha()`: ajusta estado final ao encerrar.

### Observação crítica
Este arquivo deve continuar forte, mas as fórmulas internas precisam obedecer totalmente às diretrizes novas.

---

## 7.7. `SimuladorServerJogo/Batalha/ProjetilBatalha.py`

### Classe: `ProjetilBatalha`
Objeto de batalha com vida própria após criação.

### Papel
- guardar posição, velocidade, raio, alcance restante, massa opcional e execute embutido;
- andar por tick;
- colidir com pokémons, projéteis, objetos e paredes.

### Métodos principais
- `avancar_tick()`: move o projétil no tick.
- `resolver_colisao()`: resolve colisão conforme o alvo e propriedades.
- `executar_estado()`: resolve execute de estado quando a colisão ou outro ponto técnico pedir.
- `aplicar_ricochete()`: altera direção e velocidade após ricochete.
- `aplicar_atravessar()`: resolve continuação do projétil quando a colisão permitir atravessar.
- `reduzir_alcance()`: desconta alcance restante.
- `finalizar()`: encerra o projétil.
- `serializar()`: devolve estado público útil para histórico e replay.

---

## 7.8. `SimuladorServerJogo/Batalha/ParedeBatalha.py`

### Classe: `ParedeBatalha`
Objeto fixo da arena.

### Papel
- representar colisão retangular fixa;
- barrar movimentação, dash, impulso, laser e projéteis conforme regra.

### Métodos principais
- `serializar()`: devolve estado público da parede.
- `colide()`: verifica colisão com objeto móvel.
- `resolver_impacto()`: devolve resultado físico da batida.

---

## 7.9. `SimuladorServerJogo/Batalha/ConstrutoBatalha.py`

### Classe: `ConstrutoBatalha`
Objeto de batalha irregular criado por ataques, passivas ou regras da arena.

### Papel
- existir em campo;
- agir por tick quando necessário;
- ter vida, massa, colisão e efeito próprios dependendo da configuração.

### Métodos principais
- `avancar_tick()`: executa rotina de tick.
- `Verifica()`: rotina de verificação no fim do tick.
- `TomarDano()`: recebe dano, se aplicável.
- `AplicarEfeitoPassivo()`: aplica efeito próprio do construto.
- `serializar()`: devolve estado do construto.

---

## 7.10. `SimuladorServerJogo/Batalha/FraquezasResistencias.py`

### Papel
Utilitário de multiplicador de tipo.

### Observação
Este arquivo pode continuar **sem classe**, pois é naturalmente utilitário.

### Funções principais
- `carregar_tabela_fr()`: carrega tabela de tipos.
- `normalizar_tipo()`: normaliza texto do tipo.
- `modificador_tipo()`: devolve multiplicador final do ataque contra os tipos do alvo.

---

## 7.11. `SimuladorServerJogo/Batalha/FisicaBatalha.py`

### Classe: `FisicaBatalha`
Arquivo extra recomendado, derivado da necessidade hoje atendida parcialmente por `SimuladorFisica.py`.

### Papel
- centralizar matemática e física reais da batalha;
- calcular velocidade efetiva, atrito, potência, colisão, reflexão, dominância e deslocamento por tick.

### Métodos principais
- `velocidade_movimento()`: calcula `max(0, Vel + 50)` ou variações de dash/impulso.
- `tiles_por_tick()`: converte velocidade para deslocamento espacial.
- `custo_movimento_por_tile()`: devolve custo por tile do movimento.
- `massa_efetiva()`: calcula `max(1, Peso / 10)`.
- `potencia_fisica()`: calcula potência com base em peso e velocidade real.
- `desaceleracao_atrito()`: devolve desaceleração conforme atrito e peso.
- `fator_tangencial()`: devolve `f_t` conforme o contexto do tile.
- `componentes_colisao()`: projeta velocidade em normal e tangente.
- `resolver_colisao_objetos()`: aplica a fórmula vetorial da colisão entre dois objetos móveis.
- `resolver_colisao_fixo()`: aplica reflexão contra parede ou outro objeto fixo.
- `dominancia_colisao()`: calcula o peso do atropelamento quando as potências forem muito diferentes.
- `normalizar_vetor()`: normaliza direção.
- `distancia()`: mede distância útil da simulação.
- `limitar_ao_campo()`: garante permanência na arena quando cabível.
- `mover_um_tick()`: produz nova posição após um tick.
- `resolver_impulso_pos_colisao()`: converte o vetor final em impulso desacelerado pós-colisão.

---

## 7.12. `SimuladorServerJogo/Batalha/MotorAcoes.py`

### Classe: `MotorAcoes`
Executor das ações em andamento.

### Papel
- iniciar ações do tick atual;
- prosseguir ações já iniciadas;
- finalizar ações quando sua condição acabar;
- criar objetos derivados de ações, como projéteis.

### Métodos principais
- `iniciar_acoes_tick()`: começa as ações que entram no tick atual.
- `prosseguir_acoes()`: avança ações em andamento.
- `finalizar_acao()`: fecha ação por conclusão.
- `cancelar_acao()`: fecha ação por cancelamento.
- `criar_objetos_da_acao()`: cria projéteis e construtos nascidos de ações.
- `acoes_em_curso()`: devolve ações ainda vivas.
- `acoes_futuras()`: devolve ações ainda não iniciadas.

---

## 7.13. `SimuladorServerJogo/Batalha/DetectorColisoes.py`

### Classe: `DetectorColisoes`
Responsável por detectar pares que colidem no tick e encaminhar a resolução.

### Papel
- checar colisões entre pokémons, projéteis, construtos e paredes;
- impedir dupla resolução do mesmo par no mesmo tick.

### Métodos principais
- `coletar_colisoes_tick()`: devolve lista de colisões do tick.
- `colisao_pokemon_pokemon()`: detecta colisão entre pokémons.
- `colisao_objeto_parede()`: detecta colisão com parede.
- `colisao_projetil_objeto()`: detecta colisão de projétil.
- `ja_processada()`: verifica se a colisão do par já foi tratada.
- `registrar_processada()`: marca par como já processado no tick.
- `limpar_tick()`: limpa memória local da deduplicação para o próximo tick.

---

## 7.14. `SimuladorServerJogo/Batalha/ExecutorTurnos.py`

### Classe: `ExecutorTurnos`
Rodador oficial do turno.

### Papel
- executar o loop principal por tick;
- chamar `MotorAcoes`, `DetectorColisoes`, `LogBatalha` e verificações finais;
- encerrar o turno só quando não restar ação, objeto pendente nem evento futuro.

### Métodos principais
- `executar_turno()`: rotina principal do turno.
- `_iniciar_tick()`: prepara estruturas do tick.
- `_iniciar_acoes_do_tick()`: chama o motor para começar ações do tick.
- `_prosseguir_acoes_e_objetos()`: avança tudo que está em curso.
- `_resolver_colisoes_tick()`: coleta e resolve colisões.
- `_processar_timers_e_efeitos()`: consome tempo interno e efeitos por tick.
- `_rodar_verificacoes()`: chama `Verifica()` de Pokémon, Construtos e Partida.
- `_encerrar_tick()`: registra encerramento do tick.
- `_condicao_parada()`: diz se ainda existe trabalho pendente.
- `_timeout()`: aplica encerramento seguro por excesso de ticks.

---

## 7.15. `SimuladorServerJogo/Batalha/ColetorJogadas.py`

### Classe: `ColetorJogadas`
Recebe e organiza as jogadas do turno antes da simulação.

### Papel
- validar formato de entrada;
- normalizar ids e ações;
- separar por lado e por executor;
- ordenar ações pela fila simples do turno usando `tick_inicio`, com velocidade como critério de desempate quando necessário.

### Métodos principais
- `receber_jogadas()`: recebe o pacote bruto de jogadas.
- `validar_jogadas()`: valida regras básicas de quantidade e formato.
- `normalizar_jogadas()`: normaliza os dados de entrada.
- `ordenar_jogadas()`: aplica ordenação por inteligência e ordem local.
- `custo_jogada_multiplas_acoes()`: calcula custo com regra da segunda ação.
- `jogadas_prontas()`: devolve jogadas prontas para o executor do turno.

---

## 7.16. `SimuladorServerJogo/Batalha/LogBatalha.py`

### Classe: `LogBatalha`
Responsável pelo histórico técnico, histórico público e diff final.

### Papel
- registrar eventos por tick;
- consolidar histórico do turno;
- gerar diff final;
- manter log geral da partida.

### Métodos principais
- `registrar_evento()`: registra evento técnico bruto.
- `registrar_acao()`: registra início/fim/cancelamento de ação.
- `registrar_movimento()`: registra trajetória e conclusão.
- `registrar_dano()`: registra pacote detalhado de dano.
- `registrar_cura()`: registra cura.
- `registrar_barreira()`: registra alteração de barreira.
- `registrar_efeito()`: registra aplicação/remoção/expiração de efeito.
- `registrar_objeto()`: registra criação/finalização de projétil ou construto.
- `registrar_colisao()`: registra colisões e resultados físicos.
- `registrar_clima()`: registra alteração de clima.
- `registrar_tile()`: registra interação relevante com tile.
- `registrar_timeout()`: registra timeout do turno.
- `construir_historico_publico()`: gera histórico consumível pelo client.
- `construir_diff_final()`: gera diff final do turno apenas com os campos que realmente mudaram.
- `fechar_turno()`: consolida histórico do turno.
- `fechar_partida()`: fecha log geral da partida.

---

# 8. `SimuladorServerJogo/Batalha/ConstrutorAcao.py`

## 8.1. Papel
Arquivo que concentra a hierarquia principal das ações do turno.

### Classes principais
- `AcaoBase`: contrato comum de qualquer ação do turno.
- `AcaoAtaque`: filha de `AcaoBase`, base de ataques que não são movimento puro.
- `AcaoTroca`: filha de `AcaoBase`, responsável pela troca entre ativo e reserva.
- `AcaoMover`: filha de `AcaoBase`, base de deslocamentos.

### Métodos principais de `AcaoBase`
- `iniciar()`: marca começo oficial da ação.
- `prosseguir()`: executa um tick da ação.
- `finalizar()`: conclui ação por término natural.
- `cancelar()`: encerra ação por impedimento.
- `esta_ativa()`: informa se a ação ainda vive.
- `serializar()`: devolve resumo útil para histórico e debug.

### Métodos principais de `AcaoAtaque`
- `ativar()`: dispara a ativação real após intervalo.
- `executar_principal()`: chama o execute principal.
- `executar_estado()`: chama o execute de estado quando a regra técnica exigir.
- `definir_imunes_ao_ataque()`: registra ids imunes à ação/ataque derivado quando necessário.
- `concluir()`: finaliza a ação conforme o estilo.

### Métodos principais de `AcaoTroca`
- `iniciar()`: registra início da troca.
- `prosseguir()`: acompanha a janela da troca.
- `concluir_troca()`: substitui o ativo pelo reserva.
- `cancelar_por_morte()`: cancela troca caso o executor morra antes da conclusão.

### Métodos principais de `AcaoMover`
- `definir_destino()`: registra destino desejado.
- `cobrar_passo()`: cobra energia antes do passo.
- `avancar_passo()`: move o executor no tick.
- `converter_para_impulso()`: converte deslocamento em impulso após colisão.
- `chegou_destino()`: informa se terminou.

---

# 9. `SimuladorServerJogo/Batalha/ConstrutorAtaque.py`

## 9.1. Papel
Arquivo que recebe `PropriedadesAtaque` e os dados enviados pelo jogador para construir a ação concreta do estilo correto.

### Leitura arquitetural
`PropriedadesAtaque` + envio do jogador (direção, alvo quando couber, intensidade quando couber) entram no construtor.  
O construtor escolhe a classe correta do estilo, acopla automaticamente execute principal, execute de estado e executes periféricos quando necessário, e devolve a ação pronta para a fila do turno.  
Todas as classes de estilo herdam de `AcaoAtaque`, **exceto dash e impulso**, que herdam de `AcaoMover`.

### Classes principais
- `AtaqueBase`: base comum carregada pelo construtor.
- `AtaqueAlvo`: filha de `AcaoAtaque`.
- `AtaqueStatus`: filha de `AcaoAtaque`.
- `AtaqueProjetil`: filha de `AcaoAtaque`.
- `AtaqueArea`: filha de `AcaoAtaque`.
- `AtaqueZona`: filha de `AcaoAtaque`.
- `AtaqueLaser`: filha de `AcaoAtaque`.
- `AtaqueDash`: filha de `AcaoMover` com execute ofensivo acoplado na colisão.
- `AtaqueImpulso`: filha de `AcaoMover` com desaceleração e execute ofensivo acoplado na colisão.

### Métodos principais do construtor
- `construir()`: decide o estilo e devolve a ação correta.
- `carregar_propriedades()`: lê e normaliza `PropriedadesAtaque`.
- `acoplar_executes()`: liga automaticamente execute principal, execute de estado e executes periféricos à ação quando necessário.
- `calcular_tick_inicio()`: calcula o tick de início da ação somando tick de ativação/construção e intervalo.

### Métodos principais das classes de estilo
- `resolver_alvo()`: decide alvo real da ativação quando o estilo exigir.
- `criar_objeto()`: cria projétil ou construto quando o estilo exigir.
- `coletar_alvos_area()`: resolve área/zona quando o estilo exigir.
- `resolver_ticks_laser()`: executa a faixa do laser ao longo dos ticks.
- `resolver_impacto_movimento()`: resolve dash/impulso quando a colisão disparar execute.
- `resolver_comportamento_fim_colisao()`: aplica destruir/ricochetear/atravessar após colisão relevante, especialmente em projéteis.

---

# 10. EXECUTES

## 10.1. `SimuladorServerJogo/Logica/Executes/ExecuteAtaques.py`

### Classe: `ExecuteAtaques`
Dispatcher das execuções dos ataques.

### Papel
- localizar execute técnico do ataque;
- montar contexto do execute;
- chamar métodos de pokémon/objeto corretos;
- separar quando necessário execução principal, execução de estado e execução periférica.

### Métodos principais
- `executar_principal()`: executa o núcleo do ataque.
- `executar_estado()`: executa o fluxo de estado do ataque/objeto quando houver.
- `executar_perifericos()`: prepara ou entrega os executes periféricos para o método chamado.
- `montar_contexto()`: cria contexto padronizado do execute.
- `registrar_resultado()`: devolve resultado estruturado ao log.

### Observação
Passivas de item e habilidade não dependem de JSON nem de um novo dispatcher dedicado neste desenho. Elas permanecem em seus próprios arquivos `.py`, como funções, e são consumidas pelos métodos e flags do sistema quando necessário.

---

# 11. O que acontece com os arquivos legados atuais

## 11.1. Arquivos que sobrevivem quase com o mesmo nome
- `Arena.py`
- `ControladorBatalha.py`
- `ElementosHudBatalha.py`
- `InicializadorBatalha.py`
- `FinalizadorBatalha.py`
- `LeitorLogs.py`
- `MontadorJogada.py`
- `PlayerBatalha.py`
- `PokemonAnimator.py`
- `Codigo/Geradores/PokemonBatalha.py`
- `FichaPokemonBatalha.py`
- `FraquezasResistencias.py`
- `ObjetoBatalha.py`
- `PokemonBatalha.py`

## 11.2. Arquivos legados que devem ser absorvidos ou sumir do núcleo
- `ControladorFluxos.py` deve ser absorvido por `IndicadoresAcoes.py` + `MontadorJogada.py`.
- `LeitorFluxos.py` sai do núcleo da batalha nova.
- `PlayerControleBat.py` pode ser absorvido por `PlayerBatalha.py` ou `ControladorBatalha.py`.
- `Codigo/ModulosBatalha/SistemaBatalha.py` deve ser quebrado entre `ControladorBatalha`, `InicializadorBatalha` e `FinalizadorBatalha`.
- `SimuladorServerJogo/Batalha/SistemaBatalha.py` deve virar `Partida.py` + `InicializadorPartida.py`.
- `SimuladorServerJogo/Batalha/LeitorJogadas.py` deve ser desmontado em `ColetorJogadas.py`, `MotorAcoes.py`, `ExecutorTurnos.py`, `LogBatalha.py`, `ConstrutorAcao.py` e `ConstrutorAtaque.py`.
- `SimuladorServerJogo/Batalha/SimuladorFisica.py` deve virar `FisicaBatalha.py`.


---

# 12. Fechamento

Esta arquitetura tenta equilibrar três coisas ao mesmo tempo:

1. **fidelidade às diretrizes novas**;
2. **aproveitamento real das peças já existentes**;
3. **árvore enxuta o bastante para não virar um inferno de arquivos**.

Ela não depende de um arquivo gigante que faz tudo.  
Também não cai no outro extremo de inventar estrutura demais.

O resultado é um núcleo onde:
- a **Partida** manda no estado;
- o **ExecutorTurnos** manda no tempo;
- o **MotorAcoes** manda nas ações vivas;
- o **DetectorColisoes** manda nos encontros físicos;
- o **LogBatalha** manda no histórico;
- o **ExecuteAtaques** centraliza apenas os três tipos de execute do ataque;
- passivas continuam onde já fazem mais sentido: nos métodos e nos arquivos `.py` próprios de item/habilidade.
