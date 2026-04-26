# Plano de Implementação da Batalha em 5 Fases

## 1. Objetivo deste arquivo

Este arquivo transforma a **DiretrizesBatalha v7** em um roteiro prático de implementação em 5 fases.

A intenção é impedir que a implementação tente fazer tudo de uma vez. Cada fase deve gerar um resultado testável, visualmente verificável e coerente com a arquitetura final da Batalha.

A regra principal é: **cada fase precisa deixar o sistema mais funcional sem criar legado novo**.

---

## 2. Fonte de verdade

A fonte de verdade conceitual continua sendo a **DiretrizesBatalha v7**.

Este plano não substitui a v7. Ele apenas organiza a ordem de implementação.

Regras da v7 que devem ser respeitadas em todas as fases:

- O sistema se chama **Batalha**.
- `CenaCombate` é só a cena hospedeira da batalha no sistema normal de cenas.
- O cliente nunca é fonte da verdade da regra oficial.
- O servidor é a autoridade real da batalha.
- A comunicação client-servidor de batalha passa por `Codigo/Server/ServerBatalha.py`.
- O servidor trabalha com `lado_id`, nunca com `aliado`/`inimigo` como regra oficial.
- No cliente, os nomes `aliado`/`inimigo` podem existir apenas como leitura visual da UI.
- A lógica oficial usa `rodada` e `passo`.
- `tick` é apenas visual/animação no cliente.
- A energia real é gasta na execução da ação pelo servidor.
- Movimento custa `10` de energia.
- Troca custa `15` de energia.
- A energia recupera no fim da rodada.
- Efeitos formais duram em passos e decrementam no fim de cada passo global.
- O limite total é de 4 efeitos formais por Pokémon.
- O 5º efeito é bloqueado, não substitui efeitos existentes.
- Ataques miram área por padrão.
- O ocupante da área é resolvido na execução.
- Linha/coluna recalcula alvos na execução.
- Dano absorvido por barreira não conta para XP nem vampirismo.
- Não há troca automática após morte na v7.
- Captura não entra nesta implementação.
- Construtos entram só como classe/contrato mínimo.
- XP usa `rodadas`, não `turnos`.

---

## 3. Observações sobre a estrutura atual do projeto

A implementação deve levar em conta a estrutura real atual.

Arquivos e estruturas reais relevantes já presentes:

```text
Codigo/Cenas/CenaCombate.py
Codigo/ModulosBatalha/Arena.py
Codigo/ModulosBatalha/InicializadorBatalha.py
Codigo/ModulosGerais/PokemonAnimator.py
Codigo/Paineis/FichaPokemonBatalha.py
Codigo/Paineis/PainelAcoes.py
Codigo/Paineis/VisualizadorLog.py
Codigo/Prefabs/Barra.py
Codigo/Prefabs/Botao.py
Codigo/Prefabs/Painel.py
Codigo/Prefabs/Texto.py
Codigo/Telas/SubtelaFinalizacao.py
Codigo/Server/ServerMundo.py
Codigo/Server/ServerTerminal.py
SimuladorServerJogo/Gerais/Geradores/GeradorPokemon.py
SimuladorServerJogo/Logica/Executes/ExecuteAtaques.py
Dados/Pokemon Global Server - Ataques.csv
Dados/Pokemon Global Server - Efeitos.csv
Dados/Pokemon Global Server - Pokemons.csv
Dados/Pokemon Global Server - Sistema FR.csv
```

Arquivos que aparecem como `__pycache__` ou nomes antigos não devem ser tratados como fonte de verdade. Se não houver `.py` correspondente, o Codex não deve tentar reconstruir comportamento antigo a partir de `.pyc`.

Exemplos de nomes antigos/legados que não devem guiar a nova arquitetura:

```text
PlayerControleBat
ControladorJogadas
ControladorFluxos
SistemaBatalha
DebugCombate
LeitorAtaquesCombate
LeitorFluxos
MontadorJogada  # singular, se ainda aparecer em cache/legado
FichaPokemonCombate
PainelJogada
SimuladorServerJogo/Batalha/Combate/*  # se aparecer como resto legado
SimuladorServerJogo/Batalha/IA/*       # IA antiga/servidor, se for legado
```

Se houver arquivo `.py` legado real com esses nomes, ele só deve ser mantido se ainda for usado fora da batalha nova. Caso contrário, remover ou isolar sem compatibilidade artificial.

Não criar camada de compatibilidade para formato antigo de batalha.

---

## 4. Organização geral das fases

| Fase | Resultado principal | Estado esperado |
|---|---|---|
| Fase 1 | `Outros/SimuladorBatalha.py` visual e interativo | Arena, HUD, Pokémon, reserva, seleção, ficha e botões funcionando sem servidor real |
| Fase 2 | Montagem de jogadas, indicadores e início da ponte com servidor | Ações preparadas aparecem no painel e são serializadas/enviadas |
| Fase 3 | Servidor funcional com matemática e diffs | Rodada resolve corretamente, mas sem histórico bonito nem animações |
| Fase 4 | Histórico completo de logs e animações | Replay visual ordenado por evento, com leitura sólida de log |
| Fase 5 | Finalização, resultado, IA e refinamento | Ciclo completo: iniciar, jogar, resolver, animar, finalizar e voltar |

---

# FASE 1 — Simulador visual local da Batalha

## 1.1 Objetivo

Criar um simulador local simples em `Outros/SimuladorBatalha.py`, na raiz do repositório, para testar a estrutura visual e interativa inicial da Batalha sem depender ainda do servidor real.

Esta fase deve permitir abrir uma janela de teste e ver imediatamente:

- arena de batalha;
- áreas `A1` até `A9` e `I1` até `I9`;
- Pokémon ativos posicionados nas áreas;
- Pokémon da reserva desenhados fora da arena;
- HUD principal da batalha;
- ficha do Pokémon selecionado na parte inferior;
- botões de HUD;
- botão de pronto;
- botão de fuga com ícone;
- botão de modo teste;
- timer/barra de rodada;
- painel de ações preparado, ainda vazio;
- visualizador de logs, ainda vazio ou com placeholder.

A fase 1 não implementa montagem real de ataques, não resolve dano, não envia jogadas ao servidor e não lê logs reais.

O botão `Pronto` nesta fase apenas passa a rodada localmente, incrementa contador e reinicia/atualiza o timer visual.

---

## 1.2 Arquivo a criar

Criar apenas um arquivo simples na raiz do repositório:

```text
Outros/SimuladorBatalha.py
```

Não criar pasta própria para o simulador, não criar pacote, não criar `README.md` e não criar arquivos auxiliares. O simulador deve ser um arquivo único, direto e leve, vivendo de imports dos módulos úteis da Batalha, dos prefabs/painéis existentes, dos loaders/dados necessários e das funções reais de geração/materialização de Pokémon.

O arquivo deve poder ser executado diretamente:

```bash
python Outros/SimuladorBatalha.py
```

Responsabilidade desse arquivo único:

- abrir uma janela Pygame de teste;
- montar um contexto local 6v6 sem entrar no mundo;
- selecionar 6 Pokémon aleatórios para cada lado;
- usar as funções atuais de geração e materialização de Pokémon;
- sortear/associar ataques exibíveis;
- criar um estado inicial simples com 3 ativos e até 3 reservas por lado;
- inicializar `Arena`, `ControladorBatalha`, `ElementosHudBatalha`, `PlayerBatalha` e `PokemonBatalha`;
- não criar regra oficial de servidor;
- não duplicar prefabs, ficha, painel de ações ou visualizador de logs.

---

## 1.3 Arquivos do cliente a criar ou completar nesta fase

A fase 1 deve criar/ajustar os arquivos client-side mínimos, mas ainda sem lógica oficial de servidor:

```text
Codigo/ModulosBatalha/PokemonBatalha.py
Codigo/ModulosBatalha/ControladorBatalha.py
Codigo/ModulosBatalha/PlayerBatalha.py
Codigo/ModulosBatalha/ElementosHudBatalha.py
Codigo/ModulosBatalha/Arena.py
```

`Arena.py` já existe e atualmente renderiza contexto visual/fundo. Nesta fase, ela deve ser expandida para conhecer também:

- áreas do lado visual do jogador: `A1` até `A9`;
- áreas do lado visual oponente: `I1` até `I9`;
- retângulos clicáveis das áreas;
- ocupação visual das áreas;
- regiões de reserva/banco;
- conversão mouse → área;
- desenho das áreas;
- destaque de hover/seleção.

Não remover o que já existe de renderização de contexto visual se ainda for útil. A evolução da `Arena` deve somar a malha de áreas da Batalha ao fundo atual.

---

## 1.4 Geração de Pokémon aleatórios no simulador

O simulador deve gerar uma batalha local 6v6 para testar ativos e reservas.

Padrão recomendado:

```text
lado_jogador: 6 Pokémon aleatórios
lado_oponente: 6 Pokémon aleatórios
ativos iniciais por lado: 3
reservas por lado: até 3
```

Os Pokémon devem ser gerados a partir dos dados atuais do projeto:

```text
Dados/Pokemon Global Server - Pokemons.csv
Dados/Pokemon Global Server - Ataques.csv
SimuladorServerJogo/Gerais/Geradores/GeradorPokemon.py
```

A fase 1 deve usar o gerador/materializador real e pode importar tudo que for necessário para montar o contexto 6v6 local. O ponto importante é que esses imports fiquem concentrados no arquivo único `Outros/SimuladorBatalha.py` e não sejam espalhados pela UI.

A geração deve:

- sortear espécies válidas do CSV de Pokémon;
- ignorar formas especiais quando necessário para manter o teste limpo, principalmente Mega, Ultra, Gigantamax e equivalentes;
- materializar os Pokémon para formato próximo do inventário/batalha;
- sortear ataques a partir dos ataques atuais;
- garantir que cada Pokémon tenha ataques exibíveis na ficha;
- preencher vida e energia iniciais;
- atribuir `lado_id` neutro, por exemplo `50` e `51`;
- atribuir posição inicial de ativos nas áreas;
- marcar reservas como fora da arena.

A nomenclatura visual pode usar `jogador` e `oponente`, mas os dados internos já devem ter `lado_id`.

---

## 1.5 Pokémon visual de batalha

Criar `Codigo/ModulosBatalha/PokemonBatalha.py` como espelho visual da batalha.

Nesta fase ele precisa suportar:

- `id_batalha`;
- `id_original`, quando existir;
- `nome`/`Nome`;
- `especie`;
- `lado_id`;
- lado visual (`jogador`/`oponente`) apenas para UI;
- `ativo`;
- `em_reserva`;
- `vivo`;
- `area_id` para ativo;
- posição visual calculada pela arena;
- dados de atributos;
- vida atual e vida máxima;
- energia atual e energia máxima;
- barreira atual;
- lista de ataques da ficha;
- tipos;
- sprite/frame atual.

Métodos mínimos:

```text
from_serializado(dados)
serializar()
atualizar_por_diff(diff)
obter_ataques_ficha(limite=5)
desenhar(surface, camera, arena)
desenhar_reserva(surface, rect_slot)
desenhar_barras(surface)
contem_ponto(pos_mouse)
esta_ativo()
esta_na_reserva()
esta_vivo()
```

Nesta fase, `atualizar_por_diff` pode existir como stub seguro, porque ainda não há servidor real.

A classe não deve calcular dano nem regra oficial.

---

## 1.6 Arena e reservas

A arena deve desenhar 18 áreas quadradas.

IDs visuais:

```text
A1 A2 A3
A4 A5 A6
A7 A8 A9

I1 I2 I3
I4 I5 I6
I7 I8 I9
```

A distribuição exata pode ser ajustada visualmente, mas precisa ser consistente:

- lado do jogador mais abaixo/esquerda conforme a estética da cena;
- lado oponente mais acima/direita;
- 3 linhas por lado;
- 3 colunas por lado;
- áreas com centro claro para prender indicadores na fase 2;
- hover e seleção visíveis;
- área ocupada mostrando destaque leve.

Reservas:

- desenhar reservas do jogador em uma faixa lateral ou inferior próxima do HUD;
- desenhar reservas oponentes em faixa lateral ou superior;
- cada reserva precisa ter retângulo clicável;
- clicar reserva seleciona o Pokémon para visualização;
- na fase 1, reserva ainda não prepara troca real.

---

## 1.7 HUD da batalha

Criar/completar `ElementosHudBatalha.py` usando prefabs existentes, não desenho manual duplicado.

Prefabs/painéis que devem ser reutilizados:

```text
Codigo/Prefabs/Botao.py
Codigo/Prefabs/Barra.py
Codigo/Prefabs/Painel.py
Codigo/Prefabs/Texto.py
Codigo/Paineis/FichaPokemonBatalha.py
Codigo/Paineis/PainelAcoes.py
Codigo/Paineis/VisualizadorLog.py
```

HUD mínimo da fase 1:

- ficha do Pokémon selecionado na parte inferior da tela;
- botão `Pronto`;
- botão `Fugir` com ícone de fuga;
- botão/alavanca `Modo teste`;
- texto de rodada atual;
- timer/barra de rodada;
- painel de ações vazio;
- visualizador de logs vazio.

Botão de fuga:

- usar ícone de `Recursos/Visual/Icones/Diversos/Fuga.png`, ou o resolvedor atual de ícones diversos procurando por `Fuga`/`fuga`;
- se o ícone não existir no ambiente de teste, usar fallback textual sem quebrar;
- nesta fase pode não finalizar a batalha, mas deve existir visualmente e responder a hover/clique com efeito simples.

Botão de pronto:

- nesta fase não envia jogada;
- ao clicar, incrementa `rodada_atual` local;
- limpa seleção de ataque;
- mantém Pokémon selecionado ou limpa seleção conforme ficar melhor para UX;
- adiciona opcionalmente uma linha visual simples ao log local, como “Rodada X iniciada”, mas o visualizador pode continuar vazio se o foco for testar layout.

Botão de modo teste:

- usar `BotaoAlavanca` se possível;
- quando ativo:
  - ataques não devem gastar energia na prévia futura;
  - Pokémon oponentes podem ser controlados como se fossem do jogador;
  - ficha de Pokémon oponente permite seleção de ataque;
  - arraste/seleção de oponente será liberado nas fases seguintes.
- quando inativo:
  - oponente só pode ser selecionado para visualização;
  - não pode preparar ataque/movimento com oponente.

---

## 1.8 Seleção e desseleção

Implementar em `PlayerBatalha.py` e coordenar pelo `ControladorBatalha.py`.

Regras da fase 1:

- clicar em Pokémon aliado ativo seleciona o Pokémon;
- clicar no mesmo Pokémon selecionado desseleciona;
- clicar em outro Pokémon muda seleção;
- clicar em área vazia seleciona a área ou limpa seleção, conforme decidido, mas sem preparar ação ainda;
- clicar em Pokémon da reserva seleciona para visualização;
- clicar em oponente seleciona para visualização;
- se modo teste estiver ativo, oponente passa a ser controlável;
- clicar em ataque da ficha seleciona/deseleciona ataque;
- ataque com `estilo_logico = "passivo"` não deve ser selecionável;
- ataque com `estilo_logico = "ativo"` deve ser selecionável e confirmado sem alvo;
- ataque com `estilo_logico = "alvo"` deve exigir área/alvo;
- `ESC` limpa ataque selecionado primeiro, depois Pokémon/área selecionada.

A ficha `FichaPokemonBatalha` já tem suporte a seleção de ataques e controle inimigo por `definir_controle_inimigo`. A fase 1 deve reaproveitar isso.

---

## 1.9 Controlador da batalha no simulador

`ControladorBatalha.py` nesta fase deve funcionar como maestro local.

Estados mínimos:

```text
inicializando
montando_jogada
passando_rodada
encerrada
```

Componentes mínimos:

```text
self.arena
self.pokemons
self.pokemons_por_id
self.player_batalha
self.hud
self.rodada_atual
self.lado_jogador
self.modo_teste
```

Métodos mínimos:

```text
iniciar(estado_inicial)
criar_componentes()
atualizar(dt, eventos)
desenhar(surface)
selecionar_pokemon(pokemon)
selecionar_area(area_id)
selecionar_ataque(ataque)
passar_rodada_local()
alternar_modo_teste()
```

Não criar servidor falso complexo nesta fase. O simulador pode montar um `estado_inicial` local e entregar direto ao controlador.

---

## 1.10 Remoção de legado na fase 1

Nesta fase, remover ou ignorar restos que atrapalham a leitura da nova estrutura.

Regras:

- não usar `__pycache__` como fonte;
- não criar imports para módulos legados que só existem em cache;
- não manter `PlayerControleBat`, `SistemaBatalha`, `ControladorJogadas`, `ControladorFluxos`, `LeitorFluxos`, `LeitorAtaquesCombate` como base da nova Batalha;
- se algum desses existir como `.py` real e estiver morto, remover com diff clara;
- se for usado fora da batalha, não apagar cegamente: isolar e documentar.

---

## 1.11 Critérios de aceite da fase 1

A fase 1 só está pronta quando:

- o simulador abre sem precisar entrar no mundo normal;
- aparecem Pokémon ativos dos dois lados;
- aparecem reservas dos dois lados;
- aparecem as áreas da arena;
- clicar em Pokémon mostra a ficha na parte inferior;
- clicar no mesmo Pokémon desseleciona;
- clicar em ataques da ficha seleciona/deseleciona ataque;
- Pokémon oponente só é controlável se modo teste estiver ativo;
- botão de modo teste liga/desliga e muda comportamento da ficha;
- botão de pronto passa rodada local;
- botão de fuga existe com ícone/fallback;
- painel de ações aparece vazio sem erro;
- visualizador de logs aparece vazio ou com placeholder;
- não existe dependência real com servidor de batalha novo ainda;
- não houve alteração de gameplay do mundo.

---

# FASE 2 — Indicadores visuais, montagem de jogadas e início da conexão com servidor

## 2.1 Objetivo

Implementar a montagem completa de jogadas no cliente e iniciar a ponte real com o servidor.

Nesta fase, o jogador deve conseguir:

- selecionar Pokémon;
- selecionar ataque;
- escolher área alvo;
- arrastar Pokémon para movimento;
- arrastar Pokémon ativo até reserva para troca;
- ver indicadores visuais de ações;
- ver ações preparadas no painel lateral;
- remover ações preparadas;
- clicar em pronto;
- enviar a jogada serializada para a camada de servidor;
- receber resposta mínima do servidor.

A fase 2 ainda não precisa resolver dano completo. Ela prepara e envia jogadas corretamente.

---

## 2.2 Arquivos a criar ou completar

Cliente:

```text
Codigo/ModulosBatalha/MontadorJogadas.py
Codigo/ModulosBatalha/IndicadorAtaque.py
Codigo/ModulosBatalha/PlayerBatalha.py
Codigo/ModulosBatalha/ElementosHudBatalha.py
Codigo/ModulosBatalha/ControladorBatalha.py
Codigo/Server/ServerBatalha.py
```

Dados:

```text
Dados/Pokemon Global Server - PropriedadesAtaques.json
```

Servidor mínimo/ponte:

```text
SimuladorServerJogo/Gerais/Rotas/RotasBatalha.py
SimuladorServerJogo/Batalha/GerenciadorPartidas.py
SimuladorServerJogo/Batalha/Partida.py
```

Observação de estrutura:

A rota oficial da Batalha deve ficar em `SimuladorServerJogo/Gerais/Rotas/RotasBatalha.py`, seguindo o padrão real do projeto. Não criar `SimuladorServerJogo/Rotas/` duplicado e não criar reexport/camada extra sem necessidade.

---

## 2.3 JSON de propriedades dos ataques

Criar o JSON inicial de propriedades dos ataques.

O CSV de ataques continua sendo fonte simples/visual. Não editar o CSV por IA.

O JSON deve conter, no mínimo:

```json
{
  "schema_version": 1,
  "ataques": {
    "1": {
      "ID": 1,
      "Code": 1,
      "nome": "Investida",
      "custo": 40,
      "estilo_logico": "alvo",
      "alvificacao": {
        "tipo": "area",
        "quantidade": 1,
        "lados_permitidos": ["lado_oposto"],
        "exige_area_ocupada": false
      },
      "animacao": {
        "contato": "avanco",
        "projetil": null
      },
      "execute_principal": "ataque_investida"
    }
  }
}
```

Não precisa acertar balanceamento perfeito. Precisa acertar o contrato.

Campos mínimos por ataque:

- `ID`;
- `Code`;
- `nome`;
- `custo`, se sobrescrever CSV;
- `estilo_logico`;
- `alvificacao`, apenas quando `estilo_logico = "alvo"`;
- `animacao`;
- `execute_principal`;
- `execute_alvificacao`, quando existir;
- `executes_perifericos`, quando existir;
- parâmetros extras simples.

Semântica obrigatória de `estilo_logico`:

- `alvo`: o ataque exige seleção de alvo/área e possui `alvificacao`;
- `ativo`: o ataque é ativado diretamente, sem escolha de alvo; não deve trazer `alvificacao` de seleção;
- `passivo`: o ataque não é selecionável/acionável pela ficha e só roda por flags/passivas.

Regras obrigatórias:

- ataque sem JSON não roda;
- na ficha, ataque sem JSON deve aparecer bloqueado/desabilitado ou não selecionável;
- ataques com `estilo_logico = "alvo"` serializam o alvo como `area_id` por padrão;
- mesmo se o clique for no Pokémon, ataque de alvo envia a área ocupada por ele;
- ataque de alvo pode mirar área vazia por padrão;
- usar `exige_area_ocupada: true` para exceções;
- ataques com `estilo_logico = "ativo"` não serializam alvo e executam diretamente no usuário/partida;
- ataques com `estilo_logico = "passivo"` não entram na montagem manual;
- linha/coluna devem guardar a referência necessária para recalcular na execução.

---

## 2.4 Montador de jogadas

`MontadorJogadas.py` deve implementar a preparação real de ações.

Limites:

```text
5 ações por lado por rodada
2 ações por Pokémon por rodada
segunda ação do mesmo Pokémon custa +10%
movimento custa 10
entrada/troca com reserva custa 15
```

Tipos de ação iniciais:

```text
ataque
movimento
troca_posicao
troca_reserva
```

Estrutura serializada sugerida de ação:

```json
{
  "id_local": 1,
  "tipo": "ataque",
  "pokemon_id": "05001",
  "lado_id": 50,
  "rodada": 1,
  "ordem_local": 0,
  "ataque": {
    "ID": 6,
    "Code": 6,
    "nome": "Arranhar"
  },
  "alvo": {
    "tipo": "area",
    "area_id": "I5"
  },
  "custo_previsto": 35,
  "modo_teste": false
}
```

Movimento:

```json
{
  "tipo": "movimento",
  "pokemon_id": "05001",
  "lado_id": 50,
  "destino": {
    "tipo": "area",
    "area_id": "A6"
  },
  "custo_previsto": 10
}
```

Troca com reserva:

```json
{
  "tipo": "troca_reserva",
  "pokemon_id": "05001",
  "pokemon_reserva_id": "05004",
  "lado_id": 50,
  "custo_previsto": 15
}
```

Regras de montagem:

- preparar ataque ao clicar em área válida;
- preparar movimento ao arrastar para área livre do mesmo lado visual;
- preparar troca de posição ao arrastar para área ocupada por aliado;
- preparar troca de reserva ao arrastar ativo até Pokémon da reserva;
- cancelar prévia se soltar fora de destino válido;
- remover ação pelo `PainelAcoes`;
- recalcular energia prevista após remoção;
- impedir montagem óbvia se energia prevista não comportar, exceto em modo teste;
- modo teste faz custo previsto poder ser exibido, mas não bloquear por energia.

---

## 2.5 Indicadores visuais

`IndicadorAtaque.py` deve representar ataque, movimento e troca.

Não criar indicador só para ataque se isso causar duplicação futura.

Cada ação preparada deve guardar seu próprio indicador.

Estados:

```text
preparando
preparado
invalido
```

Tipos:

```text
ataque
movimento
troca_posicao
troca_reserva
```

Visual:

- ataque: setas/fluxo laranja;
- movimento: setas/fluxo azul;
- troca: linha/fluxo verde;
- inválido: vermelho;
- preparado: mais transparente;
- preparando: mais forte e animado;
- troca com reserva liga o Pokémon ativo ao slot de reserva.

O visual deve lembrar fluxo de setas:

```text
>>>>>
```

Com setas arredondadas, transparentes e sensação de movimento.

---

## 2.6 Painel de ações

A fase 2 deve integrar `Codigo/Paineis/PainelAcoes.py`.

O painel deve mostrar:

- ícone do Pokémon executor;
- ícone do ataque, movimento ou troca;
- nome da ação;
- custo previsto;
- botão de remover;
- destaque da ação em hover/seleção.

Comandos do painel:

```text
selecionar ação
remover ação
```

Remover ação deve chamar `MontadorJogadas.remover_acao(...)` e atualizar:

- lista de ações;
- energia prevista;
- indicadores;
- ficha;
- barras dos Pokémon.

---

## 2.7 Botão de pronto funcional

Na fase 2, `Pronto` deixa de apenas passar rodada local.

Fluxo:

1. HUD chama `ControladorBatalha.enviar_jogada_pronta()`.
2. Controlador pega `MontadorJogadas.gerar_pacote_jogada()`.
3. Controlador chama `Codigo/Server/ServerBatalha.py`.
4. `ServerBatalha.py` envia para a rota de batalha.
5. Servidor mínimo registra/aceita a jogada.
6. Cliente recebe resposta.

Resposta mínima aceita nesta fase:

```json
{
  "status": "ok",
  "mensagem": "Jogada recebida",
  "id_partida": "...",
  "estado_batalha": "aguardando" ou "recebido_stub",
  "avisos": [],
  "erros": []
}
```

A fase 2 deve ter apenas um servidor mínimo/stub de recebimento: ele registra/aceita a jogada e devolve resposta serializável, mas ainda não faz matemática real de dano, cura, efeitos, ordenação completa ou resultado de rodada. Essa matemática entra na Fase 3.

---

## 2.8 Integração com modo teste

Modo teste continua existindo.

Na fase 2, modo teste deve:

- permitir controlar Pokémon oponentes;
- permitir preparar ações do lado oponente;
- permitir preparar manualmente as ações dos dois lados no simulador;
- ao clicar em `Pronto`, enviar as ações dos dois lados juntas no mesmo pacote/fluxo de rodada, como acontecerá futuramente quando a IA existir;
- manter a IA desativada nesta fase, porque no teste manual o usuário faz o papel dos dois lados;
- ignorar bloqueio por energia na montagem;
- marcar no pacote se a ação foi criada em modo teste, se isso for útil para debug.

A regra oficial continua sendo do servidor. Modo teste só facilita teste visual e manual.

---

## 2.9 Critérios de aceite da fase 2

A fase 2 está pronta quando:

- selecionar ataque e clicar em área cria ação de ataque;
- arrastar ativo para área livre cria movimento;
- arrastar ativo para aliado ativo cria troca de posição;
- arrastar ativo para reserva cria troca de reserva;
- indicador aparece durante prévia;
- indicador permanece após ação preparada;
- painel de ações mostra as ações;
- remover ação funciona;
- energia prevista atualiza ficha e barra;
- modo teste remove bloqueio por energia;
- botão pronto envia pacote serializável; em modo teste, envia as ações dos dois lados juntas;
- servidor mínimo/stub recebe a jogada sem objetos Python complexos e sem resolver matemática real;
- ataque mira `area_id`, não objeto Pokémon;
- JSON de propriedades dos ataques existe e é usado pelo montador.

---

# FASE 3 — Servidor funcional com matemática e diffs, ainda sem histórico completo

## 3.1 Objetivo

Implementar o servidor inteiro da Batalha de forma funcional, mas ainda sem replay bonito.

Nesta fase, o servidor deve:

- criar partida;
- armazenar estado oficial;
- receber jogadas;
- validar ações;
- ordenar ações;
- executar rodada em passos;
- gastar energia na execução;
- resolver ataque/movimento/troca;
- aplicar dano, cura, barreira, efeitos e energia;
- recalcular atributos;
- aplicar fim de passo;
- decrementar efeitos formais;
- recuperar energia no fim da rodada;
- finalizar se um lado ficar sem Pokémon vivos;
- retornar diffs finais.

O log nesta fase pode ser feio. Ele não precisa ter histórico evento por evento ainda.

A resposta pode conter `resultado`/diff final suficiente para o cliente atualizar tudo de uma vez.

---

## 3.2 Arquivos do servidor a criar

Criar a lógica nova em fontes `.py` reais:

```text
SimuladorServerJogo/Batalha/GerenciadorPartidas.py
SimuladorServerJogo/Batalha/Partida.py
SimuladorServerJogo/Batalha/PokemonBatalha.py
SimuladorServerJogo/Batalha/ColetorAcoes.py
SimuladorServerJogo/Batalha/RodadorTurno.py
SimuladorServerJogo/Batalha/ConstrutorLog.py
SimuladorServerJogo/Batalha/FraquezasResistencia.py
SimuladorServerJogo/Batalha/Construto.py
```

Rotas/adaptação:

```text
Codigo/Server/ServerBatalha.py
SimuladorServerJogo/Gerais/Rotas/RotasBatalha.py
```

Executes:

```text
SimuladorServerJogo/Logica/Executes/ExecuteAtaques.py
SimuladorServerJogo/Logica/Executes/PassivaAtaques.py
SimuladorServerJogo/Logica/Executes/PassivaItens.py
```

Se `ExecuteAtaques.py` já existe, adaptar com cuidado. Não misturar com formato legado se ele estiver incompatível com a v7.

---

## 3.3 Gerenciador de partidas

`GerenciadorPartidas.py` deve ser o registro oficial de partidas ativas.

Responsabilidades:

- criar partida;
- localizar partida por `id_partida`;
- receber jogada;
- chamar resolução quando todos os lados necessários estiverem prontos;
- finalizar partida;
- remover partida encerrada quando apropriado.

Métodos mínimos:

```text
criar_partida(dados_inicializacao)
obter_partida(id_partida)
receber_jogada(id_partida, lado_id, jogada)
finalizar_partida(id_partida, motivo=None, dados=None)
```

Nesta fase, como a IA ainda não entra, o simulador pode:

- enviar jogadas dos dois lados manualmente em modo teste; ou
- permitir que o lado bot envie jogada vazia temporária.

Não implementar IA verdadeira aqui.

---

## 3.4 Partida

`Partida.py` é a fonte da verdade do estado de batalha.

Campos mínimos:

```text
id_partida
seed_partida
random
rodada_atual
passo_atual
lados
times
pokemons_por_id
areas
ocupacao_areas
jogadas_recebidas
clima_atual
construtos
estado
vencedor
resultado_pendente
```

Métodos mínimos:

```text
inicializar(dados)
serializar_estado_inicial()
receber_jogada(lado_id, jogada)
todos_lados_prontos()
resolver_rodada()
aplicar_fim_de_rodada()
verificar_fim_batalha()
gerar_resultado_diff()
finalizar(motivo)
```

Regras obrigatórias:

- IDs oficiais nascem no servidor;
- usar `lado_id`;
- preservar `id_original` quando existir;
- posições oficiais são áreas;
- reservas não ocupam área;
- cada lado pode ter até 3 ativos;
- não há troca automática após morte;
- captura fora do escopo.

---

## 3.5 Pokémon de batalha no servidor

`SimuladorServerJogo/Batalha/PokemonBatalha.py` deve conter a versão autoritativa.

Campos:

- `id_batalha`;
- `id_original`;
- `lado_id`;
- `ativo`;
- `reserva`;
- `area_id`;
- `vivo`;
- atributos base;
- variações temporárias;
- variações permanentes;
- atributos finais;
- `VidaAtual`;
- `EnergiaAtual`;
- `BarreiraAtual`;
- efeitos formais;
- estados transitórios;
- ataques;
- build.

Métodos oficiais:

```text
Verificar()
AplicarDano(...)
ReceberDano(...)
AplicarCura(...)
ReceberCura(...)
AplicarEfeito(...)
ReceberEfeito(...)
RemoverEfeito(...)
GastarEnergia(...)
GanharEnergia(...)
Mover(area_id)
TrocarComReserva(pokemon_reserva)
TrocarPosicao(outro_pokemon)
Morrer()
serializar()
```

Regras obrigatórias:

- dano altera `VidaAtual`, não variação temporária;
- energia real é gasta na execução;
- `EnergiaAtual` inicia em 75% de `EneM`, salvo regra explícita;
- efeito formal ocupa slot;
- máximo total de 4 efeitos;
- 5º efeito bloqueia;
- duração de efeito decrementa no fim de cada passo global;
- estado transitório não conta como efeito formal.

---

## 3.6 Coletor de ações

`ColetorAcoes.py` deve validar e ordenar ações.

Validações:

- lado existe;
- Pokémon existe;
- Pokémon pertence ao `lado_id` correto;
- Pokémon está vivo;
- Pokémon está ativo quando a ação exigir ativo;
- Pokémon de reserva só pode entrar por troca;
- limite de ações por lado;
- limite de ações por Pokémon;
- ação do Pokémon que entrou por troca na rodada atual falha;
- ataque existe no JSON;
- alvo é coerente com propriedade do ataque;
- movimento vai para área válida;
- troca com reserva usa Pokémon vivo da reserva;
- troca de posição usa ocupante válido;
- custo real pode ser calculado.

Ordenação:

```text
maior Int primeiro
empate: maior Vel
empate persistente: critério estável por seed/ID
```

A ordem visual de duas ações do mesmo Pokémon deve ser preservada entre elas quando necessário.

---

## 3.7 Rodador de turno

`RodadorTurno.py` executa a rodada em passos.

Fluxo de cada passo:

1. pegar próxima ação ordenada;
2. validar estado atual do executor;
3. checar energia atual;
4. gastar energia real se a ação for tentada;
5. executar ação;
6. aplicar métodos oficiais do Pokémon/partida;
7. rodar flags/passivas/executes periféricos quando existirem;
8. chamar `Verificar` nos Pokémon/construtos relevantes;
9. decrementar efeitos formais no fim do passo global;
10. seguir para próxima ação.

Se uma ação falhar:

- registrar falha no log/diff mínimo;
- não cancelar a rodada;
- ainda concluir fim de passo quando apropriado.

Ataques:

- resolver ocupante da área no momento da execução;
- linha/coluna recalcula alvos na execução;
- ataque em área vazia gera falha/sem alvo real se não houver alvo válido;
- ataques multi-alvo rolam acerto por alvo;
- execute de alvificação roda antes do acerto final;
- execute principal roda para alvos atingidos;
- execute periférico roda via flags.

Movimento:

- custo `10`;
- mover para área livre;
- se área ficou ocupada antes da execução, converter para troca de posição quando a regra permitir;
- se não permitir, ação falha.

Troca com reserva:

- custo `15`;
- Pokémon que sai paga a ação;
- Pokémon que entra recebe estado transitório `entrou_na_rodada`;
- Pokémon que entrou não age nessa mesma rodada.

---

## 3.8 Matemática inicial

A matemática precisa estar funcional, mesmo que possa ser refinada depois.

Dano:

```text
dano_base = poder_ataque * atributo_ofensivo / max(1, defesa_alvo)
dano_final = max(1, dano_base * multiplicadores)
```

Categorias iniciais:

- físico/normal: `Atk` contra `Def`;
- especial: `SpA` contra `SpD`;
- efeito/magia: usar `Mag` quando o ataque declarar;
- cura: usar regra do execute/JSON.

Ordem recomendada:

```text
dano base
Amp
tipo/fraqueza-resistência
STAB, se existir
crítico
defesa/perfuração
Dur
barreira
vida
```

Barreira:

- absorve depois do cálculo final;
- se `BarreiraAtual > 0`, a barreira segura ao menos aquela instância;
- dano absorvido por barreira não conta para XP;
- dano absorvido por barreira não conta para vampirismo.

Energia:

- ataques usam custo do JSON, com fallback no CSV;
- movimento custa `10`;
- troca custa `15`;
- segunda ação do mesmo Pokémon custa `+10%`;
- recuperação no fim da rodada usa `Ene`;
- modo teste pode ignorar gasto, mas apenas no simulador/cliente de teste, nunca na regra oficial normal.

---

## 3.9 ConstrutorLog simplificado

Nesta fase, `ConstrutorLog.py` pode ser simples.

Ele deve retornar estrutura com `resultado` completo e, se quiser, `historico` vazio ou mínimo.

Exemplo:

```json
{
  "id_log": "6001",
  "rodada": 1,
  "historico": [],
  "resultado": {
    "pokemons": {},
    "areas": {},
    "energia": {},
    "efeitos": {},
    "estado_batalha": "montando_jogada",
    "vencedor": null
  }
}
```

O cliente nesta fase pode aplicar diretamente o `resultado` sem replay.

---

## 3.10 Critérios de aceite da fase 3

A fase 3 está pronta quando:

- inicialização real no servidor funciona;
- partida tem `id_partida` oficial;
- Pokémon recebem `id_batalha` oficial;
- enviar jogadas resolve rodada;
- energia é gasta na execução;
- movimento move;
- troca com reserva troca;
- troca de posição troca áreas;
- ataque causa dano;
- cura cura;
- barreira absorve;
- efeito aplica respeitando limite de 4;
- 5º efeito bloqueia;
- efeitos decrementam por passo;
- energia recupera no fim da rodada;
- morte é detectada;
- fim de batalha é detectado;
- servidor retorna diff final;
- cliente aplica diff final e muda visual imediatamente;
- ainda não precisa ter replay/animação bonita.

---

# FASE 4 — Histórico completo de logs, leitor de logs e animações

## 4.1 Objetivo

Transformar a fase 3, que já funciona mas é feia, em uma batalha visualmente compreensível.

Nesta fase, o servidor deve registrar histórico evento por evento, e o cliente deve ler esse histórico em ordem, animando cada acontecimento.

A batalha passa a ter replay visual da rodada.

---

## 4.2 Arquivos a criar ou completar

Servidor:

```text
SimuladorServerJogo/Batalha/ConstrutorLog.py
SimuladorServerJogo/Batalha/RodadorTurno.py
SimuladorServerJogo/Batalha/PokemonBatalha.py
```

Cliente:

```text
Codigo/ModulosBatalha/LeitorLogs.py
Codigo/ModulosBatalha/ControladorAnimacoes.py
Codigo/ModulosGerais/PokemonAnimator.py
Codigo/ModulosBatalha/ControladorBatalha.py
Codigo/Paineis/VisualizadorLog.py
```

`VisualizadorLog.py` já existe e deve ser reaproveitado.

`PokemonAnimator.py` já existe e deve ser ampliado sem virar regra de batalha.

---

## 4.3 Histórico do servidor

O `ConstrutorLog` deve registrar eventos estruturados.

Eventos mínimos:

```text
rodada_iniciada
acao_iniciada
acao_falhou
ataque_usado
ataque_sem_alvo_real
ataque_errou
ataque_acertou
pokemon_sofreu_dano
pokemon_recebeu_cura
pokemon_ganhou_barreira
barreira_absorveu
pokemon_recebeu_efeito
efeito_bloqueado_por_limite
efeito_tickou
efeito_expirou
pokemon_gastou_energia
pokemon_ganhou_energia
pokemon_moveu
pokemon_trocou_posicao
pokemon_trocou_reserva
pokemon_entrou
pokemon_saiu
pokemon_morreu
rodada_finalizada
batalha_finalizada
```

Cada evento deve ter:

```text
id_evento
rodada
passo
tipo
timestamp_logico ou ordem
ids envolvidos
dados antes/depois quando necessário
valores numéricos relevantes
area_id quando houver posição
ataque_id quando houver ataque
```

O histórico não precisa conter snapshots completos em todo evento.

O `resultado` final continua obrigatório para consolidar o estado.

Estrutura final:

```json
{
  "id_log": "6001",
  "rodada": 1,
  "historico": [
    {"tipo": "acao_iniciada", "passo": 1},
    {"tipo": "pokemon_gastou_energia", "passo": 1},
    {"tipo": "ataque_usado", "passo": 1},
    {"tipo": "pokemon_sofreu_dano", "passo": 1}
  ],
  "resultado": {
    "pokemons": {},
    "areas": {},
    "estado_batalha": "montando_jogada"
  }
}
```

---

## 4.4 Leitor de logs

`LeitorLogs.py` deve ler o histórico em ordem.

Responsabilidades:

- receber log do servidor;
- separar `historico` e `resultado`;
- processar um evento por vez;
- mandar texto/registro para o HUD;
- mandar evento para `ControladorAnimacoes`;
- aplicar diffs intermediários quando fizer sentido;
- aguardar animações bloqueantes;
- ao fim, aplicar `resultado` final;
- devolver controle para montagem se a batalha não acabou;
- chamar finalizador se a batalha acabou.

Estados:

```text
parado
lendo
aguardando_animacao
consolidando
finalizado
```

Falhas:

- evento sem animação deve passar seco;
- erro de ação entra no visualizador de logs, mas não precisa travar replay;
- evento desconhecido deve gerar aviso em debug e continuar.

---

## 4.5 Controlador de animações

`ControladorAnimacoes.py` converte eventos em animações.

Animações mínimas:

- ataque usado;
- projétil;
- avanço;
- salto;
- dano;
- cura;
- barreira;
- aplicação de efeito;
- morte/desmaio;
- movimento;
- troca de posição;
- troca com reserva;
- cartucho flutuante de dano/cura/energia/efeito.

Regras:

- animação não decide regra;
- posição final vem do log/diff;
- projétil é interpolação visual;
- avanço/salto são interpolação visual;
- animações importantes podem bloquear o próximo evento;
- cartuchos e efeitos pequenos podem ser não bloqueantes.

---

## 4.6 PokemonAnimator

`PokemonAnimator.py` deve concentrar animações relacionadas ao Pokémon.

Métodos esperados:

```text
animar_morrer(pokemon)
animar_tomar_dano(pokemon, valor=None)
animar_receber_cura(pokemon, valor=None)
exibir_cartucho(pokemon, texto, tipo)
animar_lancar_projetil(origem, destino, sprite=None)
animar_avanco(pokemon, destino)
animar_salto(pokemon, destino)
animar_troca(pokemon_saida, pokemon_entrada)
animar_sofrer_ataque(pokemon, dados_evento)
atualizar(dt)
desenhar(surface)
```

Ele pode ter fila própria de animações, mas não deve virar `RodadorTurno` visual.

---

## 4.7 Visualizador de logs

O visualizador deve ficar mais vivo nesta fase.

O servidor não precisa mandar texto pronto como fonte principal.

O cliente deve gerar textos amigáveis a partir dos eventos estruturados.

Exemplos:

```text
Pikachu usou Investida em I5.
Charmander sofreu 34 de dano.
Bulbasaur ganhou Queimado.
Squirtle tentou agir, mas não tinha energia.
A barreira de Snorlax absorveu 50 de dano.
```

Se o `VisualizadorLog.py` atual já monta registros com tooltip e segmentos, reaproveitar isso.

---

## 4.8 Critérios de aceite da fase 4

A fase 4 está pronta quando:

- servidor retorna `historico` completo e `resultado`;
- cliente não aplica tudo instantaneamente antes do replay;
- eventos são lidos em ordem;
- animações ocorrem na ordem correta;
- dano aparece com animação/cartucho;
- cura aparece com animação/cartucho;
- movimento/troca têm animação;
- morte/desmaio aparece e depois remove/some da arena;
- visualizador de logs mostra acontecimentos;
- ao fim, resultado final consolida estado;
- se a batalha não acabou, volta para montagem;
- se a batalha acabou, chama finalização.

---

# FASE 5 — Finalização, tela de resultados, IA e refinamento geral

## 5.1 Objetivo

Completar o ciclo da Batalha.

Nesta fase entram:

- finalização real de partida;
- tela de resultados;
- persistência final de vida e XP;
- fuga completa;
- IA do lado selvagem/oponente;
- integração mais madura com `CenaCombate` e fluxo do mundo;
- refinamento geral;
- limpeza final de legado;
- testes finais.

---

## 5.2 Finalizador da batalha

Criar/completar:

```text
Codigo/ModulosBatalha/FinalizadorBatalha.py
```

Responsabilidades:

- receber resultado final oficial;
- detectar vencedor/perdedor pelo resultado do servidor;
- aplicar vida final dos Pokémon do jogador;
- aplicar XP recebido;
- abrir subtela de resultados quando apropriado;
- finalizar fluxo e voltar ao mundo;
- chamar `ServerBatalha.finalizar_batalha(...)`;
- limpar estado temporário da batalha.

Regras:

- apenas vida e XP persistem;
- energia não persiste;
- barreira não persiste;
- efeitos de batalha não persistem;
- buffs/debuffs não persistem;
- captura não entra;
- fuga não abre subtela de resultados, salvo se depois for decidido o contrário;
- fim normal abre tela de resultados.

---

## 5.3 Tela de resultados

Reaproveitar:

```text
Codigo/Telas/SubtelaFinalizacao.py
```

Ela já possui base para:

- título de final da batalha;
- rodadas totais;
- vencedor/derrota;
- cards por Pokémon;
- XP animado;
- dano;
- abates;
- energia gasta;
- botão continuar.

A fase 5 deve adaptar o `FinalizadorBatalha` para montar os itens esperados por essa subtela.

Dados por Pokémon:

```text
nome
visual
xp_batalha
dano
abates
energia_gasta
morto
```

Também deve corrigir nomenclatura:

```text
rodadas_totais
```

Nunca voltar a usar `turnos` para XP.

---

## 5.4 XP e persistência

Fórmula base da v7:

```text
xp_base = dano_causado + energia_gasta + rodadas * 10
xp_final_por_pokemon = xp_base * multiplicador
```

Regras:

- dano absorvido por barreira não conta como dano causado para XP;
- energia gasta conta;
- rodadas conta;
- fuga reduz XP pela metade;
- multiplicador individual entre `0.75` e `1.5`;
- persistir apenas vida final e XP.

O cálculo oficial deve vir do servidor ou do resultado oficial, não ser inventado pela subtela.

---

## 5.5 Fuga completa

O botão de fuga já deve existir desde a fase 1.

Na fase 5 ele deve fechar o ciclo.

Comportamento:

- cada clique no botão de fuga aumenta escurecimento da tela;
- a tela clareia naturalmente com o tempo;
- cliques rápidos o suficiente completam a fuga;
- ao completar, cliente chama `ServerBatalha.finalizar_batalha(..., motivo="fuga")`;
- servidor finaliza oficialmente;
- XP é reduzido pela metade;
- não abre subtela de resultados;
- volta ao mundo normal;
- aplica imunidade curta contra reabrir combate imediatamente, se o fluxo do mundo já tiver esse padrão.

---

## 5.6 IA no cliente

Criar:

```text
Codigo/ModulosBatalha/IA/ControladorIA.py
```

A IA fica no cliente.

Ela deve montar jogada para o `lado_id` controlado por bot e enviar pelo mesmo caminho do jogador:

```text
ControladorIA
  -> Montador/serializador de jogada
  -> Codigo/Server/ServerBatalha.py
  -> RotasBatalha
  -> GerenciadorPartidas
  -> Partida
```

A IA inicial não precisa ser inteligente, mas precisa ser funcional.

Comportamento inicial recomendado:

- localizar Pokémon ativos vivos do lado controlado;
- ignorar Pokémon sem energia suficiente, salvo movimento/troca simples;
- escolher ataque com `estilo_logico = "alvo"` ou `estilo_logico = "ativo"`; nunca escolher ataque `passivo` como ação manual;
- priorizar alvo em área ocupada por adversário;
- se não houver alvo bom, pode mirar área provável ou enviar jogada vazia;
- ocasionalmente mover para área livre;
- evitar troca com reserva salvo se ativo estiver morto ou muito fraco;
- respeitar limite de 5 ações por lado;
- respeitar limite de 2 ações por Pokémon;
- usar RNG derivado da `seed_partida` quando sortear.

Importante:

- servidor permanece neutro;
- servidor não escolhe ações por conta própria;
- IA não deve usar nomenclatura servidor de `inimigo`/`aliado` como regra oficial;
- no cliente pode traduzir visualmente o lado do bot.

---

## 5.7 Integração com CenaCombate

`Codigo/Cenas/CenaCombate.py` já existe e atualmente cuida de contexto visual de combate, terminal e transição.

Na fase 5, integrar o fluxo novo sem destruir a estrutura de cena:

- `CenaCombate.Inicializar` deve criar/acionar o `InicializadorBatalha` ou `ControladorBatalha` real;
- `render_base` desenha arena/Pokémon/animações de mundo;
- `render_post` pode receber filtros/pós-processo futuros;
- `render_hud` desenha HUD, terminal e subtelas;
- terminal não deve bloquear eventos da batalha quando não estiver digitando;
- `ESC` deve respeitar a cadeia de cancelamento da batalha antes de abrir opções, quando aplicável;
- fim da batalha deve retornar ao mundo pelo fluxo normal.

Não colocar regra de dano, jogada ou log dentro de `CenaCombate`.

---

## 5.8 Refinamento geral

A fase 5 também deve revisar o sistema inteiro.

Checklist:

- nomes de arquivos seguem v7;
- nenhum arquivo novo usa `Combate` como nome de sistema, salvo `CenaCombate` existente;
- nenhum servidor usa `aliado`/`inimigo` como regra persistida;
- cliente usa `aliado`/`inimigo` só para visual;
- nenhum módulo fora de `ServerBatalha.py` chama diretamente `GerenciadorPartidas`;
- nenhum CSV é editado por IA;
- JSON de propriedades é validado;
- ataque sem JSON não roda;
- modo teste não vaza para regra normal;
- histórico de log não substitui `resultado` final;
- resultado final sempre consolida estado;
- `SubtelaFinalizacao` recebe dados corretos;
- não há captura;
- construtos continuam mínimos;
- não há troca automática após morte;
- energia e efeitos respeitam v7.

---

## 5.9 Critérios de aceite da fase 5

A fase 5 está pronta quando:

- uma batalha completa pode iniciar, rodar e terminar;
- IA consegue jogar pelo lado selvagem/oponente;
- jogador consegue jogar sem modo teste;
- modo teste continua funcionando;
- vitória abre tela de resultados;
- derrota abre fluxo coerente de fim;
- fuga finaliza sem tela de resultados;
- XP aparece animado;
- vida final e XP persistem;
- energia/efeitos/barreira não persistem;
- logs e animações rodam antes da finalização;
- voltar ao mundo funciona;
- não há legado novo;
- os testes principais passam.

---

# 6. Testes por fase

## Fase 1

Testes manuais:

- abrir simulador;
- ver 6v6 com ativos e reservas;
- selecionar/desselecionar Pokémon;
- selecionar ataque;
- alternar modo teste;
- selecionar oponente com e sem modo teste;
- clicar pronto e ver rodada mudar;
- verificar HUD, ficha, painel de ações e visualizador de logs.

## Fase 2

Testes manuais e unitários leves:

- preparar ataque;
- preparar movimento;
- preparar troca de posição;
- preparar troca com reserva;
- remover ação;
- recalcular energia;
- enviar pacote ao servidor;
- validar JSON serializável;
- validar que alvo de ataque é `area_id`.

## Fase 3

Testes automatizados recomendados:

- inicialização de partida;
- IDs oficiais;
- ordem por `Int` e desempate por `Vel`;
- gasto real de energia;
- falta de energia falha sem cancelar rodada;
- dano;
- cura;
- barreira;
- vampirismo não conta barreira;
- XP não conta barreira;
- limite de 4 efeitos;
- bloqueio do 5º efeito;
- decremento de efeito por passo;
- recuperação de energia no fim da rodada;
- movimento;
- troca;
- morte sem troca automática;
- fim de batalha.

## Fase 4

Testes visuais:

- cada evento importante aparece no histórico;
- replay respeita ordem;
- animação de dano;
- animação de cura;
- animação de projétil;
- animação de avanço/salto;
- animação de troca;
- animação de morte;
- evento sem animação não quebra o leitor;
- resultado final consolida estado.

## Fase 5

Testes finais:

- batalha completa contra IA;
- vitória;
- derrota;
- fuga;
- tela de resultados;
- XP e vida persistidos;
- volta ao mundo;
- modo teste ainda funcional;
- sem captura;
- sem construtos complexos;
- sem server usando `aliado`/`inimigo` como regra.

---

# 7. Ordem recomendada de commits

Uma divisão segura de commits seria:

```text
1. Criar SimuladorBatalha e mocks visuais locais
2. Completar Arena/PokemonBatalha/ControladorBatalha/HUD básicos
3. Integrar FichaPokemonBatalha, PainelAcoes e VisualizadorLog
4. Criar JSON de propriedades dos ataques e loader mínimo
5. Implementar MontadorJogadas e IndicadorAtaque
6. Criar ServerBatalha e rotas mínimas
7. Criar GerenciadorPartidas/Partida/PokemonBatalha server
8. Implementar ColetorAcoes/RodadorTurno/Executes
9. Implementar diffs e aplicação imediata no cliente
10. Implementar ConstrutorLog completo
11. Implementar LeitorLogs/ControladorAnimacoes/PokemonAnimator
12. Implementar FinalizadorBatalha/SubtelaFinalizacao/XP/fuga
13. Implementar IA cliente
14. Limpeza geral de legado e testes finais
```

Cada commit deve rodar e deixar algo verificável.

---

# 8. Regras de qualidade para o Codex

Durante a implementação:

- não fazer patch gigante sem necessidade;
- preferir diffs cirúrgicas por fase;
- não alterar gameplay do mundo fora do necessário para entrar/sair da batalha;
- não editar CSVs de dados por IA;
- não criar compatibilidade com batalha velha;
- não depender de `.pyc`;
- não espalhar import direto do servidor no cliente, exceto no ponto temporário de inicialização/simulador;
- não deixar `ServerBatalha.py` retornar objetos Python complexos;
- serializar tudo em dicionários/listas simples;
- não mover lógica oficial para HUD;
- não colocar regra oficial em animação;
- não colocar regra oficial em `CenaCombate`;
- não criar IA no servidor;
- não implementar captura;
- não implementar construtos complexos;
- não trocar nomenclatura para `turno` quando a regra fala `rodada`;
- remover código morto quando ficar claro que não serve mais ao sistema novo.

---

# 9. Resultado final esperado

Ao fim das 5 fases, o sistema deve permitir:

1. iniciar batalha de confronto;
2. montar jogadas com ataques, movimento e troca;
3. enviar jogadas ao servidor;
4. resolver rodada no servidor;
5. receber histórico e resultado;
6. animar acontecimentos em ordem;
7. continuar para novas rodadas;
8. finalizar por vitória, derrota ou fuga;
9. mostrar resultado quando apropriado;
10. persistir apenas vida e XP;
11. voltar ao mundo normal.

Esse é o ciclo mínimo completo da Batalha v7.
