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
│   └── Shaders/
│       ├── mundo.frag
│       └── mundo.vert
├── Paineis/
│   ├── Container.py
│   ├── FichaAtaque.py
│   ├── FichaItem.py
│   ├── FichaPokemon.py
│   ├── FichaPokemonBatalha.py
│   ├── Musicdex.py
│   ├── PainelAcoes.py
│   ├── PainelArvoreHabilidades.py
│   ├── PainelAuxiliarPoke.py
│   ├── PainelCraft.py
│   ├── PainelEstatisticas.py
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
│   ├── GerenciadorServerList.py
│   ├── Login.py
│   ├── ServerBatalha.py
│   ├── ServerLogin.py
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
    ├── Subtela.py
    ├── SubtelaCriarPersonagem.py
    ├── SubtelaDialogo.py
    ├── SubtelaFinalizacao.py
    ├── SubtelaOpcoes.py
    ├── SubtelaPreBatalha.py
    ├── TelaConfig.py
    ├── TelaConfigAvancada.py
    ├── TelaConta.py
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
│   │   ├── AvaliadorIA.py
│   │   ├── ConfigIA.py
│   │   ├── ContextoIA.py
│   │   ├── ControladorIA.py
│   │   ├── FallbackIA.py
│   │   ├── GeradorAcoesIA.py
│   │   ├── HackerIA.py
│   │   ├── MacroSimulador.py
│   │   ├── MemoriaIA.py
│   │   ├── MetadadosAtaquesIA.json
│   │   ├── MetadadosIA.py
│   │   ├── MicroSimulador.py
│   │   └── PlanejadorIA.py
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
│   ├── ContextoServidor.py
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

**Relatório:** #48  
**Repo:** `Pokemon-Global-Server-Definitivo`  
**Gerado em:** 2026-04-27T21:44:46  
**Modelo de relatório:** 9  
**Autor:** Leon Cunha Alvaro Lopez Soto

## Visão geral

- **Pastas:** 1.256
- **Arquivos:** 72.168
- **Arquivos de texto:** 249
- **Peso dos arquivos de texto:** 3003.60 KB
- **Tamanho total:** 0.584 GB (627.069.386 bytes)
- **Dias desde a criação do repo:** 56
- **Dias desde a criação oficial:** 330
- **Horas estimadas:** 313.00
- **Linhas totais gerais:** 72.199
- **Commits (repo):** 448
- **Adições desde o último relatório:** <span style='color: green'>+7.871</span>
- **Reduções desde o último relatório:** <span style='color: red'>-1.563</span>

## Python

- **Arquivos `.py`:** 185
- **Linhas totais:** 53.072
- **Tamanho total `.py`:** 2291.21 KB
- **Classes encontradas:** 176
- **Funções encontradas:** 681
- **Métodos encontrados:** 2.385
- **Total funções + métodos:** 3.066
- **Bibliotecas diferentes usadas:** 39

## Rank das 15 pastas mais relevantes por linhas

![Gráfico de barras do rank das 15 pastas](Outros/Relatorios/Imagens/2026-04-27_21-44-46/rank_15_pastas_barras.png)

![Gráfico de pizza do rank das 15 pastas](Outros/Relatorios/Imagens/2026-04-27_21-44-46/rank_15_pastas_pizza.png)

| Rank | Pasta | Subpastas | Arquivos | Linhas gerais | Tamanho (KB) |
|---:|---|---:|---:|---:|---:|
| 1 | `ServerGerais` | 4 | 50 | 8.353 | 466.30 |
| 2 | `Paineis` | 0 | 16 | 6.680 | 297.87 |
| 3 | `Telas` | 1 | 20 | 5.981 | 237.10 |
| 4 | `ServerBatalha` | 1 | 21 | 5.785 | 255.71 |
| 5 | `Dados` | 3 | 37 | 5.236 | 271.43 |
| 6 | `ServerMundo` | 1 | 17 | 4.469 | 233.38 |
| 7 | `ModulosMundo` | 0 | 14 | 4.232 | 193.67 |
| 8 | `Outros` | 0 | 8 | 3.935 | 142.38 |
| 9 | `ModulosGerais` | 0 | 15 | 3.781 | 144.21 |
| 10 | `Prefabs` | 0 | 14 | 3.606 | 131.48 |
| 11 | `ModulosBatalha` | 0 | 11 | 3.447 | 163.64 |
| 12 | `Geradores` | 1 | 15 | 3.437 | 151.96 |
| 13 | `ServerLogica` | 3 | 23 | 3.296 | 100.58 |
| 14 | `Cenas` | 0 | 6 | 1.391 | 65.20 |
| 15 | `Server` | 0 | 7 | 706 | 24.66 |

## Top 50 maiores arquivos `.py` por linhas

| Arquivo | Linhas | Tamanho (KB) |
|---|---:|---:|
| `Outros/GeradorRelatorios.py` | 1.629 | 59.82 |
| `Codigo/Paineis/FichaPokemon.py` | 1.267 | 56.90 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | 1.061 | 48.38 |
| `Codigo/ModulosMundo/ControladorObjetos.py` | 1.029 | 50.58 |
| `Codigo/Paineis/VisualizadorLog.py` | 1.011 | 56.90 |
| `SimuladorServerJogo/Gerais/EstadoServidor.py` | 992 | 39.46 |
| `Codigo/Prefabs/Texto.py` | 806 | 30.71 |
| `Codigo/ModulosBatalha/PokemonBatalha.py` | 753 | 36.64 |
| `SimuladorServerJogo/Mundo/Cerebros/CerebroNPCs.py` | 718 | 37.89 |
| `Codigo/ModulosBatalha/MontadorJogadas.py` | 716 | 35.60 |
| `Codigo/ModulosMundo/ControladorPlayer.py` | 712 | 34.00 |
| `SimuladorServerJogo/Mundo/BancoDados.py` | 689 | 33.84 |
| `Codigo/Geradores/PokemonMundo.py` | 687 | 33.85 |
| `SimuladorServerJogo/Logica/Comandos/Comandos.py` | 686 | 28.53 |
| `SimuladorServerJogo/Gerais/Geradores/GeradorMundo.py` | 678 | 27.20 |
| `Codigo/Paineis/FichaPokemonBatalha.py` | 671 | 33.04 |
| `SimuladorServerJogo/Logica/Executes/ExecuteAtaques.py` | 656 | 24.48 |
| `SimuladorServerJogo/Batalha/PokemonBatalha.py` | 651 | 34.38 |
| `Codigo/Paineis/Container.py` | 637 | 23.33 |
| `SimuladorServerJogo/Gerais/Geradores/GeradorPokemon.py` | 622 | 25.64 |
| `Outros/AtualizadorRelatorios.py` | 619 | 21.46 |
| `Codigo/ModulosGerais/PokemonAnimator.py` | 611 | 25.09 |
| `Codigo/Cenas/CenaMundo.py` | 596 | 32.71 |
| `SimuladorServerJogo/Batalha/Partida.py` | 572 | 27.31 |
| `Codigo/Telas/TelaServers.py` | 570 | 18.40 |
| `SimuladorServerJogo/Gerais/Rotas/Atualizador.py` | 559 | 27.64 |
| `Codigo/ModulosGerais/Sonoridades.py` | 553 | 14.59 |
| `Codigo/Paineis/PainelArvoreHabilidades.py` | 547 | 26.81 |
| `Codigo/Telas/TelasGenericas.py` | 547 | 19.10 |
| `Outros/EditorSkins.py` | 514 | 19.97 |
| `Codigo/Telas/Inventario/InventarioItens.py` | 509 | 23.76 |
| `SimuladorServerJogo/Mundo/ObjetosMundoServer.py` | 494 | 32.12 |
| `Codigo/Prefabs/Botao.py` | 489 | 17.97 |
| `Codigo/ModulosMundo/LeitorMundo.py` | 484 | 22.01 |
| `SimuladorServerJogo/Batalha/BatalhaIA/AvaliadorIA.py` | 480 | 25.08 |
| `Codigo/ModulosGerais/FiltroCamera.py` | 478 | 21.53 |
| `Codigo/ModulosMundo/LeitorDialogo.py` | 478 | 19.33 |
| `SimuladorServerJogo/Gerais/Rotas/Ativador.py` | 472 | 22.18 |
| `Outros/Mixer.py` | 460 | 15.31 |
| `Codigo/Paineis/PainelReceitas.py` | 455 | 15.29 |
| `Codigo/ModulosBatalha/ControladorBatalha.py` | 453 | 21.36 |
| `SimuladorServerJogo/Mundo/InicializadorNPC.py` | 448 | 23.14 |
| `Codigo/Telas/SubtelaDialogo.py` | 429 | 18.88 |
| `SimuladorServerJogo/Mundo/Cerebros/CerebroCentral.py` | 427 | 21.80 |
| `Codigo/Telas/SubtelaCriarPersonagem.py` | 423 | 15.31 |
| `SimuladorServerJogo/Batalha/BatalhaIA/MacroSimulador.py` | 419 | 18.81 |
| `Outros/AtualizadorReadMe.py` | 417 | 13.97 |
| `Codigo/Geradores/Ator.py` | 413 | 18.02 |
| `SimuladorServerJogo/Gerais/LoaderRegras.py` | 411 | 23.36 |
| `Codigo/Geradores/Player/Controle.py` | 408 | 17.30 |

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
| `SimuladorServerJogo/Gerais/Geradores/GeradorMundo.py` | `_executar_world_generator` | funcao | 144 |
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
| `SimuladorServerJogo/Gerais/Rotas/Entrada.py` | `processar_entrada_json` | funcao | 109 |

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
| `SimuladorServerJogo/Mundo/BancoDados.py` | `BancoDadosMundo` | 661 |
| `Codigo/Paineis/FichaPokemonBatalha.py` | `FichaPokemonBatalha` | 651 |
| `Codigo/Paineis/Container.py` | `Container` | 628 |
| `SimuladorServerJogo/Batalha/PokemonBatalha.py` | `PokemonBatalha` | 610 |
| `Codigo/Cenas/CenaMundo.py` | `CenaMundo` | 559 |
| `SimuladorServerJogo/Batalha/Partida.py` | `Partida` | 546 |
| `Codigo/ModulosGerais/PokemonAnimator.py` | `PokemonAnimator` | 523 |
| `Codigo/Paineis/PainelArvoreHabilidades.py` | `PainelArvoreHabilidades` | 517 |
| `Codigo/Telas/Inventario/InventarioItens.py` | `InventarioItens` | 492 |
| `Codigo/ModulosGerais/FiltroCamera.py` | `FiltroCamera` | 469 |
| `Codigo/ModulosMundo/LeitorDialogo.py` | `LeitorDialogo` | 468 |

## Top 10 arquivos mais importados

| Arquivo | Vezes importado |
|---|---:|
| `Codigo/Prefabs/Texto.py` | 41 |
| `Codigo/Prefabs/Botao.py` | 31 |
| `SimuladorServerJogo/Gerais/EstadoServidor.py` | 16 |
| `SimuladorServerJogo/Mundo/BancoDados.py` | 14 |
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
| `SimuladorServerJogo/Mundo/Cerebros/CerebroCentral.py` | 16 | 25 | 427 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | 14 | 21 | 1.061 |
| `Codigo/Cenas/ControladorCenas.py` | 11 | 16 | 299 |
| `SimuladorServerJogo/Batalha/BatalhaIA/ControladorIA.py` | 11 | 16 | 176 |
| `SimuladorServerJogo/Gerais/Rotas/Atualizador.py` | 11 | 15 | 559 |
| `Codigo/Telas/Inventario/InventarioItens.py` | 10 | 13 | 509 |
| `Codigo/ModulosBatalha/ControladorBatalha.py` | 10 | 13 | 453 |
| `SimuladorServerJogo/Gerais/EstadoServidor.py` | 9 | 19 | 992 |
| `Codigo/Paineis/FichaPokemon.py` | 9 | 15 | 1.267 |

## Top 10 maiores arquivos por linhas

| Arquivo | Ext | Linhas |
|---|---:|---:|
| `Legado/DiretrizesBatalha_v7_ajustada.md` | `.md` | 4.860 |
| `Legado/PlanoImplementacaoBatalha_5Fases_ajustado.md` | `.md` | 1.872 |
| `Outros/GeradorRelatorios.py` | `.py` | 1.629 |
| `Dados/Pokemon Global Server - Pokemons.csv` | `.csv` | 1.309 |
| `Codigo/Paineis/FichaPokemon.py` | `.py` | 1.267 |
| `Codigo/Telas/Inventario/InventarioPokemons.py` | `.py` | 1.061 |
| `Codigo/ModulosMundo/ControladorObjetos.py` | `.py` | 1.029 |
| `Codigo/Paineis/VisualizadorLog.py` | `.py` | 1.011 |
| `SimuladorServerJogo/Gerais/EstadoServidor.py` | `.py` | 992 |
| `SimuladorServerJogo/Gerais/Geradores/Java/GeradorTerreno.java` | `.java` | 972 |

## Linhas por extensão

![Gráfico de pizza das linhas por extensão](Outros/Relatorios/Imagens/2026-04-27_21-44-46/linhas_por_extensao_pizza.png)

| Ext | Linhas |
|---:|---:|
| `.py` | 53.072 |
| `.md` | 7.685 |
| `.json` | 4.585 |
| `.java` | 4.033 |
| `.csv` | 1.746 |
| `.toml` | 1.060 |

## Peso por extensão

![Gráfico de pizza do peso por categoria](Outros/Relatorios/Imagens/2026-04-27_21-44-46/peso_por_categoria_pizza.png)

| Ext | Arquivos | Peso | % do jogo |
|---:|---:|---:|---:|
| `.png` | 71.814 | 496.57 MB | 83.04% |
| `.ogg` | 35 | 90.64 MB | 15.16% |
| `.wav` | 9 | 3.81 MB | 0.64% |
| `.jpg` | 23 | 3.61 MB | 0.60% |
| `.py` | 185 | 2.24 MB | 0.37% |
| `.md` | 3 | 243.88 KB | 0.04% |
| `.ttf` | 2 | 196.64 KB | 0.03% |
| `.csv` | 9 | 180.84 KB | 0.03% |
| `.java` | 7 | 152.40 KB | 0.02% |
| `.mp3` | 3 | 135.71 KB | 0.02% |
| `.class` | 31 | 125.12 KB | 0.02% |
| `.json` | 30 | 113.03 KB | 0.02% |
| `.toml` | 14 | 22.04 KB | 0.00% |
| `.frag` | 1 | 7.01 KB | 0.00% |
| `.vert` | 1 | 160 bytes | 0.00% |

## Comparativo com o último relatório

| Métrica | Relatório anterior | Relatório atual | Diferença |
|---|---:|---:|---:|
| Arquivos | 72.152 | 72.168 | +16 |
| Linhas | 67.259 | 72.199 | +4.940 |
| Linhas .py | 48.844 | 53.072 | +4.228 |
| Métodos/funções | 2.804 | 3.066 | +262 |
| Classes | 155 | 176 | +21 |
| Commits | 434 | 448 | +14 |
| Tamanho | 597.81 MB | 598.02 MB | +216.74 KB |

### Top 3 commits por tamanho de diff

| Rank | Commit | Mensagem | Arquivos | Adições | Reduções | Diff total |
|---:|---|---|---:|---:|---:|---:|
| 1 | `0e7dc58c00e9` | relatorio | 13 | 2.396 | 765 | 3.161 |
| 2 | `df505f9cfbb6` | Super IA de batalha | 19 | 2.415 | 647 | 3.062 |
| 3 | `579a3d40bb55` | Zipador e IA descompactada | 11 | 1.796 | 73 | 1.869 |

## Gráficos de crescimento

![Crescimento de linhas gerais](Outros/Relatorios/Imagens/2026-04-27_21-44-46/crescimento_linhas_totais.png)

![Crescimento de linhas .py](Outros/Relatorios/Imagens/2026-04-27_21-44-46/crescimento_linhas_py.png)

![Crescimento de arquivos .py](Outros/Relatorios/Imagens/2026-04-27_21-44-46/crescimento_arquivos_py.png)

![Crescimento de commits](Outros/Relatorios/Imagens/2026-04-27_21-44-46/crescimento_commits.png)

<!-- FIM_REGISTRO_MD -->

---

<div align="center">

**Pokémon Global Server**  
Projeto em desenvolvimento contínuo.

</div>
