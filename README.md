<div align="center">

# Pokémon Global Server

<img src="Recursos/Visual/Icones/GlobalServer/QuadroLogo.png" alt="Logo do Pokémon Global Server" width="360">

**Jogo 2D em Python com arquitetura client/server, mundo aberto, coleta de Pokémon, inventário, crafting, NPCs, exploração e batalhas estratégicas baseadas em turnos, ticks, física e efeitos.**

</div>

---

## 1. Descrição

**Pokémon Global Server** é um jogo 2D desenvolvido em Python com foco em exploração, progressão e batalhas estratégicas. O projeto combina um cliente visual feito com Pygame, módulos de interface, animação e renderização, além de um simulador de servidor responsável por regras, mundo, entidades, rotas e lógica autoritativa.

O jogo possui uma base grande de dados própria, incluindo Pokémon, ataques, itens, equipamentos, efeitos, NPCs, receitas, diálogos e regras de mundo. A estrutura foi pensada para separar cada parte importante do projeto: o cliente cuida da experiência visual e da interação do jogador, enquanto o servidor/simulador concentra a lógica de mundo, batalha, geração e validação de regras.

A proposta principal é criar um jogo com aparência simples, mas sistemas internos profundos: mundo grande em tiles, NPCs combatentes e vendedores, inventário, crafting, captura, efeitos de status, batalha 6v6, leitura de logs de combate, ações planejadas pelo jogador e uma arquitetura preparada para evoluir para multiplayer real.

---

## 2. Snapshots

> O vídeo de showcase ainda será adicionado. As imagens abaixo são renderizadas diretamente do diretório `Snapshots/` do repositório.

### Showcase em vídeo

[Assistir showcase no YouTube](https://www.youtube.com/watch?v=COLOCAR_ID_DO_VIDEO_AQUI)

### Galeria

| Snapshot | Snapshot |
|---|---|
| <img src="Snapshots/Foto1.png" alt="Snapshot 01" width="420"> | <img src="Snapshots/Foto2.png" alt="Snapshot 02" width="420"> |
| <img src="Snapshots/Foto3.png" alt="Snapshot 03" width="420"> | <img src="Snapshots/Foto4.png" alt="Snapshot 04" width="420"> |
| <img src="Snapshots/Foto5.png" alt="Snapshot 05" width="420"> | <img src="Snapshots/Foto6.png" alt="Snapshot 06" width="420"> |
| <img src="Snapshots/Foto7.png" alt="Snapshot 07" width="420"> | <img src="Snapshots/Foto8.png" alt="Snapshot 08" width="420"> |
| <img src="Snapshots/Foto9.png" alt="Snapshot 09" width="420"> | <img src="Snapshots/Foto10.png" alt="Snapshot 10" width="420"> |

---

## 3. Detalhes estatísticos

Os números abaixo foram levantados a partir dos arquivos atuais enviados do projeto. Alguns valores podem mudar conforme novos dados, assets e relatórios forem adicionados ao repositório.

| Categoria | Quantidade atual |
|---|---:|
| Pokémon cadastrados em `Dados/Pokemon Global Server - Pokemons.csv` | **1.275** |
| Ataques cadastrados em `Dados/Pokemon Global Server - Ataques.csv` | **17** |
| Efeitos cadastrados em `Dados/Pokemon Global Server - Efeitos.csv` | **50** |
| Itens cadastrados em `Dados/Pokemon Global Server - Itens.csv` | **140** |
| Equipáveis cadastrados em `Dados/Pokemon Global Server - Equipaveis.csv` | **63** |
| NPCs cadastrados | **75** |
| Tipos de Pokémon | **20** |
| Biomas | **7** |
| Estruturas naturais | **24** |
| Trilhas sonoras | **35** |
| Receitas | **31** |
| Estádios/categorias de combatentes no CSV atual | **20** |
| Mundo planejado | **10.000 x 10.000 tiles** |

Principais arquivos de dados:

- `Dados/Pokemon Global Server - Pokemons.csv`
- `Dados/Pokemon Global Server - Ataques.csv`
- `Dados/Pokemon Global Server - Efeitos.csv`
- `Dados/Pokemon Global Server - Itens.csv`
- `Dados/Pokemon Global Server - Equipaveis.csv`
- `Dados/Pokemon Global Server - Receitas.json`
- `Dados/Pokemon Global Server - PropriedadesAtaques.json`
- `Dados/Pokemon Global Server - Sistema FR.csv`

---

## 4. Features principais e conceitos

### Mundo e exploração

- Mundo grande baseado em tiles.
- Sistema de leitura e controle de mundo no cliente.
- Módulos dedicados para atores, objetos, player, HUD, minimapa e mapa-múndi.
- Sistema de chunks/pacotes para sincronização e atualização do estado do mundo.
- Geração de mundo com regras próprias de terreno, biomas, localidades, rotas e estruturas naturais.
- Estrutura de geração em Java para etapas pesadas de criação do mundo.

### Pokémon e progressão

- Base extensa com mais de mil Pokémon cadastrados.
- Atributos próprios como vida, ataque, defesa, ataque especial, defesa especial, velocidade, magia, perfuração, energia, inteligência, crítico, raridade, estágio, peso, tamanho e linhagem.
- Sistema de inventário de Pokémon.
- Painéis de visualização como Pokédex, ficha de Pokémon, ficha de batalha e times.
- Estrutura para captura, materialização e controle de Pokémon no mundo.

### Batalha

- Sistema de batalha separado dos módulos gerais do mundo.
- Batalha com times, jogadores, arena, HUD, controlador de ações, leitor de logs e finalização.
- Arquitetura de batalha preparada para turnos, ações planejadas e reprodução visual por logs.
- Sistema de ataques com propriedades carregadas de dados.
- Efeitos de status e regras próprias para cálculo e aplicação de consequências.
- IA separada em módulo próprio dentro de `Codigo/ModulosBatalha/IA`.

### Ações, ataques e efeitos

- Ataques definidos em CSV e propriedades adicionais em JSON.
- Execução de ataques separada em módulos de lógica do servidor.
- Suporte a passivas de ataques, itens, equipamentos e habilidades.
- Efeitos negativos e positivos controlados por dados e regras.
- Sistema de fraquezas e resistências baseado em matriz própria.

### Inventário, itens e crafting

- Sistema de itens com raridade, valor, stack, baú e estilo.
- Equipáveis com múltiplos bônus de status.
- Receitas definidas em JSON.
- Serviço de crafting no módulo de mundo.
- Painéis próprios para inventário, itens, receitas e craft.

### NPCs e interações

- NPCs combatentes e vendedores cadastrados em CSV.
- Diálogos e interações em JSON.
- Cérebro de NPCs no servidor.
- Estrutura para vendedores, combatentes, capitães, líderes e personagens especiais.

### Interface e experiência visual

- Sistema de cenas: login, menu, carregamento, mundo e combate.
- Subtelas e painéis reutilizáveis.
- Componentes de interface próprios: botões, barras, caixas de texto, tooltips, mensagens, painéis e imagens.
- HUDs separados para mundo e batalha.
- Sistema de animação de Pokémon.
- Pipeline gráfico em evolução, com módulos para composição e suporte a ModernGL/shaders.

### Servidor e simulação

- Simulador de servidor separado do cliente.
- Rotas próprias para entrada, ativação, atualização, terminal, operação e batalha.
- Estado central do servidor.
- Regras centralizadas em TOML.
- Cérebro central de mundo e cérebros especializados para Pokémon, baús, estádios, estruturas, itens, NPCs, projéteis, tempo e XP.

---

## 5. Arquitetura

A arquitetura do projeto está organizada em três blocos principais:

- `Codigo/`: cliente do jogo, interface, cenas, renderização, HUDs, telas e módulos visuais.
- `Dados/`: base de dados do jogo, com CSVs e JSONs de Pokémon, ataques, itens, NPCs, receitas e interações.
- `SimuladorServerJogo/`: servidor/simulador, regras, rotas, lógica autoritativa, mundo, batalha, geração e banco de dados.

### Visão geral

```text
.
├── Codigo/
│   ├── Cenas/
│   ├── Geradores/
│   ├── ModulosBatalha/
│   ├── ModulosGerais/
│   ├── ModulosMundo/
│   ├── Outros/
│   ├── Paineis/
│   ├── Prefabs/
│   ├── Server/
│   └── Telas/
│
├── Dados/
│   ├── InteracoesNPC/
│   ├── Pokemon Global Server - Ataques.csv
│   │   ├── Pokemon Global Server - Efeitos.csv
│   ├── Pokemon Global Server - Equipaveis.csv
│   ├── Pokemon Global Server - Itens.csv
│   ├── Pokemon Global Server - NPC Combatente.csv
│   ├── Pokemon Global Server - NPC Vendedor.csv
│   ├── Pokemon Global Server - Pokemons.csv
│   ├── Pokemon Global Server - PropriedadesAtaques.json
│   ├── Pokemon Global Server - Receitas.json
│   └── Pokemon Global Server - Sistema FR.csv
│
└── SimuladorServerJogo/
    ├── Batalha/
    ├── Gerais/
    ├── Logica/
    └── Mundo/
```

### `Codigo/` — cliente do jogo

O diretório `Codigo/` concentra a parte visual e interativa do jogo. Ele controla cenas, telas, HUDs, animações, entrada do jogador, renderização, módulos do mundo, módulos de batalha e comunicação com rotas do servidor.

```text
Codigo/
├── Cenas/
│   ├── CenaCarregamento.py
│   ├── CenaCombate.py
│   ├── CenaLogin.py
│   ├── CenaMenu.py
│   ├── CenaMundo.py
│   └── ControladorCenas.py
│
├── Geradores/
│   ├── Ator.py
│   ├── Baus.py
│   ├── Dungeon.py
│   ├── Estadio.py
│   ├── EstruturaNaturais.py
│   ├── ItemInventario.py
│   ├── ItemMundo.py
│   ├── PokemonInventario.py
│   ├── PokemonMundo.py
│   ├── Projetil.py
│   ├── XpMundo.py
│   └── Player/
│       ├── Controle.py
│       ├── Inventario.py
│       ├── Perfil.py
│       └── Player.py
│
├── ModulosBatalha/
│   ├── Arena.py
│   ├── ControladorAnimacoes.py
│   ├── ControladorBatalha.py
│   ├── ElementosHudBatalha.py
│   ├── FinalizadorBatalha.py
│   ├── IndicadorAtaque.py
│   ├── InicializadorBatalha.py
│   ├── LeitorLogs.py
│   ├── MontadorJogadas.py
│   ├── PlayerBatalha.py
│   ├── PokemonBatalha.py
│   └── IA/
│       └── ControladorIA.py
│
├── ModulosGerais/
│   ├── Auxiliares.py
│   ├── Camera.py
│   ├── Colisor.py
│   ├── CompositorModernGL.py
│   ├── DesenhaAtor.py
│   ├── DesenhoMapa.py
│   ├── Discord.py
│   ├── EfeitosTela.py
│   ├── FiltroCamera.py
│   ├── GerenciadorTiles.py
│   ├── ImagensMapa.py
│   ├── ModuladorRegras.py
│   ├── PipelineGrafica.py
│   ├── PokemonAnimator.py
│   └── Sonoridades.py
│
├── ModulosMundo/
│   ├── ControladorAtores.py
│   ├── ControladorCriaveis.py
│   ├── ControladorMundo.py
│   ├── ControladorObjetos.py
│   ├── ControladorPlayer.py
│   ├── ElementosHudMundo.py
│   ├── LeitorDialogo.py
│   ├── LeitorMundo.py
│   ├── Loja.py
│   ├── Minimapa.py
│   ├── ServicoCraft.py
│   ├── ServicoMapaMundo.py
│   └── SistemaPacotes.py
│
├── Outros/
│   ├── Shaders/
│   │   ├── mundo.frag
│   │   └── mundo.vert
│   └── TestesBatalha/
│
├── Paineis/
│   ├── Container.py
│   ├── FichaAtaque.py
│   ├── FichaItem.py
│   ├── FichaPokemon.py
│   ├── FichaPokemonBatalha.py
│   ├── FichaPokemonCombate.py
│   ├── Musicdex.py
│   ├── PainelAcoes.py
│   ├── PainelArvoreHabilidades.py
│   ├── PainelAuxiliarPoke.py
│   ├── PainelCraft.py
│   ├── PainelReceitas.py
│   ├── PainelTimes.py
│   ├── Pokedex.py
│   ├── Skindex.py
│   └── VisualizadorLog.py
│
├── Prefabs/
│   ├── Arrastavel.py
│   ├── Barra.py
│   ├── BarraPesquisa.py
│   ├── Botao.py
│   ├── CaixaTexto.py
│   ├── EfeitosVisuais.py
│   ├── Fluxos.py
│   ├── Imagem.py
│   ├── Mensagem.py
│   ├── Opcoes.py
│   ├── Painel.py
│   ├── Terminal.py
│   ├── Texto.py
│   └── Tooltip.py
│
├── Server/
│   ├── Login.py
│   ├── ServerBatalha.py
│   ├── ServerMenu.py
│   ├── ServerMundo.py
│   └── ServerTerminal.py
│
└── Telas/
    ├── Creditos.py
    ├── Subtela.py
    ├── SubtelaCriarPersonagem.py
    └── Inventario/
        ├── Estatisticas.py
        ├── InventarioItens.py
        ├── InventarioPokemons.py
        └── SubtelaInventario.py
```

### `Dados/` — base de dados do jogo

O diretório `Dados/` funciona como uma base semiestruturada do projeto. Ele concentra informações editáveis sobre entidades, ataques, efeitos, itens, NPCs, receitas e diálogos.

```text
Dados/
├── InteracoesNPC/
│   ├── Combatentes/
│   │   ├── Alleka.json
│   │   ├── Amable.json
│   │   ├── Caio.json
│   │   ├── Felipox.json
│   │   ├── Felps.json
│   │   ├── Ferraz.json
│   │   ├── Garcia.json
│   │   ├── Guedes.json
│   │   ├── Henrique.json
│   │   ├── João.json
│   │   ├── Lisciele.json
│   │   ├── Murilo.json
│   │   ├── Nathzinha.json
│   │   ├── Paulo.json
│   │   ├── Ph.json
│   │   ├── Ramos.json
│   │   ├── Sidney.json
│   │   ├── Suneiva.json
│   │   ├── Suriane.json
│   │   └── Vasques.json
│   │
│   ├── Vendedores/
│   │   └── Josefa.json
│   │
│   ├── ExemploCapitao_Laura.json
│   ├── ExemploDesafiante_Ravi.json
│   ├── ExemploDissociado_Nico.json
│   ├── ExemploLider_Alleka.json
│   └── ManualDialogos.json
│
├── Pokemon Global Server - Ataques.csv
├── Pokemon Global Server - Efeitos.csv
├── Pokemon Global Server - Equipaveis.csv
├── Pokemon Global Server - Itens.csv
├── Pokemon Global Server - NPC Combatente.csv
├── Pokemon Global Server - NPC Vendedor.csv
├── Pokemon Global Server - Pokemons.csv
├── Pokemon Global Server - PropriedadesAtaques.json
├── Pokemon Global Server - Receitas.json
└── Pokemon Global Server - Sistema FR.csv
```

### `SimuladorServerJogo/` — servidor, regras e simulação

O diretório `SimuladorServerJogo/` concentra a lógica mais autoritativa do jogo. Ele organiza batalha, mundo, rotas, comandos, regras, geração, banco de dados e execuções de efeitos.

```text
SimuladorServerJogo/
├── Batalha/
│   ├── ColetorAcoes.py
│   ├── Construto.py
│   ├── ConstrutorLog.py
│   ├── FraquezasResistencia.py
│   ├── GerenciadorPartidas.py
│   ├── Partida.py
│   ├── PokemonBatalha.py
│   └── RodadorTurno.py
│
├── Gerais/
│   ├── EstadoServidor.py
│   ├── LoaderRegras.py
│   ├── Geradores/
│   │   ├── GeradorMundo.py
│   │   ├── GeradorPokemon.py
│   │   └── Java/
│   │       ├── GeradorBiomas.java
│   │       ├── GeradorImagens.java
│   │       ├── GeradorLocalidades.java
│   │       ├── GeradorObjetos.java
│   │       ├── GeradorRotas.java
│   │       ├── GeradorTerreno.java
│   │       └── WorldGenerator.java
│   │
│   └── Rotas/
│       ├── Ativador.py
│       ├── Atualizador.py
│       ├── Entrada.py
│       ├── RotasBatalha.py
│       ├── ServerOperar.py
│       └── Terminal.py
│
├── Logica/
│   ├── Comandos/
│   │   └── Comandos.py
│   │
│   ├── Executes/
│   │   ├── ExecuteAtaques.py
│   │   ├── ExecutesFrutas.py
│   │   ├── ExecutesPokebolas.py
│   │   ├── PassivaAtaques.py
│   │   ├── PassivaItens.py
│   │   ├── PassivasEquipaveis.py
│   │   └── PassivasHabilidades.py
│   │
│   └── Regras/
│       ├── Batalha.toml
│       ├── Biomas.toml
│       ├── Ciclo.toml
│       ├── EstruturasNaturais.toml
│       ├── Geracao.json
│       ├── Gerais.toml
│       ├── Localidades.toml
│       ├── Mundo.toml
│       ├── NPCs.toml
│       ├── Player.toml
│       ├── Pokemons.toml
│       ├── Projeteis.toml
│       ├── Server.toml
│       ├── Spawn.toml
│       └── Terreno.toml
│
└── Mundo/
    ├── AutoridadeCaptura.py
    ├── BancoDados.py
    ├── ObjetosMundoServer.py
    ├── PacotesTick.py
    ├── ServicoInventario.py
    ├── TiqueServidor.py
    └── Cerebros/
        ├── CerebroCentral.py
        ├── CerebroEstadios.py
        ├── CerebroEstruturasNaturais.py
        ├── CerebroItensMundo.py
        ├── CerebroNPCs.py
        ├── CerebroPokemons.py
        ├── CerebroProjeteis.py
        ├── CerebroTempo.py
        └── CerebroXpMundo.py
```

---

## 6. Fluxo

### Fluxo geral do jogo

```text
Jogador
  ↓
Cliente Python/Pygame
  ↓
Controlador de Cenas
  ↓
Cena atual
  ├── Login
  ├── Menu
  ├── Mundo
  └── Combate
  ↓
Módulos específicos
  ├── Mundo: player, atores, objetos, HUD, minimapa, diálogo, loja e pacotes
  └── Batalha: arena, HUD, ações, animações, logs e finalização
  ↓
Comunicação com camada Server do cliente
  ↓
Rotas do SimuladorServerJogo
  ↓
Lógica autoritativa do servidor
  ↓
Resposta para o cliente
  ↓
Atualização visual, HUD, animações e estado local
```

### Fluxo de mundo

```text
CenaMundo
  ↓
ControladorMundo
  ├── ControladorPlayer
  ├── ControladorAtores
  ├── ControladorObjetos
  ├── ControladorCriaveis
  ├── SistemaPacotes
  ├── ElementosHudMundo
  ├── Minimapa
  └── ServicoMapaMundo
  ↓
ServerMundo / Rotas do servidor
  ↓
CerebroCentral
  ├── CerebroPokemons
  ├── CerebroNPCs
  ├── CerebroItensMundo
  ├── CerebroEstadios
  ├── CerebroEstruturasNaturais
  ├── CerebroProjeteis
  ├── CerebroTempo
  └── CerebroXpMundo
  ↓
PacotesTick / EstadoServidor
  ↓
Cliente atualiza entidades, HUD e visualização
```

### Fluxo de batalha

```text
CenaCombate
  ↓
InicializadorBatalha
  ↓
ControladorBatalha
  ├── Arena
  ├── PlayerBatalha
  ├── PokemonBatalha
  ├── MontadorJogadas
  ├── IndicadorAtaque
  ├── ElementosHudBatalha
  ├── ControladorAnimacoes
  ├── LeitorLogs
  └── FinalizadorBatalha
  ↓
ServerBatalha / RotasBatalha
  ↓
GerenciadorPartidas
  ↓
Partida
  ↓
ColetorAcoes
  ↓
RodadorTurno
  ↓
Executes e passivas
  ├── ExecuteAtaques
  ├── PassivaAtaques
  ├── PassivaItens
  ├── PassivasEquipaveis
  └── PassivasHabilidades
  ↓
ConstrutorLog
  ↓
Cliente lê logs e reproduz visualmente os acontecimentos
```

### Fluxo de dados e regras

```text
Dados/*.csv e Dados/*.json
  ↓
LoaderRegras / ModuladorRegras
  ↓
Regras TOML e JSON do servidor
  ↓
Geradores e serviços
  ↓
Entidades de mundo, batalha, itens, NPCs e Pokémon
  ↓
Cliente e servidor usam a mesma base conceitual de dados
```

### Fluxo de renderização e interface

```text
ControladorCenas
  ↓
Cena atual renderiza mundo/base
  ↓
PipelineGrafica
  ├── composição de cena
  ├── composição de HUD
  ├── filtros de câmera
  ├── efeitos de tela
  └── possível composição ModernGL/shader
  ↓
Paineis e Prefabs
  ↓
Tela final do jogo
```

---

## 7. Como rodar

> Esta seção ainda está como placeholder, porque o site oficial, instalador e pacote final de distribuição ainda não existem.

### Instalação pelo site

1. Acesse o site oficial:

```text
https://COLOCAR_SITE_DO_JOGO_AQUI.com
```

2. Baixe o instalador mais recente.

3. Execute o instalador.

4. Abra o jogo pelo atalho criado na área de trabalho ou no menu iniciar.

### Execução para desenvolvimento

> Ajuste os comandos abaixo conforme o arquivo principal definitivo do projeto.

```bash
# 1. Clone o repositório
git clone URL_DO_REPOSITORIO_AQUI

# 2. Entre na pasta do projeto
cd NOME_DA_PASTA_DO_PROJETO

# 3. Crie um ambiente virtual
python -m venv .venv

# 4. Ative o ambiente virtual
# Windows:
.venv\Scripts\activate

# Linux/macOS:
source .venv/bin/activate

# 5. Instale as dependências
pip install -r requirements.txt

# 6. Rode o jogo
python main.py
```

### Observações

- O projeto ainda está em desenvolvimento.
- O instalador final ainda será criado.
- O site de download ainda será definido.
- O comando exato de execução deve ser ajustado conforme o arquivo principal usado no repositório final.

---

## 8. Autor

Desenvolvido por **Leon**.

Projeto criado como um jogo autoral em Python, com foco em sistemas complexos de jogo, arquitetura client/server, mundo aberto, batalha estratégica e evolução contínua.

---

## 9. Último relatório

O projeto mantém o relatório mais recente em [`Registro.md`](Registro.md), localizado na raiz do repositório.

> O GitHub não incorpora automaticamente o conteúdo de outro arquivo Markdown dentro do README apenas com sintaxe Markdown. Para manter esta seção sempre atualizada de forma autônoma, o ideal é o atualizador de relatórios copiar o conteúdo de `Registro.md` para dentro do bloco abaixo sempre que o relatório for regenerado.

<!-- INICIO_REGISTRO_MD -->

> Conteúdo de `Registro.md` será inserido aqui automaticamente pelo atualizador de relatórios.

<!-- FIM_REGISTRO_MD -->

---

<div align="center">

**Pokémon Global Server**  
Projeto em desenvolvimento contínuo.

</div>
