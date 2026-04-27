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

## 3. Detalhes estatísticos

Os números abaixo são atualizados automaticamente pelo `Outros/AtualizadorReadMe.py` a partir dos arquivos atuais do projeto.

| Categoria | Quantidade atual |
|---|---:|
| Pokémon cadastrados em `Dados/Pokemon Global Server - Pokemons.csv` | **1.292** |
| Ataques cadastrados em `Dados/Pokemon Global Server - Ataques.csv` | **18** |
| Efeitos cadastrados em `Dados/Pokemon Global Server - Efeitos.csv` | **51** |
| Itens cadastrados em `Dados/Pokemon Global Server - Itens.csv` | **141** |
| Equipáveis cadastrados em `Dados/Pokemon Global Server - Equipaveis.csv` | **64** |
| NPCs cadastrados | **95** |
| Estruturas naturais | **25** |
| Trilhas sonoras | **35** |
| Receitas | **31** |
| Tipos de Pokémon | **20** |
| Biomas | **7** |
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

A arquitetura abaixo é atualizada automaticamente pelo `Outros/AtualizadorReadMe.py`, vasculhando as principais pastas do projeto.

- `Codigo/`: cliente do jogo, interface, cenas, renderização, HUDs, telas e módulos visuais.
- `Dados/`: base de dados do jogo, com CSVs e JSONs de Pokémon, ataques, itens, NPCs, receitas e interações.
- `SimuladorServerJogo/`: servidor/simulador, regras, rotas, lógica autoritativa, mundo, batalha, geração e banco de dados.

### Visão geral atualizada

```text
.
├── Dados/
├── Codigo/
└── SimuladorServerJogo/
```

### `Dados/`

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
│   ├── Vendedores/
│   │   └── Josefa.json
│   ├── ExemploCapitao_Laura.json
│   ├── ExemploDesafiante_Ravi.json
│   ├── ExemploDissociado_Nico.json
│   ├── ExemploLider_Alleka.json
│   └── ManualDialogos.json
├── Pokemon Global Server - Ataques.csv
├── Pokemon Global Server - Baus.csv
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

### `Codigo/`

```text
Codigo/
├── Cenas/
│   ├── CenaCarregamento.py
│   ├── CenaCombate.py
│   ├── CenaLogin.py
│   ├── CenaMenu.py
│   ├── CenaMundo.py
│   └── ControladorCenas.py
├── Geradores/
│   ├── Player/
│   │   ├── Controle.py
│   │   ├── Inventario.py
│   │   ├── Perfil.py
│   │   └── Player.py
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
│   └── XpMundo.py
├── ModulosBatalha/
│   ├── IA/
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
│   └── PokemonBatalha.py
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
├── ModulosMundo/
│   ├── ControladorAtores.py
│   ├── ControladorCriaveis.py
│   ├── ControladorMundo.py
│   ├── ControladorObjetos.py
│   ├── ControladorPlayer.py
│   ├── ElementosHudMundo.py
│   ├── ExecutaveisPoção.py
│   ├── LeitorDialogo.py
│   ├── LeitorMundo.py
│   ├── Loja.py
│   ├── Minimapa.py
│   ├── ServicoCraft.py
│   ├── ServicoMapaMundo.py
│   └── SistemaPacotes.py
├── Outros/
│   ├── Shaders/
│   │   ├── mundo.frag
│   │   └── mundo.vert
│   └── TestesBatalha/
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
├── Server/
│   ├── Login.py
│   ├── ServerBatalha.py
│   ├── ServerMenu.py
│   ├── ServerMundo.py
│   └── ServerTerminal.py
└── Telas/
    ├── Inventario/
    │   ├── Estatisticas.py
    │   ├── InventarioItens.py
    │   ├── InventarioPokemons.py
    │   └── SubtelaInventario.py
    ├── Creditos.py
    ├── Opções.py
    ├── Subtela.py
    ├── SubtelaCriarPersonagem.py
    ├── SubtelaDialogo.py
    ├── SubtelaFinalizacao.py
    ├── SubtelaOpcoes.py
    ├── SubtelaPreBatalha.py
    ├── TelaConfig.py
    ├── TelaLogin.py
    ├── TelaMapa.py
    ├── TelaMenu.py
    ├── TelaOperador.py
    ├── TelaServers.py
    └── TelasGenericas.py
```

### `SimuladorServerJogo/`

```text
SimuladorServerJogo/
├── Batalha/
│   ├── BatalhaIA/
│   │   └── ControladorIA.py
│   ├── ColetorAcoes.py
│   ├── Construto.py
│   ├── ConstrutorLog.py
│   ├── FraquezasResistencia.py
│   ├── GerenciadorPartidas.py
│   ├── Partida.py
│   ├── PokemonBatalha.py
│   └── RodadorTurno.py
├── Gerais/
│   ├── Geradores/
│   │   ├── Java/
│   │   │   ├── classes/
│   │   │   │   ├── Biome.class
│   │   │   │   ├── BiomeDefinition.class
│   │   │   │   ├── BiomeRules.class
│   │   │   │   ├── ClimateSource.class
│   │   │   │   ├── GeneratorContext$1.class
│   │   │   │   ├── GeneratorContext.class
│   │   │   │   ├── GeradorBiomas$1.class
│   │   │   │   ├── GeradorBiomas.class
│   │   │   │   ├── GeradorImagens$1.class
│   │   │   │   ├── GeradorImagens.class
│   │   │   │   ├── GeradorLocalidades.class
│   │   │   │   ├── GeradorObjetos.class
│   │   │   │   ├── GeradorRotas$RouteCandidate.class
│   │   │   │   ├── GeradorRotas$RouteNode.class
│   │   │   │   ├── GeradorRotas.class
│   │   │   │   ├── GeradorTerreno.class
│   │   │   │   ├── LocalityPoiConfig.class
│   │   │   │   ├── LocalityRules.class
│   │   │   │   ├── NaturalStructure.class
│   │   │   │   ├── NoiseLayerConfig.class
│   │   │   │   ├── Poi.class
│   │   │   │   ├── PoiConfig.class
│   │   │   │   ├── PoiType.class
│   │   │   │   ├── RegionData.class
│   │   │   │   ├── RouteData.class
│   │   │   │   ├── RouteRules.class
│   │   │   │   ├── SimpleToml.class
│   │   │   │   ├── TerrainRules.class
│   │   │   │   ├── Tile.class
│   │   │   │   ├── TomlTable.class
│   │   │   │   └── WorldGenerator.class
│   │   │   ├── GeradorBiomas.java
│   │   │   ├── GeradorImagens.java
│   │   │   ├── GeradorLocalidades.java
│   │   │   ├── GeradorObjetos.java
│   │   │   ├── GeradorRotas.java
│   │   │   ├── GeradorTerreno.java
│   │   │   └── WorldGenerator.java
│   │   ├── GeradorBaus.py
│   │   ├── GeradorMundo.py
│   │   └── GeradorPokemon.py
│   ├── Rotas/
│   │   ├── Ativador.py
│   │   ├── Atualizador.py
│   │   ├── Entrada.py
│   │   ├── RotasBatalha.py
│   │   ├── ServerOperar.py
│   │   └── Terminal.py
│   ├── EstadoServidor.py
│   └── LoaderRegras.py
├── Logica/
│   ├── Comandos/
│   │   └── Comandos.py
│   ├── Executes/
│   │   ├── ExecuteAtaques.py
│   │   ├── ExecutesFrutas.py
│   │   ├── ExecutesPokebolas.py
│   │   ├── PassivaAtaques.py
│   │   ├── PassivaItens.py
│   │   ├── PassivasEquipaveis.py
│   │   └── PassivasHabilidades.py
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
└── Mundo/
    ├── Cerebros/
    │   ├── CerebroBaus.py
    │   ├── CerebroCentral.py
    │   ├── CerebroEstadios.py
    │   ├── CerebroEstruturasNaturais.py
    │   ├── CerebroItensMundo.py
    │   ├── CerebroNPCs.py
    │   ├── CerebroPokemons.py
    │   ├── CerebroProjeteis.py
    │   ├── CerebroTempo.py
    │   └── CerebroXpMundo.py
    ├── AutoridadeCaptura.py
    ├── BancoDados.py
    ├── InicializadorNPC.py
    ├── ObjetosMundoServer.py
    ├── PacotesTick.py
    ├── ServicoInventario.py
    └── TiqueServidor.py
```

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

# Registro

**Relatório:** #47  
**Repo:** `Pokemon-Global-Server-Definitivo`  
**Gerado em:** 2026-04-26T21:25:17  
**Modelo de relatório:** 9  
**Autor:** Leon Cunha Alvaro Lopez Soto

## Visão geral

- **Pastas:** 1.258
- **Arquivos:** 72.152
- **Arquivos de texto:** 233
- **Peso dos arquivos de texto:** 2789.54 KB
- **Tamanho total:** 0.584 GB (626.847.447 bytes)
- **Dias desde a criação do repo:** 55
- **Dias desde a criação oficial:** 329
- **Horas estimadas:** 313.00
- **Linhas totais gerais:** 67.259
- **Commits (repo):** 434
- **Adições desde o último relatório:** <span style='color: green'>+6.741</span>
- **Reduções desde o último relatório:** <span style='color: red'>-1.756</span>

## Python

- **Arquivos `.py`:** 170
- **Linhas totais:** 48.844
- **Tamanho total `.py`:** 2103.78 KB
- **Classes encontradas:** 155
- **Funções encontradas:** 627
- **Métodos encontrados:** 2.177
- **Total funções + métodos:** 2.804
- **Bibliotecas diferentes usadas:** 44

## Rank das 15 pastas mais relevantes por linhas

![Gráfico de barras do rank das 15 pastas](Outros/Relatorios/Imagens/2026-04-26_21-25-17/rank_15_pastas_barras.png)

![Gráfico de pizza do rank das 15 pastas](Outros/Relatorios/Imagens/2026-04-26_21-25-17/rank_15_pastas_pizza.png)

| Rank | Pasta | Subpastas | Arquivos | Linhas gerais | Tamanho (KB) |
|---:|---|---:|---:|---:|---:|
| 1 | `ServerGerais` | 4 | 49 | 8.134 | 455.50 |
| 2 | `Paineis` | 0 | 16 | 6.325 | 281.72 |
| 3 | `Telas` | 1 | 19 | 5.761 | 230.19 |
| 4 | `Dados` | 3 | 37 | 5.236 | 272.61 |
| 5 | `ServerMundo` | 1 | 17 | 4.435 | 231.08 |
| 6 | `ModulosMundo` | 0 | 14 | 4.232 | 193.38 |
| 7 | `Outros` | 0 | 7 | 3.890 | 139.85 |
| 8 | `ModulosGerais` | 0 | 15 | 3.781 | 143.88 |
| 9 | `Prefabs` | 0 | 14 | 3.597 | 131.39 |
| 10 | `ModulosBatalha` | 1 | 11 | 3.447 | 161.93 |
| 11 | `Geradores` | 1 | 15 | 3.437 | 151.88 |
| 12 | `ServerLogica` | 3 | 23 | 3.296 | 100.23 |
| 13 | `ServerBatalha` | 1 | 9 | 2.336 | 109.99 |
| 14 | `Cenas` | 0 | 6 | 1.391 | 64.99 |
| 15 | `Server` | 0 | 5 | 406 | 14.96 |

## Top 50 maiores arquivos `.py` por linhas

| Arquivo | Linhas | Tamanho (KB) |
|---|---:|---:|
| `Outros/GeradorRelatorios.py` | 1.629 | 58.23 |
| `Codigo/Paineis/FichaPokemon.py` | 1.277 | 57.22 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | 1.061 | 48.38 |
| `Codigo/ModulosMundo/ControladorObjetos.py` | 1.029 | 50.58 |
| `Codigo/Paineis/VisualizadorLog.py` | 1.011 | 56.61 |
| `SimuladorServerJogo/Gerais/EstadoServidor.py` | 843 | 34.70 |
| `Codigo/Prefabs/Texto.py` | 806 | 30.97 |
| `Codigo/ModulosBatalha/PokemonBatalha.py` | 753 | 36.20 |
| `SimuladorServerJogo/Mundo/Cerebros/CerebroNPCs.py` | 718 | 37.56 |
| `Codigo/ModulosBatalha/MontadorJogadas.py` | 716 | 35.42 |
| `Codigo/ModulosMundo/ControladorPlayer.py` | 712 | 33.99 |
| `Codigo/Geradores/PokemonMundo.py` | 687 | 33.86 |
| `SimuladorServerJogo/Mundo/BancoDados.py` | 686 | 33.68 |
| `SimuladorServerJogo/Logica/Comandos/Comandos.py` | 686 | 28.53 |
| `SimuladorServerJogo/Gerais/Geradores/GeradorMundo.py` | 681 | 27.51 |
| `Codigo/Paineis/FichaPokemonBatalha.py` | 671 | 33.03 |
| `SimuladorServerJogo/Logica/Executes/ExecuteAtaques.py` | 656 | 24.16 |
| `SimuladorServerJogo/Batalha/PokemonBatalha.py` | 651 | 33.74 |
| `Codigo/Paineis/Container.py` | 637 | 23.33 |
| `SimuladorServerJogo/Gerais/Geradores/GeradorPokemon.py` | 622 | 25.53 |
| `Outros/AtualizadorRelatorios.py` | 619 | 22.07 |
| `Codigo/ModulosGerais/PokemonAnimator.py` | 611 | 24.56 |
| `Codigo/Cenas/CenaMundo.py` | 596 | 32.61 |
| `SimuladorServerJogo/Gerais/Rotas/Atualizador.py` | 559 | 27.60 |
| `Codigo/ModulosGerais/Sonoridades.py` | 553 | 14.59 |
| `Codigo/Paineis/PainelArvoreHabilidades.py` | 547 | 26.81 |
| `Outros/EditorSkins.py` | 514 | 19.97 |
| `SimuladorServerJogo/Batalha/Partida.py` | 514 | 24.25 |
| `Codigo/Telas/Inventario/InventarioItens.py` | 509 | 23.76 |
| `SimuladorServerJogo/Mundo/ObjetosMundoServer.py` | 494 | 32.06 |
| `Codigo/Telas/TelaServers.py` | 492 | 15.67 |
| `Codigo/ModulosMundo/LeitorMundo.py` | 484 | 21.81 |
| `Codigo/Prefabs/Botao.py` | 480 | 17.59 |
| `Codigo/ModulosGerais/FiltroCamera.py` | 478 | 21.53 |
| `Codigo/ModulosMundo/LeitorDialogo.py` | 478 | 19.33 |
| `SimuladorServerJogo/Gerais/Rotas/Ativador.py` | 472 | 22.16 |
| `Outros/Mixer.py` | 460 | 15.31 |
| `Codigo/Paineis/PainelReceitas.py` | 455 | 15.29 |
| `Codigo/ModulosBatalha/ControladorBatalha.py` | 453 | 21.12 |
| `SimuladorServerJogo/Mundo/InicializadorNPC.py` | 448 | 22.71 |
| `Codigo/Telas/TelasGenericas.py` | 448 | 15.30 |
| `Codigo/Telas/SubtelaDialogo.py` | 429 | 18.87 |
| `Codigo/Telas/SubtelaCriarPersonagem.py` | 423 | 15.31 |
| `Outros/AtualizadorReadMe.py` | 417 | 13.56 |
| `Codigo/Geradores/Ator.py` | 413 | 18.01 |
| `SimuladorServerJogo/Gerais/LoaderRegras.py` | 411 | 23.35 |
| `Codigo/Geradores/Player/Controle.py` | 408 | 17.28 |
| `SimuladorServerJogo/Mundo/Cerebros/CerebroCentral.py` | 402 | 20.64 |
| `Codigo/Telas/Inventario/Estatisticas.py` | 401 | 17.83 |
| `Codigo/Geradores/Estadio.py` | 394 | 14.82 |

## Top 20 maiores funções e métodos

| Arquivo | Nome | Tipo | Linhas |
|---|---|---:|---:|
| `Codigo/Paineis/VisualizadorLog.py` | `VisualizadorLog._registro_evento` | metodo | 286 |
| `Codigo/Geradores/Estadio.py` | `EstadioInterno.renderizar` | metodo | 254 |
| `Codigo/Prefabs/Fluxos.py` | `Fluxo.desenhar` | metodo | 249 |
| `SimuladorServerJogo/Gerais/Rotas/Atualizador.py` | `processar_atualizador_json` | funcao | 247 |
| `Outros/GeradorRelatorios.py` | `coletar_metricas` | funcao | 239 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | `InventarioPokemons.atualizar` | metodo | 147 |
| `Codigo/ModulosGerais/Colisor.py` | `Colisor.resolver_movimento_com_colisores` | metodo | 146 |
| `SimuladorServerJogo/Gerais/Geradores/GeradorMundo.py` | `_executar_world_generator` | funcao | 145 |
| `Codigo/Telas/TelaMapa.py` | `TelaMapa.desenhar` | metodo | 136 |
| `Outros/GeradorRelatorios.py` | `analisar_python_ast` | funcao | 132 |
| `Outros/AtualizadorRelatorios.py` | `main` | funcao | 131 |
| `Codigo/Telas/TelaMenu.py` | `TelaMenu` | funcao | 131 |
| `Outros/GeradorRelatorios.py` | `gerar_markdown` | funcao | 126 |
| `SimuladorServerJogo/Mundo/Cerebros/CerebroNPCs.py` | `CerebroNPCs.executar_tick` | metodo | 122 |
| `Codigo/Prefabs/Botao.py` | `Botao.render` | metodo | 119 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | `InventarioPokemons._reconstruir` | metodo | 118 |
| `Codigo/Cenas/CenaMundo.py` | `CenaMundo.atualizar_cena` | metodo | 114 |
| `Codigo/Telas/SubtelaCriarPersonagem.py` | `SubtelaCriarPersonagem._rebuild_layout` | metodo | 112 |
| `Outros/Mixer.py` | `main` | funcao | 109 |
| `SimuladorServerJogo/Mundo/Cerebros/CerebroItensMundo.py` | `CerebroItensMundo.executar_tick` | metodo | 101 |

## Top 20 maiores classes

| Arquivo | Classe | Linhas |
|---|---|---:|
| `Codigo/Paineis/FichaPokemon.py` | `FichaPokemon` | 1.245 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | `InventarioPokemons` | 1.033 |
| `Codigo/ModulosMundo/ControladorObjetos.py` | `ControladorObjetos` | 1.003 |
| `Codigo/Paineis/VisualizadorLog.py` | `VisualizadorLog` | 821 |
| `Codigo/ModulosBatalha/PokemonBatalha.py` | `PokemonBatalha` | 720 |
| `SimuladorServerJogo/Mundo/Cerebros/CerebroNPCs.py` | `CerebroNPCs` | 697 |
| `Codigo/ModulosMundo/ControladorPlayer.py` | `ControladorPlayer` | 693 |
| `Codigo/ModulosBatalha/MontadorJogadas.py` | `MontadorJogadas` | 674 |
| `Codigo/Geradores/PokemonMundo.py` | `Pokemon` | 663 |
| `SimuladorServerJogo/Mundo/BancoDados.py` | `BancoDadosMundo` | 658 |
| `Codigo/Paineis/FichaPokemonBatalha.py` | `FichaPokemonBatalha` | 651 |
| `Codigo/Paineis/Container.py` | `Container` | 628 |
| `SimuladorServerJogo/Batalha/PokemonBatalha.py` | `PokemonBatalha` | 610 |
| `Codigo/Cenas/CenaMundo.py` | `CenaMundo` | 559 |
| `Codigo/ModulosGerais/PokemonAnimator.py` | `PokemonAnimator` | 523 |
| `Codigo/Paineis/PainelArvoreHabilidades.py` | `PainelArvoreHabilidades` | 517 |
| `Codigo/Telas/Inventario/InventarioItens.py` | `InventarioItens` | 492 |
| `SimuladorServerJogo/Batalha/Partida.py` | `Partida` | 489 |
| `Codigo/ModulosGerais/FiltroCamera.py` | `FiltroCamera` | 469 |
| `Codigo/ModulosMundo/LeitorDialogo.py` | `LeitorDialogo` | 468 |

## Top 10 arquivos mais importados

| Arquivo | Vezes importado |
|---|---:|
| `Codigo/Prefabs/Texto.py` | 38 |
| `Codigo/Prefabs/Botao.py` | 28 |
| `SimuladorServerJogo/Mundo/BancoDados.py` | 14 |
| `SimuladorServerJogo/Gerais/EstadoServidor.py` | 14 |
| `Codigo/Geradores/ItemInventario.py` | 14 |
| `Codigo/ModulosGerais/Sonoridades.py` | 13 |
| `Codigo/ModulosGerais/Auxiliares.py` | 13 |
| `SimuladorServerJogo/Gerais/Rotas/Ativador.py` | 12 |
| `SimuladorServerJogo/Mundo/ObjetosMundoServer.py` | 11 |
| `SimuladorServerJogo/Gerais/LoaderRegras.py` | 10 |

## Top 10 arquivos que mais importam

| Arquivo | Arquivos internos importados | Imports totais | Linhas |
|---|---:|---:|---:|
| `Codigo/Cenas/CenaMundo.py` | 22 | 25 | 596 |
| `SimuladorServerJogo/Mundo/Cerebros/CerebroCentral.py` | 16 | 25 | 402 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | 14 | 21 | 1.061 |
| `Codigo/Cenas/ControladorCenas.py` | 11 | 16 | 299 |
| `SimuladorServerJogo/Gerais/Rotas/Atualizador.py` | 11 | 15 | 559 |
| `Codigo/Telas/Inventario/InventarioItens.py` | 10 | 13 | 509 |
| `Codigo/ModulosBatalha/ControladorBatalha.py` | 10 | 13 | 453 |
| `Codigo/Paineis/FichaPokemon.py` | 9 | 22 | 1.277 |
| `Codigo/Paineis/FichaPokemonBatalha.py` | 9 | 15 | 671 |
| `Codigo/Cenas/CenaCombate.py` | 9 | 12 | 249 |

## Top 10 maiores arquivos por linhas

| Arquivo | Ext | Linhas |
|---|---:|---:|
| `Legado/DiretrizesBatalha_v7_ajustada.md` | `.md` | 4.860 |
| `Legado/PlanoImplementacaoBatalha_5Fases_ajustado.md` | `.md` | 1.872 |
| `Outros/GeradorRelatorios.py` | `.py` | 1.629 |
| `Dados/Pokemon Global Server - Pokemons.csv` | `.csv` | 1.309 |
| `Codigo/Paineis/FichaPokemon.py` | `.py` | 1.277 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | `.py` | 1.061 |
| `Codigo/ModulosMundo/ControladorObjetos.py` | `.py` | 1.029 |
| `Codigo/Paineis/VisualizadorLog.py` | `.py` | 1.011 |
| `SimuladorServerJogo/Gerais/Geradores/Java/GeradorTerreno.java` | `.java` | 972 |
| `SimuladorServerJogo/Gerais/Geradores/Java/WorldGenerator.java` | `.java` | 846 |

## Linhas por extensão

![Gráfico de pizza das linhas por extensão](Outros/Relatorios/Imagens/2026-04-26_21-25-17/linhas_por_extensao_pizza.png)

| Ext | Linhas |
|---:|---:|
| `.py` | 48.844 |
| `.md` | 7.422 |
| `.json` | 4.148 |
| `.java` | 4.033 |
| `.csv` | 1.746 |
| `.toml` | 1.060 |

## Peso por extensão

![Gráfico de pizza do peso por categoria](Outros/Relatorios/Imagens/2026-04-26_21-25-17/peso_por_categoria_pizza.png)

| Ext | Arquivos | Peso | % do jogo |
|---:|---:|---:|---:|
| `.png` | 71.814 | 496.57 MB | 83.07% |
| `.ogg` | 35 | 90.64 MB | 15.16% |
| `.wav` | 9 | 3.81 MB | 0.64% |
| `.jpg` | 23 | 3.61 MB | 0.60% |
| `.py` | 170 | 2.05 MB | 0.34% |
| `.md` | 3 | 224.32 KB | 0.04% |
| `.ttf` | 2 | 196.64 KB | 0.03% |
| `.csv` | 9 | 180.84 KB | 0.03% |
| `.java` | 7 | 152.13 KB | 0.02% |
| `.mp3` | 3 | 135.71 KB | 0.02% |
| `.class` | 31 | 122.27 KB | 0.02% |
| `.json` | 29 | 106.37 KB | 0.02% |
| `.toml` | 14 | 22.04 KB | 0.00% |
| `.frag` | 1 | 7.18 KB | 0.00% |
| `.vert` | 1 | 170 bytes | 0.00% |

## Comparativo com o último relatório

| Métrica | Relatório anterior | Relatório atual | Diferença |
|---|---:|---:|---:|
| Arquivos | 72.139 | 72.152 | +13 |
| Linhas | 64.616 | 67.259 | +2.643 |
| Linhas .py | 47.153 | 48.844 | +1.691 |
| Métodos/funções | 2.705 | 2.804 | +99 |
| Classes | 154 | 155 | +1 |
| Commits | 423 | 434 | +11 |
| Tamanho | 584.14 MB | 597.81 MB | +13.67 MB |

### Top 3 commits por tamanho de diff

| Rank | Commit | Mensagem | Arquivos | Adições | Reduções | Diff total |
|---:|---|---|---:|---:|---:|---:|
| 1 | `2361df0e48a0` | NPC extremamente melhorado | 31 | 2.776 | 1.454 | 4.230 |
| 2 | `5e6c85ce5e94` | relatorio | 11 | 1.966 | 115 | 2.081 |
| 3 | `d8a8e9713599` | primeiro readme (devia ter feito faz tempo) | 4 | 700 | 0 | 700 |

## Gráficos de crescimento

![Crescimento de linhas gerais](Outros/Relatorios/Imagens/2026-04-26_21-25-17/crescimento_linhas_totais.png)

![Crescimento de linhas .py](Outros/Relatorios/Imagens/2026-04-26_21-25-17/crescimento_linhas_py.png)

![Crescimento de arquivos .py](Outros/Relatorios/Imagens/2026-04-26_21-25-17/crescimento_arquivos_py.png)

![Crescimento de commits](Outros/Relatorios/Imagens/2026-04-26_21-25-17/crescimento_commits.png)

<!-- FIM_REGISTRO_MD -->

---

<div align="center">

**Pokémon Global Server**  
Projeto em desenvolvimento contínuo.

</div>
