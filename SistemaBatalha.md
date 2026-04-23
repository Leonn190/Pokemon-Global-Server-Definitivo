# SistemaBatalha

**Projeto:** Pokemon Global Server  
**Natureza deste arquivo:** consolidação única de **diretrizes**, **arquitetura** e **plano de implementação** do novo modelo de batalha.  
**Regra de manutenção:** este arquivo substitui a separação entre os três documentos anteriores e passa a concentrar tudo em um único `.md`, preservando o conteúdo já fechado e aplicando apenas os ajustes solicitados nesta rodada.

---

# PARTE I — DIRETRIZES

## DIRETRIZES DE BATALHA
**Projeto:** Batalha / Pokemon Global Server  
**Data-base consolidada:** 2026-04-22

> Este documento é a consolidação única e acumulativa das diretrizes de batalha discutidas até aqui.  
> Ele substitui a ideia de “modelos separados” como referência de trabalho: daqui em diante, a intenção é manter **um único arquivo vivo**, sempre atualizado sem apagar conteúdo útil já fechado.  
> Quando houver evolução futura, o ideal é complementar, corrigir e reorganizar este mesmo documento.

---

## 0. OBJETIVO DO DOCUMENTO

Este documento define as diretrizes oficiais atuais da nova batalha.

Ele deve ser usado como base para repensar o fluxo inteiro da batalha, especialmente no servidor.  
O modelo atual do código deve ser tratado como legado: algumas ideias visuais e estruturas de apoio podem ser reaproveitadas, mas o núcleo lógico de ordenação, simulação, dano, física, arena, clima, objetos, efeitos, logs, ataques e execução deve ser reestruturado.

A batalha nova não deve ser um remendo do modelo atual.  
A lógica principal deve ser uma simulação autoritativa por ticks, com o servidor decidindo o resultado real e o cliente atuando principalmente em montagem visual, arena, preview e animação dos logs.

---

## 1. PRINCÍPIOS GERAIS

### 1.1. Servidor autoritativo

O servidor é a fonte real da batalha. Ele deve validar e simular:

- ordem das ações;
- energia;
- intervalo de ativação;
- movimento;
- aceleração/desaceleração;
- colisões;
- dano;
- cura;
- barreira;
- efeitos;
- clima;
- efeitos de tile da arena;
- morte;
- cancelamentos;
- criação/finalização de projéteis e objetos;
- histórico detalhado;
- resultado final/diff.

O cliente pode prever visualmente, mas não decide o que realmente aconteceu.

### 1.2. Cliente como montador e animador

O cliente deve manter principalmente:

- arena e elementos visuais;
- HUD de batalha;
- montagem visual de jogadas;
- previews fiéis usando os dados técnicos dos ataques;
- indicadores de área, projétil, zona, laser, dash, impulso, alvo e status;
- leitura/animação do histórico enviado pelo servidor;
- correção final pelo resultado/diff do turno.

### 1.3. Dados estruturados acima de texto

A execução real dos ataques não deve depender de parsing de descrição textual.

As descrições continuam existindo para o jogador, mas o servidor deve executar ataques a partir de JSON técnico estruturado.

O CSV pode continuar existindo como tabela simples/humana, mas o JSON técnico de **PropriedadesAtaque** deve ser a fonte de verdade para:

- estilo;
- hitbox;
- física;
- multiplicador de dano;
- condições;
- propriedades de colisão;
- propriedades de ricochete;
- propriedades de atravessar;
- comportamento de fim em colisões quando o estilo usar projétil;
- dados visuais do ataque.

O JSON técnico do ataque deve carregar, de forma explícita, os nomes técnicos dos executes do ataque quando eles existirem, para dar mais segurança ao contrato dos dados.

Campos técnicos recomendados:

- execute principal;
- execute de estado, quando existir;
- lista de executes periféricos, quando existirem.

Flags técnicas internas do fluxo não precisam viver no JSON base. O construtor e os dispatchers continuam responsáveis por ligar esses executes ao fluxo real da ação.

### 1.4. Código atual como legado

A análise dos zips mostra que o modelo atual concentra muita coisa em poucos pontos, especialmente no servidor:

- `SimuladorServerJogo/Batalha/LeitorJogadas.py` mistura ordenação, interpretação de ataques, cálculo de dano, execução, física, objetos, logs e IA.
- `SimuladorServerJogo/Batalha/SimuladorFisica.py` já tem uma física parcial, mas usa fórmula de velocidade diferente da nova diretriz.
- `SimuladorServerJogo/Batalha/PokemonBatalha.py` já possui `Verifica()`, atributos, dano, cura, barreira, energia e efeitos, mas várias fórmulas atuais não batem com este novo modelo.
- `Codigo/ModulosBatalha/MontadorJogada.py` tem ideias reaproveitáveis: limite de ações, ações por Pokémon, energia reservada, ordem de criação e posição virtual.
- `Codigo/ModulosBatalha/ControladorFluxos.py` tem ideias reaproveitáveis para UX, mas o modelo antigo de fluxos de batalha deve ser substituído.
- `Codigo/ModulosBatalha/LeitorFluxos.py` deve ser apagado para a batalha nova. Fluxos antigos podem continuar existindo fora da batalha se ainda forem úteis em outro contexto.
- `Codigo/ModulosBatalha/LeitorLogs.py` tem base útil como leitor/animação, mas o formato de histórico deve mudar para o novo histórico por eventos de tick.

---

## 2. PIPELINE MACRO DA BATALHA

### 2.1. Origem da batalha

Uma batalha nasce como:

- **Confronto**
- **Batalha contra treinador**
- **PvP**

Leitura fechada:

- **Confronto** = encontrar um Pokémon selvagem no mundo e batalhar contra ele;
- **Batalha contra treinador** = batalha contra um NPC que controla uma equipe inteira;
- **PvP** = batalha contra outro player online.

### 2.2. Partida

Quando a batalha nasce, o servidor cria um objeto de **Partida**.

A **Partida** é o dono do estado vivo da batalha.

Ela deve concentrar pelo menos:

- participantes;
- arena, incluindo os efeitos de tile da arena;
- clima;
- `TickGlobal`;
- turno atual;
- Pokémon ativos e reservas;
- objetos de batalha existentes;
- log geral da partida;
- estado de vitória/derrota/encerramento.

### 2.3. Gerenciador de Partidas

A Partida é acompanhada por um **Gerenciador de Partidas**, responsável pela camada externa de ciclo de vida:

- criação;
- registro;
- busca;
- encerramento;
- limpeza;
- roteamento.

### 2.4. Inicialização no servidor

A inicialização real da batalha também existe no servidor. Ela inclui pelo menos:

- criação dos Pokémon de batalha;
- criação/configuração da arena;
- definição do estado inicial da partida;
- definição do clima inicial, se houver;
- definição dos ativos e reservas.

Os Pokémon usados dentro da batalha devem ser cópias de batalha independentes do estado fora da batalha.

### 2.5. Pipeline oficial repetido

Depois da inicialização, o jogo entra no ciclo repetido de:

1. **Montar Jogada** (client)
2. **Rodar Jogada** (server)
3. **Animar Jogada** (client)

Depois disso:

- finaliza turno;
- inicia novo ciclo.

### 2.6. Estado macro da partida

Deve existir formalmente um estado de Partida, pelo menos conceitualmente, cobrindo fases como:

- montando jogadas;
- aguardando envio/espera;
- rodando turno;
- animando turno;
- encerrada.

No modelo atual, **encerrada** não é apenas um rótulo de “acabou e sumiu”.
Ela representa o momento final em que o sistema confere o resultado/log com o estado real da partida, fecha o resultado autoritativo e prepara o desligamento definitivo da batalha.

### 2.7. Disparo da simulação do turno

O servidor só começa a rodar a jogada quando ambos os lados enviaram as ações, ou quando o sistema decidir resolver ausência de envio com ações vazias/timeout.

Em PvP, deve existir explicitamente um estado de espera quando um lado já enviou e o outro ainda não.

---

## 3. TEMPO, TICKS E TURNO

### 3.1. Tick global e tick do turno

Devem existir dois conceitos:

- **TickGlobal:** representa o tick acumulado da partida inteira, atravessando todas as rodadas.
- **tick:** representa o tick local do turno atual e começa sempre em 0.

O log público do turno usa tick local começando em 0.  
O servidor pode manter `TickGlobal` internamente para estado, depuração, seed, replay e sincronização geral.

`TickGlobal` avança 1 a cada tick processado ao longo de toda a partida.

### 3.2. Ordenação inicial por Inteligência
Cada ação do turno possui apenas **dois momentos temporais formais** na timeline:

- **tick_nascimento_acao**
- **tick_ativacao**

O `tick_nascimento_acao` de cada ação no turno é definido com base na Inteligência.

**Fórmula oficial:**

```text
tick_nascimento_acao = maior_Int_da_partida - Int_do_pokemon
```

O `tick_ativacao` da ação é dado por:

```text
tick_ativacao = tick_nascimento_acao + intervalo
```

Exemplo:

```text
maior Int = 230
Pokémon com Int 230 nasce no tick 0
Pokémon com Int 200 nasce no tick 30
Pokémon com Int 15 nasce no tick 215
```

A ação já existe como objeto Python na fila desde o seu `tick_nascimento_acao`.  
A ativação real dela acontece no `tick_ativacao`.

Inteligência pode ser negativa.  
Não existe limite máximo oficial de Inteligência.

Se, em um caso extremo, a diferença de Inteligência for tão absurda que o `tick_nascimento_acao` passe do timeout do turno, o resultado aceitável do modelo atual é o Pokémon simplesmente não agir naquele turno.

### 3.3. Empate de tick

Se dois ou mais Pokémon começam no mesmo tick, o sistema deve tentar tratar como evento simultâneo.

Quando houver concorrência dentro das etapas do tick e for inevitável aplicar uma ordem interna real de disputa, deve-se usar a **Velocidade do atuante** para definir essa disputa.

Se ainda houver empate técnico, a implementação pode usar ordem estável determinística, desde que o log registre a ordem usada.

### 3.4. Morte e cancelamento

Morte é imediata.

Se um Pokémon morrer antes de sua ação começar, a ação é cancelada.  
Se morrer durante a ação, a ação pode ser interrompida conforme o tipo da ação.

Efeitos também podem cancelar ações, especialmente efeitos como:

- Dormindo;
- Congelado;
- Recuo;
- Enraizado;
- Protegido;
- outros impedimentos.


Projéteis e outros objetos já criados não são cancelados pela morte posterior do Pokémon de origem se já ganharam vida própria.

### 3.5. Duração do turno

O turno termina quando tudo que depende dos ticks terminar:

- ações em andamento;
- movimentos;
- dashes;
- impulsos;
- lasers;
- projéteis ativos;
- colisões pendentes;
- efeitos por tick acionados durante a simulação;
- qualquer evento criado por ação que ainda precise ser resolvido.

Durante a preparação das jogadas, os efeitos ficam pausados.  
Efeitos só perdem duração durante a simulação real do turno.

### 3.6. Timeout

O turno deve ter timeout de segurança de **1000 ticks**.

Se algo ainda estiver ativo depois de 1000 ticks, o servidor deve encerrar/forçar a resolução segura e registrar no histórico que houve timeout de simulação.

---

## 4. CICLO DO TURNO E RODADOR DE TICKS

### 4.1. Organização inicial do turno

Quando o servidor recebe as ações dos dois lados, ele:

- valida as ações;
- organiza as ações em ordem;
- define o `tick_nascimento_acao` de cada uma e, a partir dele, o `tick_ativacao` da ação somando o intervalo.

A validação deve acontecer antes da simulação real do turno.

### 4.2. Leitura oficial do rodador
O núcleo do rodador do turno passa a ser lido assim:

1. verificar se existe ação para ativar no tick atual;
2. ativar as ações desse tick e registrar sua ativação;
3. seguir as ações já em curso que precisem continuar;
4. seguir os objetos de batalha que tenham comportamento próprio em curso naquele tick, como projéteis e construtos ativos;
5. rodar o detector global de colisões do tick para os **objetos de batalha**;
6. impedir colisão duplicada no mesmo tick entre o mesmo par de objetos;
7. disparar os executes correspondentes a ativação, colisão, impacto ou outro ponto técnico;
8. aplicar o que esses executes chamarem nos métodos dos Pokémon/objetos;
9. processar timers, expirações e efeitos por tick;
10. rodar a `Verifica()` no fim do tick, na ordem: **Pokémon -> Construtos -> Partida**;
11. registrar mortes, cancelamentos, finalizações e mudanças de estado;
12. verificar se ainda existe ação em curso ou ação futura para ser feita;
13. encerrar o turno quando não existir mais nenhuma dessas coisas.

Regras fechadas dessa leitura:

- o detector global roda **todo tick** para checar colisão entre os objetos de batalha do sistema, isto é: **Pokémon, Construto, Projétil e Parede**;
- a colisão não fica restrita apenas a objetos em movimento;
- a própria resolução da colisão deve impedir que os objetos continuem se sobrepondo naquele mesmo tick, salvo quando existir propriedade de atravessar;
- quando existir atravessar, o sistema precisa registrar que um objeto está **atravessando** o outro para evitar nova colisão inválida em todo tick seguinte enquanto a travessia ainda estiver acontecendo;
- se um par de objetos já colidiu naquele tick, o motor não pode resolver de novo esse mesmo par naquele mesmo tick;
- áreas e lasers **não** entram nesse detector global, porque não são filhos da hierarquia de objeto de batalha; eles usam detecção própria dentro de suas próprias classes, conforme avanço ou atuação no tick.

### 4.3. Resumo curto do rodador
Leitura resumida oficial do rodador:

- **ativar ações do tick**;
- **seguir ações/objetos em curso e resolver o detector global de colisões dos objetos de batalha**;
- **verificar no fim do tick, na ordem Pokémon -> Construtos -> Partida**.

### 4.4. Verifica()
A `Verifica()` ocorre **no fim do tick**.

Ela deve continuar existindo como rotina única, mas internamente pode ser dividida em **três métodos principais**, mantendo os três dentro do fluxo oficial da `Verifica()`:

1. **recalcular temporários**;
2. **avaliar ambiente**;
3. **fechar estado final**.

Dentro dessa leitura, a `Verifica()` deve:

- resetar variações temporárias;
- resetar flags temporárias;
- resetar multiplicadores temporários;
- reaplicar efeitos ativos;
- recalcular atributos atuais;
- avaliar o clima atual e suas consequências persistentes ou por tick;
- avaliar o tile em que o Pokémon se encontra no fim do tick;
- aplicar clamps de vida/energia/barreira quando couber;
- marcar restrições como `pode_agir`, `pode_atacar`, `pode_mover` etc.;
- processar estados como morto/imortal/evasivo quando necessário;
- **não** recalcular `EneM` a partir de `Ene`, pois `EneM` é fixada no início da batalha.

Para a parte de tile, o modelo já fecha duas leituras diferentes:

- **ao entrar no tile**;
- **já está no tile**.

Para isso, o Pokémon deve guardar pelo menos sua **última posição/tile relevante** para o motor distinguir entrada de permanência.

No modelo atual, **não existe efeito específico de saída de tile**.

Para construtos, também pode existir `Verifica()` própria.  
Para projéteis e paredes, em princípio isso não parece necessário.

A ordem atual de verificação no fechamento do tick é:

1. **Pokémon**;
2. **Construtos**;
3. **Partida**.

### 4.5. Ordem relativa de clima, tile, efeitos e colisão
As decisões já fechadas são:

- clima, tile e efeitos podem atuar em momentos diferentes do tick, conforme o evento;
- a `Verifica()` ocorre no fim do tick, na ordem **Pokémon -> Construtos -> Partida**;
- quando a lógica for “perguntar se o Pokémon está em um tile de efeito”, deve-se usar a posição atual do Pokémon naquele momento;
- em média, **colisões acontecem durante o seguir das ações/objetos**, antes do fechamento final do tick;
- clima, quando mexe na velocidade de passagem de efeitos, age **antes** do gasto natural de duração daquele tick;
- tile, em média, é avaliado depois do movimento e depois das colisões, usando a posição final relevante daquele momento;
- a distinção entre **entrou no tile** e **já estava no tile** depende do histórico de posição/tile salvo no próprio objeto.

### 4.6. Condição de parada do rodador

O rodador do turno não termina quando “acabou a lista inicial de ações”.  
Ele só termina quando:

- não há mais ação em curso;
- não há mais ação futura para iniciar;
- não há mais objeto de batalha com comportamento pendente que ainda precise ser resolvido.

### 4.7. Finalização do turno

Quando o rodador terminar, a própria **Partida** chama sua rotina de **finalizar turno**.

Essa rotina deve, no mínimo:

- consolidar resultados;
- fechar o log do turno;
- atualizar `TickGlobal`;
- verificar derrota/vitória/empate/encerramento da partida;
- preparar o próximo ciclo de montagem de jogadas, se a partida continuar.

### 4.8. Vitória e derrota

A verificação formal de vitória/derrota da partida ocorre em `finalizar_turno()`.

---

## 5. AÇÕES

### 5.1. Tipos gerais de ação
Leitura macro atual das ações:

- **ataque**;
- **deslocamento**;
- **troca**.

Dentro disso, o projeto ainda usa nomes práticos de estilos/ações, como:

- movimento normal;
- dash;
- impulso;
- alvo;
- status;
- troca.

Em especial, a leitura atual aceita considerar **ataque como um tipo de ação com vários estilos**, por exemplo:

- projétil;
- área;
- zona;
- alvo;
- status;
- laser;
- passivo;
- outros.

**Observação de implementação:** dash e impulso não devem viver na hierarquia principal como filhos de ataque.  
Eles são deslocamentos com execute ofensivo acoplado quando houver, e na implementação ficam mais próximos de `Mover`.

### 5.2. Ação como objeto

Toda ação é um objeto temporal de execução.

Pokémons e construtos criam ações por método próprio.  
Essas ações já existem como objetos Python enquanto estão na fila do turno.

Essa ação pode ser, por exemplo:

- movimento;
- troca;
- ataque.

Ataques ainda se subdividem por estilo, podendo existir classes próprias por estilo:

- projétil;
- área;
- alvo;
- status;
- laser;
- dash;
- impulso;
- outros.

Ações também podem criar objetos de batalha durante a simulação, quando a regra do estilo ou do execute pedir.

### 5.3. Ações instantâneas e duradouras

Uma ação pode ser:

- instantânea no tick;
- ou durar múltiplos ticks.

Muitas ações possuem **intervalo**, ou seja, um tempo de espera entre a criação da ação e o começo da sua execução real.

### 5.4. Limites por turno
Limite por lado:

```text
5 ações por turno por lado
```

Limite por Pokémon:

```text
2 ações por Pokémon por turno
```

Um Pokémon não pode repetir a mesma ação no mesmo turno.

Regras importantes:

- não pode usar o mesmo ataque duas vezes no mesmo turno;
- não pode mover duas vezes no mesmo turno;
- se fizer 2 ações, elas precisam ser diferentes;
- movimento + dash é permitido;
- dash + impulso é permitido;
- movimento + ataque é permitido;
- ataque + outro ataque é permitido **se forem ataques diferentes**;
- passivo não conta como ação preparada manualmente;
- troca conta como ação, mas não custa energia.

### 5.5. Segunda ação
A segunda ação do mesmo Pokémon custa **10% a mais de energia**.

```text
custo_segunda_acao = custo_base * 1.10
```

Não haverá terceira ação no modelo atual.

O acréscimo de 10% aplica para tudo que custa energia, **com exceção já fechada do movimento normal**, que não recebe essa cobrança adicional.

Troca não custa energia.  
Movimento deve respeitar a cobrança especial por deslocamento real.

### 5.6. Ordem das ações do mesmo Pokémon

As ações do mesmo Pokémon são executadas na ordem em que foram criadas no cliente.

A segunda ação começa **1 tick depois** da primeira ação terminar.  
Se a primeira ação for interrompida antes do fim esperado, a segunda ação começa 1 tick depois da interrupção.

### 5.7. Intervalo de ativação

A timeline formal da ação usa apenas estes dois momentos:

- `tick_nascimento_acao`
- `tick_ativacao`

A ação nasce no `tick_nascimento_acao` definido pela Inteligência.  
A ativação real dela acontece no `tick_ativacao`, que é o resultado de `tick_nascimento_acao + intervalo`.

Exemplo:

```text
ação nasce no tick 0
intervalo de ativação = 5
ataque ativa de fato no tick 5
```

Se `intervalo = 0`, nascimento e ativação podem coincidir no mesmo tick.

O log deve registrar pelo menos:

- nascimento da ação;
- ativação real do ataque quando houver;
- término/cancelamento da ação.

### 5.8. Término da ação por estilo

Regras oficiais:

- **Projétil:** a ação termina quando o projétil é criado. O projétil passa a ter vida própria.
- **Múltiplos projéteis com intervalo:** a ação dura até o último projétil ser criado.
- **Laser:** a ação termina apenas quando o laser acaba.
- **Área instantânea:** termina no mesmo tick em que aplica.
- **Zona instantânea:** termina no mesmo tick em que aplica.
- **Status:** termina no mesmo tick em que aplica.
- **Alvo instantâneo após intervalo:** termina quando o impacto nos alvos for resolvido.
- **Alvo múltiplo com intervalo entre alvos:** dura até o último alvo ser resolvido.
- **Movimento normal:** termina ao chegar no destino ou ao ser interrompido.
- **Dash:** tratado como movimento; termina ao chegar, ser interrompido, colidir conforme regra, ou resolver seu impulso pós-colisão.
- **Impulso:** termina quando a velocidade chega a zero ou quando a simulação o considera finalizado.
- **Troca:** dura 5 ticks.

### 5.9. Troca
Troca:

- conta como ação;
- não custa energia;
- usa a Inteligência do Pokémon que está saindo;
- tem duração de 5 ticks;
- é concluída **no tick 5**;
- deve ser cancelada se o Pokémon que sairia morrer antes de executar a troca;
- deve ser logada com início, execução/final e diff dos ativos/reservas.

Durante a janela da troca, o Pokémon que está saindo:

- continua em campo;
- pode tomar dano;
- pode ser alvo;
- pode se mover.

Se ele sofrer empurrão/impulso no meio da troca, a troca **não** é cancelada por isso.  
O que acontece é o intervalo efetivo aumentar até o empurrão acabar, e a conclusão da troca ocorre no pós-empurrão.

O Pokémon que entra aparece na mesma posição final deixada pelo anterior, no próprio momento em que a troca se conclui, durante o **prosseguir ações já iniciadas** e antes da `Verifica()`.  
Como o efeito de tile pertence ao tile, e não ao Pokémon, o Pokémon que entrar já passa a sofrer normalmente o tile daquela posição.

Ao sair por troca, os efeitos do Pokémon anterior são zerados na reserva.

### 5.10. Injeção de novas ações durante o turno

Ações podem gerar novas ações durante o turno.

O exemplo mais claro é a criação de um projétil que vem com sua própria ação de se mover.

Portanto, o sistema deve aceitar criação de novas ações/rotinas internas durante a simulação, desde que respeite as regras do motor.

### 5.11. Regra mínima de intervalo para objetos/ações criados

Objetos criados durante um tick **não passam a agir no mesmo tick**.  
Deve existir pelo menos **1 tick de intervalo** entre criação e execução do novo comportamento.

Exceção fechada:
- se o objeto nascer **já colidindo** com algo no mesmo tick da criação, essa colisão é resolvida imediatamente naquele mesmo tick, conforme as propriedades do objeto.

## 6. EXECUTES, FLAGS E MÉTODOS DOS POKÉMON

### 6.1. Regra central de arquitetura

Ações **não** devem alterar diretamente o estado interno do Pokémon.

Leitura arquitetural oficial:

- **Ação** dispara **execute**;
- **Execute** chama **métodos do Pokémon**;
- **Métodos do Pokémon** alteram estado.

### 6.2. Execute como núcleo da lógica do ataque

O **execute** é o núcleo principal da lógica do ataque.

Funções possíveis de execute:

- causar dano;
- curar;
- aplicar efeito;
- aplicar barreira;
- mutar status;
- criar projétil;
- explodir em área;
- alterar velocidade de projétil;
- aumentar dano após ricochete;
- executar alvo abaixo de X% de vida;
- criar construto;
- alterar arena/clima;
- modificar atributos;
- criar novas ações/novos ataques derivados;
- outras ações técnicas.

Ataques sem dano, como status puro, também devem usar execute para manter uniformidade.



### 6.3. Execute principal

O **execute principal** é o execute central do ataque.

Leitura atual:

- em ataque de projétil ou laser, é ele que normalmente roda quando houver colisão/impacto relevante com Pokémon;
- ele pode chamar métodos dos Pokémon/objetos;
- ele pode mutar a própria ação em andamento;
- ele pode alterar propriedades da ação depois de uma colisão, como reduzir dano após o primeiro impacto;
- ele pode criar novas ações ou novos ataques derivados quando a regra pedir.

Exemplo já aceito: um ataque como **Bola Climática** pode, ao atingir o alvo, criar um novo ataque de zona sobre o Pokémon atingido com multiplicador de dano reduzido.

### 6.3.1. Execute de estado

Além do execute principal, o sistema pode possuir um **execute de estado**.

Leitura atual:

- ele é separado do execute principal;
- é especialmente útil para ataques e projéteis que precisam **mudar o próprio estado** ou gerar um comportamento derivado sem poluir o execute principal;
- ele pode criar uma nova ação ou um novo ataque derivado;
- ele pode ajustar propriedades da própria ação/objeto depois de um impacto relevante;
- ele continua passando pelo fluxo normal do sistema, sem virar mutação solta fora do motor.

Exemplo já aceito: em um caso como **Bola Climática**, o impacto pode disparar um execute de estado que cria uma nova ação de ataque de zona sobre o alvo atingido.
Nesse caso, a ação derivada pode nascer com uma lista de **imunes_ao_ataque**, permitindo que o próprio alvo gerador fique imune ao ataque derivado quando a regra técnica exigir isso.

### 6.4. Executes periféricos

Além do execute principal, o sistema pode usar **executes periféricos**.

Leitura atual:

- execute periférico é um pedaço de lógica do ataque que pega carona nas flags espalhadas pelos métodos do Pokémon;
- se o ataque precisa mudar algo dentro de `tomar_dano()`, `curar()`, `receber_efeito()` ou outro método, isso pode ser feito por execute periférico chamado pela flag correta;
- isso evita obrigar o retorno de todos os detalhes pelos métodos só para alimentar o ataque depois;
- o log registra o que importa, e os executes periféricos entram no momento certo do método.

### 6.5. Execução por estilo

Exemplos oficiais:

- **Projétil:** cria um projétil com execute de ataque embutido que roda em toda colisão relevante.
- **Área:** o execute roda quando atinge na área.
- **Laser:** a ação calcula a faixa a cada tick; quando atinge, resolve o execute.
- **Alvo:** o execute inicia após o intervalo e resolve direto no alvo.
- **Status:** idem, sem precisar de colisão.
- **Dash:** é deslocamento com execute ofensivo acoplado quando colide.
- **Impulso:** é deslocamento desacelerado com execute ofensivo acoplado em colisões.

### 6.7. Flags do sistema

O núcleo do ataque continua sendo o execute, não a flag.

Ao mesmo tempo, o sistema usa **um conjunto único de flags**, principalmente consumido por passivas e pelos executes periféricos disparados de dentro dos métodos.

Ou seja:

- não existe distinção estrutural entre “flag de ataque” e “flag de passiva”;
- existe um conjunto único de flags do sistema;
- métodos chamados durante a resolução podem disparar essas flags no ponto correto.

Exemplos conceituais de flags:

- `AoCurar`
- `AoSerCurado`
- `AoGanharBarreira`
- `AoAplicarBarreira`
- `AoGanharEnergia`
- `AoGastarEnergia`
- `AoCausarDano`
- `AoReceberDano`
- `AoAplicarEfeito`
- `AoReceberEfeito`
- `AoMorrer`
- `AoAbater`
- `AoIniciarTurno`
- `AoTick`
- `AoColidir`
- `AoCancelarAcao`

### 6.8. Executes periféricos dentro dos métodos

Quando um método de Pokémon, construto ou outro objeto é chamado a partir de um **execute principal**, esse método pode receber junto os **executes periféricos** do ataque.

Leitura operacional:

- o execute principal chama o método;
- o método roda sua lógica normal;
- no ponto apropriado, o método dispara a flag correspondente;
- após essa flag, os executes periféricos recebidos podem rodar.

Isso mantém o sistema simples: passivas e reacts continuam ancorados nas flags do método, enquanto o ataque ainda consegue injetar lógica periférica no momento certo.

### 6.9. Métodos do Pokémon como única interface normal de alteração

Os Pokémon são afetados pelos seus próprios métodos.  
Esses métodos são a **interface normal oficial** para alterar o estado do Pokémon.

Exemplos:

- `tomar_dano()`
- `causar_dano()`
- `curar()`
- `aplicar_efeito()`
- `ganhar_barreira()`
- outros.

Clima e tile também devem chamar métodos dos Pokémon quando forem produzir efeitos reais neles.

### 6.10. Retorno dos métodos

Os métodos dos Pokémon **não precisam retornar todos os detalhes** do que aconteceu.

Leitura atual:

- eles podem retornar apenas o mínimo útil para o fluxo continuar quando necessário;
- o log registra o que realmente importa para histórico, debug e replay;
- a existência de executes periféricos reduz a necessidade de inflar o retorno só para o ataque reagir depois.

### 6.11. Passivas rodando dentro dos métodos

Passivas de item e habilidade rodam **dentro dos métodos** dos Pokémon.

Essas passivas podem:

- alterar resultado;
- disparar efeitos;
- modificar dano;
- chamar outros métodos.

### 6.12. Colisão regular e métodos dos Pokémon

Em colisão regular Pokémon vs Pokémon, ambos são tratados como atacantes e defensores.

Ambos passam por aplicar dano e tomar dano.

Ou seja, o resolvedor central da colisão precisa chamar métodos de ambos.

### 6.13. Ataque passivo como estilo

Ataque/efeito passivo pode ficar temporariamente no mesmo JSON de ataques, mas não é preparado manualmente.  
Ele só reage às flags apropriadas.

### 6.14. Ataque irregular

Ataque irregular exige classe/caso próprio.  
Ainda assim, quando possível, deve usar o mesmo sistema de dados, executes, logs e métodos.

---

## 7. POKÉMON: ATRIBUTOS E ESTADOS

### 7.1. Atributos principais
A lista oficial de atributos da batalha é:

- Vida: vida máxima;
- Atk: ataque físico/normal;
- SpA: ataque especial;
- Def: defesa contra dano normal/físico;
- SpD: defesa especial;
- Mag: magia, usada em aplicação e defesa de efeitos;
- Ene: energia, usada para recuperação de energia;
- Vel: velocidade base;
- Per: perfuração;
- Int: inteligência;
- Vamp: vampirismo;
- Peso: peso/massa física;
- Esc: escala/tamanho/hitbox;
- CrC: chance de crítico;
- CrD: dano crítico adicional;
- Dur: durabilidade;
- Amp: amplificação;
- EneM: energia máxima;
- Acuracia: capacidade de acertar outros Pokémon;
- Assertividade: capacidade de outros Pokémon acertarem este Pokémon.

### 7.2. Estados separados dos atributos

Alguns valores são estados atuais, não apenas atributos:

- `VidaAtual`
- `EnergiaAtual`
- `BarreiraAtual`
- efeitos positivos ativos
- efeitos negativos ativos
- posição
- vetor/velocidade física atual
- vivo/morto
- ações pendentes/em andamento

### 7.3. Vida

Vida como atributo representa vida máxima.  
A vida atual deve ser estado separado.

### 7.4. Energia máxima

Energia máxima é definida no início da partida como atributo próprio:

```text
EneM = Ene_base * 3
```

Ela é fixada no início da batalha e se torna atributo base próprio.  
Depois disso, não deve ser recalculada todo tick a partir de Ene.

Efeitos que alteram Ene não alteram automaticamente EneM, salvo se algum execute/passiva mexer explicitamente em EneM.

### 7.5. Barreira

Barreira é estado de barreira atual, não atributo principal como Vida máxima.

**Mecânica especial de barreira:**

Se existe qualquer barreira antes de uma instância de dano, a barreira segura a instância inteira de dano antes de chegar na vida.

Exemplo:

```text
dano = 3948
barreira = 1
resultado: barreira vira 0 e vida não perde nada nessa instância
```

Outro exemplo:

```text
dano = 30
barreira = 100
resultado: barreira vira 70 e vida não perde nada
```

A barreira não tem máximo oficial e não expira por padrão.  
Barreira conta como vida extra para receber dano, mas não conta como Vida para execução por porcentagem de vida.

### 7.6. Escala

Esc altera tamanho/hitbox/área de contato.  
Não altera automaticamente Peso.

Esc pode ficar negativa como valor interno/modificador, mas o tamanho final mínimo efetivo de um Pokémon na batalha é **0.5 tile**.

### 7.7. Peso

Peso é usado em:

- física de colisão;
- potência física;
- custo de movimento;
- atrito, junto com propriedades do deslocamento.

Na potência física, o peso usado é dividido por 10.

Peso não pode ficar negativo.

### 7.8. Durabilidade, amplificação e vampirismo
**Durabilidade:**

```text
Dur = redução percentual de dano recebido
```

Exemplo: Dur 20 reduz 20% do dano final recebido.

**Clamp oficial atual de Durabilidade:**

```text
Dur <= 100
```

**Amplificação:**

```text
Amp = aumento percentual de dano causado
```

Exemplo: Amp 20 aumenta 20% do dano causado.

**Clamp oficial atual de Amplificação:**

```text
Amp >= -100
```

**Vampirismo:**

```text
Vamp = percentual de cura baseado no dano que tirou vida
```

Exemplo: Vamp 10 cura 10% do dano que realmente removeu `VidaAtual`.

Dano absorvido apenas por barreira não gera cura de Vamp por padrão, embora ainda conte como instância de dano sofrida para outras reações que dependam de “receber dano”.

### 7.9. Crítico

CrC é chance percentual direta.

```text
CrC = 25 significa 25% de chance
```

CrD é bônus percentual de dano crítico.

```text
CrD = 5 significa multiplicar o dano crítico por 1.05 no trecho de crítico
```

O modelo de crítico deve usar o CrD como aumento percentual, não como valor fixo.



#### Acurácia e Assertividade

Acuracia e Assertividade nascem em **100** por padrão.

Nenhuma das duas pode ficar negativa. Ambas podem ultrapassar **100**.

Leitura atual:

- **Acuracia** = capacidade de você acertar;
- **Assertividade** = capacidade de o outro conseguir te acertar.

A forma percentual atual deve ser lida multiplicando os fatores.

Exemplo conceitual:

```text
Acuracia_origem = 100
Assertividade_alvo = 50

chance_relativa_de_acerto = 1.0 * 0.5 = 0.5
```

Ou seja, a leitura prática é:

```text
chance_relativa_de_acerto = (Acuracia_origem / 100) * (Assertividade_alvo / 100)
```

Valores acima de 100% significam, na prática, acerto garantido contra checagens normais de acerto, salvo bloqueios absolutos como `Protegido`.

### 7.10. Valores negativos

Atributos podem ficar negativos.

Defesa negativa aumenta o dano usando a fórmula de defesa negativa estilo LoL.  
Velocidade negativa não move o Pokémon para trás; ela apenas impede movimento efetivo.

### 7.11. Fórmula geral de atributo atual

A cada `Verifica()`, o valor real de um atributo deve ser:

```text
valor_real = base + variacao_permanente + variacao_temporaria
```

### 7.12. Variação temporária

Variação temporária é causada por efeitos e outras condições temporárias.

Ela deve ser resetada todo tick durante `Verifica()` e depois reaplicada conforme os efeitos ativos.

### 7.13. Variação permanente

Variação permanente/fixa é causada por passivas, habilidades, ataques ou fatores externos que alterem o Pokémon de forma mais estável.

Ela não reseta todo tick.

### 7.14. Somadores e multiplicadores

O sistema deve aceitar tanto:

- variação flat: `+20 Atk`;
- variação percentual: `+20% Atk`;
- multiplicador final: `dano causado +20%`;
- multiplicadores de sistema, como custo de energia, dano recebido, cura recebida etc.

Efeitos percentuais devem usar multiplicador, salvo quando o dado especificar aumento flat.

---

## 8. ENERGIA

### 8.1. Recuperação

A recuperação normal de energia ocorre **no fim/resolução do turno**.

No modelo atual, Pokémon ativos recuperam energia equivalente ao seu **Ene atual**, respeitando os modificadores que estiverem valendo naquele momento.

A recuperação de energia é afetada por:

- Descarregado;
- Energizado;
- tile Energizado;
- outras passivas.

### 8.2. Limite

A energia normalmente é limitada por EneM.

Energizado permite:

- recuperar 50% mais energia;
- não possuir limite de energia enquanto ativo.

Diretriz atual: enquanto Energizado estiver ativo, o clamp por EneM não é aplicado.  
Quando o efeito acabar, a energia excedente **permanece** acima de EneM. Porém, sem Energizado ativo, o Pokémon **não pode continuar aumentando** sua energia acima desse limite excedente; o excesso só persiste até ser naturalmente gasto ou até o valor voltar para a faixa normal.

### 8.3. Custo de ataque/status/dash/impulso
Ataques e ações que possuem custo pagam energia no começo da ação.  
Se a ação for interrompida antes de ativar, a energia já gasta não é devolvida.

Exceção fechada para **deslocamentos**, especialmente:

- movimento normal;
- dash.

Nesses casos, a energia deve ser descontada **ao longo do deslocamento**, acompanhando o movimento real.

Se o Pokémon não tiver energia suficiente para iniciar o deslocamento, ele não inicia.  
Mas, se a energia acabar no meio do movimento/dash depois que ele já começou, o deslocamento continua até sua resolução normal.

### 8.4. Movimento normal
Movimento cobra energia pelo deslocamento real feito, não pelo deslocamento planejado.

**Fórmula oficial:**

```text
custo_por_tile = min(30, round(Peso / 20)) + 5
```

O custo é proporcional e aceita decimal.

Exemplo:

```text
custo_por_tile = 8
deslocamento real = 2.5 tiles
custo = 20
```

Se o movimento foi planejado para 5 tiles, mas colisões fizeram o Pokémon mover só 2, cobra apenas o que moveu.

No modelo atual, esse custo é descontado **ao longo do movimento**, e não em um pacote único no começo. A cobrança ocorre **antes do passo** de cada avanço do deslocamento.  
Além disso, **movimento normal como segunda ação não recebe o acréscimo de 10%**.

### 8.5. Validação client/server

O cliente pode usar custo estimado para impedir preparação impossível.  
O servidor aplica a verdade.

Se, no servidor, uma ação não puder ser paga, ela deve ser cancelada.  
Porém, em fluxo normal, isso não deve acontecer se o cliente montou certo.

---

## 9. MOVIMENTO

### 9.1. Fórmula de velocidade de movimento
A velocidade bruta do atributo continua sendo `Vel`, mas a leitura operacional de deslocamento passa a usar **velocidade de movimento**.

**Fórmula oficial:**

```text
velocidade_de_movimento = max(0, Vel + 50)
tiles_por_tick = velocidade_de_movimento / 400
```

Exemplos:

```text
Vel = 150 -> velocidade_de_movimento = 200 -> 0.5 tiles por tick
Vel =   0 -> velocidade_de_movimento =  50 -> 0.125 tiles por tick
Vel = -50 -> velocidade_de_movimento =   0 -> 0 tiles por tick
```

Assim, qualquer valor de `Vel <= -50` zera o deslocamento efetivo.

O nome oficial útil para a implementação passa a ser:

- `Vel`: atributo base;
- `velocidade_de_movimento`: velocidade efetiva usada para deslocar;
- `tiles_por_tick`: conversão espacial final usada na simulação.

### 9.2. Movimento normal
Movimento normal:

- todo Pokémon pode fazer;
- define uma posição alvo;
- move em velocidade uniforme;
- não tem aceleração por padrão;
- usa `velocidade_de_movimento = max(0, Vel + 50)`;
- converte para deslocamento com `tiles_por_tick = velocidade_de_movimento / 400`;
- se colidir, deixa de tentar chegar no alvo antigo;
- após colisão, pode virar um impulso físico com nova direção, velocidade inicial e desaceleração.

Ao entrar em tile Gelado, a posição alvo deixa de ser o fim obrigatório do deslocamento; ao chegar no alvo planejado, o Pokémon continua se movendo até desacelerar completamente.

### 9.3. Dash
Dash é tratado como movimento com habilidade embutida.

- usa velocidade percentual do Pokémon;
- normalmente não tem aceleração/desaceleração própria enquanto está no dash puro;
- pode ter limite fixo ou configurável;
- pode ter distância mínima e máxima;
- pode atravessar Pokémon se a configuração permitir;
- pode causar dano por colisão física;
- pode ter execute próprio;
- pode terminar ou continuar conforme diferença de peso/velocidade/potência;
- ao bater em parede, pode causar dano e ricochetear para longe conforme o coeficiente de restituição e propriedades técnicas.

**Fórmula recomendada:**

```text
Vel_efetiva = Vel * percentual
velocidade_de_movimento = max(0, Vel_efetiva + 50)
tiles_por_tick = velocidade_de_movimento / 400
```

Energia de dash deve ser descontada ao longo do próprio dash, seguindo a mesma leitura geral dos deslocamentos.

### 9.4. Impulso
Impulso:

- não tem alcance fixo;
- tem velocidade inicial;
- tem desaceleração;
- é controlado pelo jogador pela distância do mouse;
- intensidade vai de percentual mínimo até percentual máximo;
- usa direção escolhida pelo jogador;
- jogador perde controle basicamente até parar;
- ricocheteia em colisões em vez de ser simplesmente cancelado;
- pode ricochetear em parede e Pokémon;
- causa dano por colisão física normalmente;
- pode ter execute próprio;
- normalmente não pode ser cancelado manualmente no meio do impulso.

Mapeamento visual:

- seta mais grossa e menos transparente conforme maior intensidade;
- intensidade deve ser mapeada linearmente da distância do mouse até o limite, salvo se um ataque específico definir outra curva.

**Leitura oficial do impulso:**

1. definir uma velocidade base do impulso a partir de `Vel * percentual`;
2. converter isso em **velocidade de movimento** somando `+50` e aplicando clamp mínimo 0;
3. converter para deslocamento espacial usando `/ 400`;
4. a cada tick, reduzir a **velocidade de movimento** pela desaceleração vinda do atrito;
5. quando a velocidade de movimento chegar a 0, o impulso acaba.

**Fórmula-base:**

```text
Vel_impulso_base = Vel * percentual
velocidade_de_movimento = max(0, Vel_impulso_base + 50)
tiles_por_tick = velocidade_de_movimento / 400

a cada tick:
    velocidade_de_movimento = max(0, velocidade_de_movimento - desaceleracao_por_tick)
```

Assim, o impulso para de verdade quando a velocidade de movimento zera.  
Não existe mais o problema de “parou, mas ainda anda” enquanto a velocidade já está em 0.

### 9.5. Empurrão por colisão

Movimento causado por colisão não conta como ação do Pokémon e não gasta energia.

### 9.6. Atrito
O atrito:

- é uma constante física de sistema para deslocamentos com desaceleração;
- depende do peso do objeto;
- pode ser alterado pelo tile em que o deslocamento ocorre.

A leitura operacional atual é:

```text
desaceleracao_por_tick = coeficiente_de_atrito * Peso
desaceleracao_por_tick = clamp(desaceleracao_por_tick, minimo=5, maximo=40)
```

Essa desaceleração atua sobre a **velocidade de movimento**, e não diretamente sobre `Vel`.

Ou seja:

```text
velocidade_de_movimento = max(0, velocidade_de_movimento - desaceleracao_por_tick)
tiles_por_tick = velocidade_de_movimento / 400
```

Coeficientes oficiais atuais:

- **base:** `0.15`
- **tile Gelado:** `0.05`
- **tile Destruído:** `0.25`

Leitura prática:

- **tile Gelado:** quase não freia; reduz bastante a desaceleração;
- **tile Destruído:** freia mais que o normal;
- movimento normal e dash não usam desaceleração gradual por padrão enquanto estão no seu deslocamento “puro”, mas essa física entra quando o deslocamento vira impulso, empurrão ou deslizamento.

### 10.1. Definição fixa

Tudo que está na batalha é um **objeto de batalha**.

Os quatro tipos principais são:

- **Pokémon**
- **Projétil**
- **Parede**
- **Construto**

Essa distinção existe para facilitar especialmente a parte da colisão e da atualização por tick.

### 10.2. Propriedades gerais

Todos possuem pelo menos:

- posição;
- área de colisão.

Nem todos possuem:

- vida;
- massa;
- velocidade ativa.

Velocidade só existe quando o objeto está se movendo.

### 10.3. Forma da colisão

A forma padrão é circular.

- Pokémon: normalmente círculo.
- Projétil: normalmente círculo.
- Construto: normalmente círculo, salvo caso irregular configurado.
- Parede: é o único caso padrão que não é círculo; sua colisão é retangular.

### 10.4. Objetos fixos

Existem objetos fixos.  
Objeto fixo nunca pode se mover, não importa a potência do que o atinja.

Parede é fixa por definição.  
Alguns construtos também podem ser fixos.

Parede não usa massa numérica; usa flag de fixo.

### 10.5. Massa

Nem todo objeto possui massa.

- Pokémon: possuem massa via Peso.
- Projétil: pode ou não ter massa.
- Construto: na maioria dos casos tem massa, mas pode não ter.
- Parede fixa: não usa massa; sua imobilidade vem da flag fixa.

### 10.6. Projéteis
Projéteis:

- são objetos de batalha independentes depois de criados;
- guardam a origem que os lançou;
- guardam seus executes e dados técnicos relevantes;
- possuem ação interna de movimento;
- atualizam sua posição por tick;
- podem colidir múltiplas vezes em ticks diferentes;
- podem ou não ter massa;
- sem massa, não empurram;
- mesmo sem massa, ainda têm comportamento de colisão: sumir, ricochetear, atravessar etc.;
- normalmente não precisam de `Verifica()` própria;
- depois de criados, têm vida própria mesmo que o Pokémon de origem morra depois.

### 10.7. Construtos

Construtos:

- são objetos de batalha;
- podem ou não ter vida;
- podem ou não ter massa;
- podem ou não colidir com tudo;
- podem ter regras irregulares próprias de colisão;
- não necessariamente geram impulso só por terem colisor;
- podem possuir `Verifica()`;
- podem agir por tick;
- dependem de configuração.

### 10.8. Laser
Laser **não** é tratado como objeto de batalha persistente independente da mesma forma que projétil.

Ele é melhor lido como uma **ação contínua que calcula a faixa a cada tick**.

Ou seja:

- pode ter classe própria;
- mas essa classe é filha de **Ação**, não da hierarquia de **Objeto de Batalha**.

### 10.9. Criação de objetos durante o turno

Objetos podem ser criados no meio do turno.

Exemplo clássico: um ataque cria um projétil que vem com ação interna de movimento.

Mas a regra é:

- objeto criado em um tick **não age no mesmo tick**;
- deve haver pelo menos **1 tick de intervalo** antes de começar a agir;
- exceção: se o objeto já nascer colidindo com algo no próprio tick da criação, essa colisão é resolvida imediatamente naquele tick.

## 11. FÍSICA E COLISÕES

### 11.1. Potência física
**Fórmula-base da potência física:**

```text
potencia = (Peso / 10) * velocidade_real
```

A velocidade real oficial aqui deve ser lida como **velocidade de movimento**.

Ou seja, a implementação deve pensar assim:

```text
velocidade_de_movimento = velocidade usada para o deslocamento naquele tick
potencia = (Peso / 10) * velocidade_de_movimento
```

A conversão para `tiles_por_tick` continua existindo para deslocamento espacial, mas a potência física usa a velocidade de movimento como referência interna de impacto.

Projétil com massa usa a mesma lógica de potência física.

### 11.2. Dano de colisão

Pokémon colidindo com Pokémon normalmente causa dano.

Dano de colisão:

- é sem tipo elemental;
- bate em **Def**;
- não pode critar.

Leitura atual oficial:

```text
potencia_a = (Peso_a / 10) * velocidade_de_movimento_a
potencia_b = (Peso_b / 10) * velocidade_de_movimento_b

impacto = potencia_a + potencia_b

dano_a_em_b = impacto * 0.10 + Atk_a * 0.06
dano_b_em_a = impacto * 0.10 + Atk_b * 0.06
```

Ou seja:

- a colisão usa um componente físico compartilhado de impacto;
- cada lado ainda acrescenta uma parcela própria baseada em Atk;
- Amp e Dur entram normalmente para cada atacante/alvo respectivo depois disso.

### 11.3. Fórmula final de transferência de vetor

Quando uma colisão gerar deslocamento físico, o resultado não continua como movimento com alvo. Ele vira **impulso pós-colisão**.

Na colisão entre A e B, usar primeiro a massa efetiva:

```text
m = max(1, Peso / 10)
```

Depois, construir a base vetorial da colisão:

```text
n = vetor normal da colisão, do centro de A para o centro de B
t = vetor tangencial perpendicular a n
vA, vB = vetores de velocidade atuais

uA_n = dot(vA, n)
uB_n = dot(vB, n)

uA_t = dot(vA, t)
uB_t = dot(vB, t)
```

A componente normal usa impulso com coeficiente de restituição:

```text
j = -(1 + e) * (uA_n - uB_n) / ((1 / mA) + (1 / mB))

vA_n' = uA_n - j / mA
vB_n' = uB_n + j / mB
```

No motor, também vale a regra de deduplicação por tick:

- se o sistema encontrar a mesma colisão do mesmo par de objetos no mesmo tick;
- o par já processado naquele tick não pode ser resolvido de novo naquele mesmo tick.

### 11.4. Componente tangencial e regra de dominância

A componente tangencial não usa física completa; ela é preservada parcialmente por um fator `f_t`:

```text
vA_t' = uA_t * f_t
vB_t' = uB_t * f_t
```

Valores base de `f_t`:

- normal: `0.85`
- tile Gelado: `0.95`
- tile Destruído: `0.70`

Depois, reconstruir o vetor físico resultante:

```text
vA_fisico = n * vA_n' + t * vA_t'
vB_fisico = n * vB_n' + t * vB_t'
```

Em seguida, comparar as potências da colisão.

#### 11.4.1. Potências próximas

Se:

```text
pot_menor >= 0.70 * pot_maior
```

ambos usam o vetor físico completo:

```text
v_final = v_fisico
```

#### 11.4.2. Dominância clara / atropelamento

Se:

```text
pot_menor < 0.70 * pot_maior
```

o mais forte preserva mais da rota original, e o mais fraco recebe a maior parte da transferência.

Usar:

```text
dominancia = clamp((pot_maior / max(1, pot_menor) - 1.3) / 2.0, 0, 1)
perda_minima = 0.82 + 0.18 * (1 - e)
```

Para o objeto mais forte:

```text
v_forte_final = mistura_linear(v_fisico_forte, v_original_forte * perda_minima, dominancia)
```

Para o mais fraco:

```text
v_fraco_final = v_fisico_fraco
```

### 11.5. Objeto fixo, parede e coeficiente de restituição

Contra objeto fixo, usar reflexão no eixo normal:

```text
v_n' = -e * u_n
v_t' = f_t * u_t
```

Depois reconstruir o vetor final com `n` e `t`.

Coeficientes de restituição base:

- Pokémon vs Pokémon: `e = 0.20`
- Pokémon vs parede: `e = 0.35`
- Dash vs parede: `e = 0.45`
- Impulso vs parede: `e = 0.55`

Parede da arena continua sendo objeto fixo. Ao bater nela, o objeto pode tomar dano de colisão e ter seu vetor resolvido por essa leitura de reflexão + restituição.

### 11.6. Pós-colisão sempre vira impulso

Todo deslocamento gerado pela colisão vira **impulso pós-colisão**.

Leitura operacional:

```text
velocidade_de_movimento = magnitude(v_final)
tiles_por_tick = velocidade_de_movimento / 400
```

A cada tick:

```text
velocidade_de_movimento = max(0, velocidade_de_movimento - desaceleracao_por_tick)
desaceleracao_por_tick = clamp(coeficiente_de_atrito * Peso, 5, 40)
```

Quando `velocidade_de_movimento` chega a 0, o impulso acaba.

Leitura final da mecânica:

- a colisão resolve primeiro o vetor físico base;
- se as potências forem próximas, ambos usam o resultado físico completo;
- se houver dominância clara, o mais forte preserva mais da rota original;
- colisão com fixo usa reflexão;
- todo deslocamento gerado pela colisão vira impulso pós-colisão.

### 11.7. Efeito Imparável na colisão

O efeito **Imparável** impede impulsos vindos de outros por colisão.

Isso significa que, em colisões onde normalmente haveria transferência relevante de vetor, um alvo com Imparável pode ignorar esse empurrão/impulso recebido.

### 11.8. Projéteis com massa

Projétil com massa pode empurrar Pokémon usando a mesma lógica de potência física.

Isso não interfere no dano próprio do projétil.

Projétil sem massa não empurra, mas ainda pode:

- sumir;
- ricochetear;
- atravessar;
- disparar execute especial.

### 11.9. Projétil vs projétil

Projéteis podem colidir entre si. O comportamento depende das propriedades técnicas:

- destruir;
- atravessar;
- ricochetear;
- ambos atravessarem;
- um destruir o outro;
- gerar execute especial.

Projétil com massa também pode, se configurado, empurrar outro projétil.

### 11.10. Construtos e colisão

Construtos têm colisor, mas não necessariamente geram impulso ou de fato colidem com tudo.  
São mais irregulares e dependem da configuração.

### 11.11. Ricochete e atravessar

Ricochete e atravessar devem ser configuráveis separadamente para:

- Pokémon;
- projéteis;
- construtos;
- parede.

Os limites de ricochetes e atravessadas também devem ser separados por tipo de colisão.

---

## 12. CÁLCULO DE DANO

### 12.1. Separação causar dano vs tomar dano

O sistema deve separar:

- `causar_dano`: existe atacante/origem e pode ativar passivas do atacante;
- `tomar_dano`: sempre que algo recebe dano, com ou sem atacante.

Efeitos, colisões, clima e arena podem causar dano sem atacante direto.

### 12.2. Ordem-base do dano

Ordem-base recomendada:

1. dano bruto: `fonte * multiplicador`
2. multiplicadores condicionais do ataque/execute
3. STAB
4. crítico
5. multiplicador de tipo
6. amplificação do atacante
7. passivas/executes de dano causado
8. perfuração
9. modificadores condicionais/passivos de defesa
10. fórmula de defesa estilo LoL
11. `Protegido`
12. `Evasivo`
13. `Refletindo`
14. redução de dano
15. durabilidade do alvo
16. barreira
17. vida
18. `Imortal`
19. passivas pós-dano e vampirismo

Essa ordem é a base.  
Multiplicadores condicionais e passivas podem entrar em outros pontos se o ataque/passiva exigir isso.

### 12.3. STAB

Se o tipo do ataque for tipo do Pokémon atacante:

```text
dano * 1.20
```

### 12.4. Crítico
Crítico rola **por alvo**, e não mais uma única vez para o ataque inteiro, salvo regra especial futura.

### 12.5. Defesa estilo LoL

Para defesa positiva:

```text
dano_pos_defesa = dano * 100 / (100 + defesa)
```

Para defesa negativa:

```text
dano_pos_defesa = dano * (2 - 100 / (100 - defesa_negativa))
```

### 12.6. Perfuração
Perfuração oficial:

```text
defesa_reduzida = defesa - (Per / 2)
```

Regra fechada importante:

- se a defesa original estiver **positiva**, a perfuração pode reduzi-la;
- se a defesa original já estiver **negativa**, a perfuração não mexe nela;
- defesa positiva reduzida por perfuração não pode ficar abaixo de 0.

### 12.7. Tipo de dano

Tipos de dano:

- normal/físico: usa Def;
- especial: usa SpD;
- verdadeiro: ignora defesa.

Dano verdadeiro:

- ignora defesa;
- não usa perfuração;
- ainda pode passar por Amp;
- ainda pode critar;
- ainda ativa Vamp;
- ainda pode passar por Dur, barreira e vida, salvo regra especial.

### 12.8. Barreira no dano
Barreira é aplicada depois de Durabilidade.

Se `BarreiraAtual > 0` antes da instância, ela absorve a instância inteira antes de chegar na vida, mesmo que o dano seja maior que a barreira.

Essa barreira tem leitura explícita de **escudo de instância**.

Importante:

- dano bloqueado por barreira ainda conta como instância de dano sofrida para sistemas que verificam “recebeu dano”;
- porém esse dano bloqueado não gera Vamp por padrão, porque não removeu `VidaAtual`.

### 12.9. Vampirismo

Vamp cura com base apenas no dano que realmente tirou `VidaAtual`, não no dano bloqueado por barreira.

### 12.10. Multiplicador de tipo

O multiplicador de tipo vem antes da defesa.

Se o alvo tiver dois tipos:

```text
mod_total = mod_tipo_1 * mod_tipo_2
```

A tabela atual de FR continua como fonte inicial de fraquezas/resistências.

---

## 13. CURA E BARREIRA

### 13.1. Cura

Cura é mais direta que dano.  
Não passa por defesa.

A fonte da cura depende do ataque, item, efeito, passiva ou execute.

Exemplos possíveis:

- 30% de Mag;
- 20% da vida perdida;
- valor fixo;
- percentual do dano causado.

Cura pode ser modificada por:

- flags;
- efeitos;
- clima;
- tile;
- passivas.

Cura não usa Amp por padrão.  
Cura não crita por padrão.

### 13.2. Barreira

Barreira depende do que ativa ela.  
Não usa um atributo padrão obrigatório.

Pode vir de:

- Mag;
- Vida;
- valor fixo;
- execute;
- passiva.

Barreira:

- não tem máximo;
- não expira por padrão;
- é afetada por Dur no sentido de que Dur reduz o dano antes da barreira;
- não conta como vida para execução por porcentagem de vida;
- segura pelo menos uma instância inteira de dano se existir antes do dano.

---

## 14. EFEITOS

### 14.1. Estrutura geral

O jogo possui **36 efeitos principais**:

- 18 negativos;
- 18 positivos.

Clima e efeitos de tile da arena são sistemas separados, paralelos aos 36 efeitos, e não entram nessa lista principal.

Cada efeito deve ter:

- nome;
- código;
- positivo/negativo;
- duração base em ticks;
- descrição mecânica;
- regras de aplicação;
- regras por tick, se houver;
- flags ativadas;
- modificadores temporários;
- regras de expiração.

### 14.2. Fórmula de duração

Aplicação de efeito positivo em si mesmo:

```text
duracao = Base + Mag_origem
```

Aplicação de efeito positivo em aliado:

```text
duracao = Base + Mag_origem
```

Aplicação de efeito negativo em si mesmo:

```text
duracao = Base
```

Aplicação de efeito negativo em outro Pokémon:

```text
duracao = Base + Mag_origem - Mag_alvo
```

Duração mínima:

```text
duracao_minima = Base * 0.5
```

Arredondamento:

```text
round()
```

### 14.3. Stacks
Efeitos podem acumular stack.  
Ao aplicar o mesmo efeito novamente, a duração soma.

A duração total de um mesmo efeito não pode passar de:

```text
500 ticks
```

Efeitos incompatíveis podem coexistir, salvo regra futura específica.

### 14.4. Expiração
Efeitos perdem duração depois de aplicar seu comportamento daquele tick.

A duração pode ser fracionada internamente.

Exemplo conceitual:

```text
4.5 ticks restantes
```

Na prática, isso ainda significa que o efeito ainda terá mais uma aplicação relevante antes de expirar.

Leitura operacional atual:

- a duração interna pode ser decimal;
- o motor continua gastando esse valor conforme clima/tile/efeitos;
- o efeito só é considerado expirado quando o contador terminar de fato após sua aplicação relevante.

### 14.5. Cancelamentos por efeito

Efeitos podem cancelar ações:

- Dormindo: não pode agir; removido após sofrer ataque.
- Congelado: não pode agir.
- Paralisado: não pode preparar/executar ataques.
- Recuo: não pode executar ataques já preparados.
- Enraizado: não pode se mover.
- Protegido: não pode ser atacado.

Projéteis já lançados têm vida própria e não são cancelados se o Pokémon depois ficar impedido de atacar.

### 14.6. Velocidade de passagem dos efeitos

Clima e tile podem alterar a velocidade com que um efeito perde duração.

Modelo fechado:

- “passa 2x mais rápido” = gasta **2 ticks de duração por tick**
- “passa 2x mais lento” = gasta **0.5 tick de duração por tick**
- em alguns casos isso pode zerar o efeito quase imediatamente
- quando o tile “segura” um efeito, ele **impede a redução** do contador, mas não remove o efeito do Pokémon
- se o efeito já estava ativo antes do tile, entrar no tile pode somar duração e ao mesmo tempo segurar a redução

---

## 15. TABELA OFICIAL DE EFEITOS

### 15.1. Efeitos negativos

**Code 1 — Queimado**  
Duração base: 60 ticks.  
Efeito: perde 1% da vida a cada 10 ticks e recebe 35% menos cura.  
Flags/modificadores: dano periódico; multiplicador de cura recebida = 0.65.

**Code 2 — Dormindo**  
Duração base: 120 ticks.  
Efeito: não pode agir. O efeito é removido após sofrer um ataque.  
Flags/modificadores: `pode_agir = false`; `pode_atacar = false`; `pode_mover = false`.

**Code 3 — Envenenado**  
Duração base: 60 ticks.  
Efeito: perde 2% da vida a cada 10 ticks.  
Flags/modificadores: dano periódico.

**Code 4 — Intoxicado**  
Duração base: 60 ticks.  
Efeito: perde 3% da vida a cada 10 ticks e, a cada 20 ticks, libera gás ao redor de si.  
O gás tem alcance igual a duas vezes o próprio raio e faz aliados no alcance perderem 2% da vida.  
Flags/modificadores: dano periódico no próprio Pokémon; pulso em área contra aliados.

**Code 5 — Paralisado**  
Duração base: 60 ticks.  
Efeito: não pode preparar/executar ataques.  
Flags/modificadores: `pode_atacar = false`.

**Code 6 — Vampirico**  
Duração base: 60 ticks.  
Efeito: inimigos que atacarem este Pokémon curam 25% do dano efetivo causado a ele.  
Diretriz: usar dano que tirou vida como referência principal.

**Code 7 — Encharcado**  
Duração base: 60 ticks.  
Efeito: ataques gastam 20% mais energia e o Pokémon se move 20% mais devagar.  
Flags/modificadores: `custo_energia *= 1.20`; `velocidade_movimento *= 0.80`.

**Code 8 — Quebrado**  
Duração base: 60 ticks.  
Efeito: recebe 50% menos durabilidade.  
Flags/modificadores: Dur efetiva reduzida em 50%.

**Code 9 — Enfraquecido**  
Duração base: 60 ticks.  
Efeito: recebe 50% menos amplificação.  
Flags/modificadores: Amp efetiva reduzida em 50%.

**Code 10 — Confuso**  
Duração base: 60 ticks.  
Efeito: recebe 50% menos assertividade.  
Flags/modificadores: `Assertividade *= 0.50`.

**Code 11 — Congelado**  
Duração base: 60 ticks.  
Efeito: não pode agir, mas recebe 30% menos dano.  
Flags/modificadores: `pode_agir = false`; `pode_atacar = false`; `pode_mover = false`; `dano_recebido *= 0.70`.

**Code 12 — Atordoado**  
Duração base: 60 ticks.  
Efeito: não pode usar passivas de itens ou habilidades.  
Flags/modificadores: passivas de item e habilidade desativadas.

**Code 13 — Cauterizado**  
Duração base: 60 ticks.  
Efeito: não pode causar acertos críticos.  
Flags/modificadores: `critico_bloqueado = true`.

**Code 14 — Descarregado**  
Duração base: 60 ticks.  
Efeito: recupera 50% menos energia.  
Flags/modificadores: `energia_ganho *= 0.50`.

**Code 15 — Bloqueado**  
Duração base: 60 ticks.  
Efeito: não pode receber efeitos positivos.  
Flags/modificadores: `bloqueia_efeito_positivo = true`.

**Code 16 — Amaldiçoado**  
Duração base: 60 ticks.  
Efeito: efeitos negativos aplicados duram 50% mais tempo.  
Flags/modificadores: ao receber efeito negativo, `duracao *= 1.50`.

**Code 17 — Recuo**  
Duração base: 20 ticks.  
Efeito: não pode executar ataques já preparados.  
Flags/modificadores: cancela/bloqueia ataques que ainda não ativaram. Não cancela projéteis já criados.

**Code 18 — Enraizado**  
Duração base: 60 ticks.  
Efeito: não pode se mover.  
Flags/modificadores: `pode_mover = false`.

### 15.2. Efeitos positivos

**Code 19 — Regeneração**  
Duração base: 60 ticks.  
Efeito: cura 5% da vida perdida a cada 10 ticks.  
Flags/modificadores: cura periódica baseada em `VidaMax - VidaAtual`.

**Code 20 — Abençoado**  
Duração base: 60 ticks.  
Efeito: cura 3% da vida perdida a cada 10 ticks e recebe 35% mais cura de qualquer fonte.  
Flags/modificadores: cura periódica; `cura_recebida *= 1.35`.

**Code 21 — Imortal**  
Duração base: 60 ticks.  
Efeito: não pode ser morto. O efeito é removido após sofrer dano mortal.  
Diretriz: dano mortal deixa o Pokémon vivo com pelo menos 1 de vida e consome Imortal.

**Code 22 — Fortificado**  
Duração base: 60 ticks.  
Efeito: recebe 50% mais durabilidade.  
Flags/modificadores: Dur efetiva aumenta 50%.

**Code 23 — Amplificado**  
Duração base: 60 ticks.  
Efeito: recebe 50% mais amplificação.  
Flags/modificadores: Amp efetiva aumenta 50%.

**Code 24 — Voando**  
Duração base: 60 ticks.  
Efeito: reduz a `Assertividade` efetiva do Pokémon para 50.  
Flags/modificadores: contra este alvo, a checagem de acerto usa `Assertividade = 50`, salvo exceções específicas.

**Code 25 — Flutuando**  
Duração base: 60 ticks.  
Efeito: contra ataques normais, a `Assertividade` efetiva deste Pokémon é reduzida para 50.  
Flags/modificadores: ataques normais contra esse Pokémon usam `Assertividade = 50`.

**Code 26 — Imune**  
Duração base: 60 ticks.  
Efeito: não pode receber efeitos negativos.  
Flags/modificadores: `imune_efeito_negativo = true`.

**Code 27 — Energizado**  
Duração base: 60 ticks.  
Efeito: recupera 50% mais energia e não possui limite de energia.  
Flags/modificadores: `energia_ganho *= 1.50`; ignorar limite de EneM enquanto ativo.

**Code 28 — Preparado**  
Duração base: 60 ticks.  
Efeito: recebe apenas 40% do dano e devolve dano equivalente a 40% da velocidade.  
Flags/modificadores: `dano_recebido *= 0.40`; ao sofrer dano, devolve dano baseado em Vel.

**Code 29 — Provocando**  
Duração base: 60 ticks.  
Efeito: em ataques de alvo, entre os inimigos em alcance, se existir um ou mais Pokémon provocando, o ataque só pode mirar em Pokémon com Provocando. Além disso, ganha `+3 Esc`.  
Flags/modificadores: restringe a seleção de alvo de ataques de alvo ao conjunto de provocadores válidos em alcance; `Esc += 3`.

**Code 30 — Furtivo**  
Duração base: 60 ticks.  
Efeito: bloqueia apenas a seleção de target por ataques de alvo, tem `-1 Esc` e também não deve ficar visível para o oponente no client.  
Flags/modificadores: bloqueia apenas a mira/seleção normal de ataques de alvo; `Esc -= 1`; ocultação visual no client inimigo.

**Code 31 — Encantado**  
Duração base: 60 ticks.  
Efeito: efeitos positivos duram 50% mais tempo.  
Flags/modificadores: ao receber efeito positivo, `duracao *= 1.50`.

**Code 32 — Refletindo**  
Duração base: 60 ticks.  
Efeito: ao sofrer dano com atacante definido, recebe apenas 25% dele e devolve os outros 75% à origem. Depois de refletir, o efeito é consumido.  
Flags/modificadores: `dano_recebido_da_instancia *= 0.25`; refletir 75% na origem quando houver; consumir o efeito após refletir.

**Code 33 — Evasivo**  
Duração base: 60 ticks.  
Efeito: desvia do próximo dano recebido.  
Flags/modificadores: consome o efeito ao evitar uma instância de dano.

**Code 34 — Focado**  
Duração base: 60 ticks.  
Efeito: define `Acuracia = 200`.  
Flags/modificadores: aumenta a checagem de acerto; ainda não vence bloqueios absolutos como `Protegido`.

**Code 35 — Protegido**  
Duração base: 20 ticks.  
Efeito: anula qualquer execute de ataque contra este Pokémon. Não anula ricochetes nem explosões cuja resolução dependa das propriedades iniciais do projétil, e não do execute principal.  
Flags/modificadores: executa um bloqueio absoluto de execute de ataque contra o alvo protegido, sem impedir efeitos físicos/colaterais independentes do execute principal.

**Code 36 — Imparavel**  
Duração base: 60 ticks.  
Efeito: não pode recuar nem ser movido por ataques ou colisões que gerariam impulso externo.  
Flags/modificadores: imune a empurrões/recuos/deslocamentos forçados por ataque ou colisão externa; não cancela movimento voluntário próprio.

### 15.3. Nomes legados a substituir ou revisar

O modelo antigo possui nomes que não batem exatamente com a nova tabela:

- Incapacitado
- Fragilizado
- Neutralizado
- Enfeitiçado
- Reforçado
- Aprimorado
- Ilimitado
- Refletido

Esses nomes devem ser removidos, migrados ou mapeados para os novos efeitos apenas se houver decisão explícita.

---

## 16. ARENA

### 16.1. Estrutura da arena
A arena é composta por tiles.

O tamanho da arena é variável, porém o padrão atual é:

```text
40 x 20 tiles
```

Ou seja, por padrão, a arena possui 800 tiles em um retângulo.

Cada tile possui posição fixa de grid, por exemplo:

```text
(1,1), (1,2), (1,3) ...
```

Os tiles têm posição fixa porque eles **são a própria grid**.

A visualização atual desejada para o jogador continua usando a leitura em `(1,1)` como canto inicial, mesmo que a implementação interna futuramente precise converter isso.

### 16.2. Efeito de tile

Cada tile pode ser:

- regular;
- ou possuir um efeito de tile.

Um tile **não** acumula múltiplos efeitos ao mesmo tempo.  
Se um novo efeito entra naquele tile, ele substitui o efeito anterior.

Os efeitos de tile pertencem ao **tile**, não ao Pokémon.  
O Pokémon apenas sofre as consequências enquanto estiver naquele tile.

### 16.3. Persistência

Os efeitos de tile permanecem na arena entre turnos.

O tamanho da arena ainda não muda durante a batalha neste modelo.

Ataques futuramente poderão criar **efeitos de tile**.

### 16.4. HUD

Efeitos de tile aparecem no HUD como cor do chão/indicador do tile.

Regras visuais já definidas:

- Incendiado: cor animada
- Contaminado: cor animada
- Abençoado: cor animada

### 16.5. Momento da checagem
A aplicação do efeito de tile é avaliada a partir da posição atual do Pokémon, normalmente durante a `Verifica()` no fim do tick.

Quando o sistema perguntar se o Pokémon está num tile de efeito, usa-se a posição real atual e converte-se para o tile correspondente.

Exemplo conceitual:

```text
posicao = (23.45803, 12.342445)
tile avaliado = (23, 12)
```

Se o Pokémon começa o tick já dentro do tile, isso conta normalmente.

Se o Pokémon atravessa vários tiles no mesmo tick, conta o tile em que ele estava no momento relevante da checagem.

Para distinguir **ao entrar no tile** e **já está no tile**, o Pokémon deve guardar a última posição/tile relevante usado na checagem.

### 16.6. Saída do tile
Os efeitos do tile não “ficam no tile dentro do Pokémon”.

O que permanece ou some ao sair depende da natureza da consequência:

- consequências locais/atributivas, como lentidão da Lama, saem imediatamente ao sair do tile;
- efeitos de status realmente aplicados ao Pokémon, como Queimado ou Envenenado, continuam no Pokémon conforme suas regras normais;
- em tiles que “seguram” a redução do contador, sair do tile faz o contador voltar a passar normalmente.

No modelo atual, não existe um gatilho especial de **efeito ao sair do tile**.

### 16.7. Interações com imunidade e bloqueio

Se o tile tentar **aplicar um efeito** ao Pokémon, o sistema de imunidade ou bloqueio do próprio Pokémon continua valendo.

Exemplos:

- `Imune` impede que um tile aplique efeito negativo ao Pokémon.
- `Bloqueado` impede receber efeitos positivos aplicados ao Pokémon.

Mas isso não anula automaticamente passivas do tile que não sejam “aplicar um efeito no Pokémon”.  
Ou seja, o tile pode continuar alterando velocidade final, cura, atrito etc. se essa consequência for da natureza do tile e não da aplicação formal de um efeito.

### 16.8. Tile Incendiado

Tile Incendiado:

- quem está nele ganha **Queimado por 30 ticks**;
- durante a permanência no tile, o efeito Queimado **não perde duração**;
- se o Pokémon já estiver Queimado ao entrar, a duração soma e o contador fica segurado enquanto ele permanecer ali;
- em clima de Chuva, tiles Incendiados ficam normais enquanto esse clima durar.

### 16.9. Tile Contaminado

Tile Contaminado:

- quem está nele ganha **Envenenado por 30 ticks**;
- durante a permanência no tile, o efeito Envenenado **não perde duração**;
- Intoxicado não é removido por isso; as regras coexistem;
- se o Pokémon já estiver com efeito relacionado, a duração soma e o contador fica segurado enquanto ele permanecer ali.

### 16.10. Tile Gelado

Tile Gelado:

- o efeito Congelado não perde duração enquanto o Pokémon permanecer no tile;
- quem passa por ele desliza;
- ao se mover, a posição alvo deixa de ser parada obrigatória;
- ao alcançar o alvo planejado, o Pokémon continua se movendo até desacelerar completamente;
- reduz a desaceleração;
- impulso sobre gelo também sofre essa redução de desaceleração;
- em clima de Sol Forte, tiles Gelados ficam normais enquanto esse clima durar.

Se um Pokémon congelado ficar num tile Gelado, ele pode continuar com o contador travado indefinidamente enquanto permanecer lá.

### 16.11. Tile Lama

Tile Lama:

- o Pokémon se move **50% mais lento** por qualquer motivo enquanto estiver lá;
- isso altera o `tiles_por_tick` final.

### 16.12. Tile Energizado

Tile Energizado:

- ao ficar nele, o Pokémon recupera **50% a mais de energia** normalmente;
- ao se mover nele, move-se **25% mais rápido**;
- os bônus do tile não são o mesmo efeito que o status Energizado do Pokémon; são sistemas paralelos.

### 16.13. Tile Destruído

Tile Destruído:

- quem está nele recebe **menos 50 de Durabilidade** efetiva;
- na prática, toma mais dano por ter menos Dur;
- também se move **25% mais lento**;
- o tile possui atrito maior que o normal.

### 16.14. Tile Abençoado

Tile Abençoado:

- efeitos positivos duram **25% a mais**;
- curas são **50% maiores**;
- esse alongamento de duração vale para efeitos positivos aplicados enquanto o Pokémon estiver no tile.

### 16.15. Projéteis e tiles

Projéteis **não** são afetados por tiles neste modelo.

### 16.16. Troca e tile
Pokémon que entra por troca já deve ser avaliado normalmente no tile em que aparecer.  
Se entrar em tile de efeito, pode receber suas consequências imediatamente conforme a regra do tile.

Como a troca coloca o novo Pokémon na posição final do anterior, a leitura de tile continua sendo feita nessa mesma posição final.

### 16.17. Tiles não são destruíveis neste modelo

Não existe destruição física de tile neste modelo.  
O que pode existir é criação, troca ou remoção de **efeito de tile**.

---

## 17. CLIMA

### 17.1. Estrutura geral

Só pode existir **um clima por vez** e ele afeta o jogo inteiro.

Clima é um sistema paralelo aos efeitos e paralelo aos efeitos de tile.

### 17.2. Mudança de clima

Clima pode mudar **no meio do turno**.  
Ele pode ser substituído instantaneamente por outro clima.

### 17.3. Duração e saída do clima
O clima atual tem **25% de chance de sair ao final de cada turno**.

Exceção fechada:

- se o clima foi criado ou substituído durante o turno atual, ele **não** rola essa chance de saída no final desse mesmo turno.

### 17.4. Relação com efeitos

Quando o clima altera a velocidade de duração de um efeito:

- “2x mais rápido” = gasta 2 ticks de duração por tick
- “2x mais lento” = gasta 0.5 tick de duração por tick

Em regra geral, o clima altera essa passagem **antes** do gasto natural do efeito naquele tick.

### 17.5. Relação com imunidade e proteção

Clima:

- ignora `Protegido`;
- não ignora `Imune` quando o que ele estiver fazendo for aplicar efeito negativo ao Pokémon.

### 17.6. Sol Forte

Sol Forte:

- Congelado e Encharcado passam 2 vezes mais rápido;
- Pokémon de gelo ficam com **-20 Durabilidade**;
- ataques de fogo dão **25% a mais de dano**;
- ataques de água dão **25% a menos de dano**;
- tiles Gelados ficam normais.

### 17.7. Chuva

Chuva:

- Queimado passa 2 vezes mais rápido;
- Encharcado demora 2 vezes mais para passar;
- ataques de fogo dão **25% a menos de dano**;
- ataques de água dão **25% a mais de dano**;
- tiles Incendiados ficam normais.

### 17.8. Nevasca

Nevasca:

- Congelado passa 2 vezes mais lento;
- Pokémon de gelo têm **+20 Durabilidade**;
- Pokémon Encharcados têm **3% de chance por tick** de terem o efeito Encharcado trocado para Congelado;
- essa troca é checada depois no tick e ocorre continuamente enquanto as condições forem válidas.

### 17.9. Chuva Ácida

Chuva Ácida:

- todos os Pokémon perdem **1% de ambas as defesas a cada 10 ticks**;
- essa perda é **permanente**;
- Pokémon do tipo Venenoso:
  - não sofrem essa perda;
  - curam **3% da vida perdida a cada 10 ticks**.

### 17.10. Tempestade de Areia

Tempestade de Areia:

- todos os Pokémon que não são dos tipos **Metal, Terrestre ou Pedra** tomam **2% da vida** como dano físico/normal a cada 10 ticks;
- esse dano usa **Def**;
- Pokémon Terrestres têm **20% mais velocidade**.

### 17.11. Tipagem e clima

Os tipos dos Pokémon são fixos em regra geral, mas futuramente poderão ser alterados por passiva ou execute de ataque.

Se isso ocorrer, o clima deve recalcular imediatamente suas interações com o novo tipo.

---

## 18. ATAQUES

### 18.1. Estrutura conceitual

Cada ataque deve possuir dados técnicos suficientes para ser executado sem ler a descrição.

Esses dados vivem no JSON de **PropriedadesAtaque**.

Campos conceituais mínimos:

- id técnico do ataque;
- code textual opcional;
- nome;
- tipo elemental;
- estilo;
- custo;
- intervalo de ativação em ticks;
- multiplicador de dano;
- STAB aplicável ou não;
- pode critar ou não;
- dados de alvo/alcance;
- dados físicos do estilo;
- condições;
- propriedades de colisão;
- propriedades de ricochete;
- propriedades de atravessar;
- comportamento de fim por tipo de colisão quando o estilo usar projétil;
- gif/efeito visual do ataque sobre o alvo, quando necessário;
- imagem de projétil, quando necessário.

O contrato base de **PropriedadesAtaque** deve carregar, quando couber:

- execute principal;
- execute de estado;
- executes periféricos.

Flags internas do fluxo de execução não precisam viver nesse contrato base. O construtor, a classe do estilo e os dispatchers continuam responsáveis por ligar esses executes ao fluxo real da ação.

### 18.2. CSV e JSON

O CSV pode manter:

- nome;
- tipo;
- custo;
- estilo;
- intervalo;
- descrição humana.

O JSON técnico se chama **PropriedadesAtaque** e define as propriedades que entram no construtor da ação real.

Os executes do ataque devem aparecer no JSON técnico quando existirem, usando campos explícitos para principal, estado e periféricos.
As flags internas do fluxo continuam fora desse contrato base; o construtor e o sistema de execução usam os nomes declarados no JSON para acoplar o comportamento real do ataque.

### 18.3. Irregular

Ataque irregular exige classe/caso próprio.  
Ainda assim, quando possível, deve usar o mesmo sistema de dados, executes, logs e métodos.

---

## 19. ESTILOS DE ATAQUE

### 19.1. Alvo
Ataque de alvo:

- exige clicar em alvo válido;
- pode limitar alvo para inimigo, aliado, ambos, si mesmo, reserva ou outros grupos;
- usa alcance circular simples por enquanto;
- pode ter múltiplos alvos;
- se múltiplos alvos forem configurados, o jogador escolhe quando esse for o modo;
- seleção automática extra deve ser feita por execute;
- pode ter intervalo entre alvos;
- se o alvo sai do alcance antes da ativação, o ataque falha;
- se o alvo morre antes da ativação, o ataque falha.

Interações já fechadas:

- se existir um ou mais inimigos em alcance com **Provocando**, o ataque de alvo só pode mirar em um dos provocadores válidos;
- **Furtivo** impede que o Pokémon seja mirado normalmente por ataques de alvo.

### 19.2. Status

Status:

- normalmente é autouso;
- o jogador seleciona o ataque e clica no próprio Pokémon;
- esse clique não desseleciona o Pokémon;
- no pacote enviado ao servidor, o status não precisa carregar alvo explícito quando for autouso puro;
- pode ter intervalo de ativação;
- pode ser interrompido por Recuo ou outro efeito aplicável;
- embora o estilo seja autouso, executes podem afetar aliados ou inimigos.

### 19.3. Projétil
Projétil:

- sempre é fisicamente uma bola/círculo com raio;
- tem alcance total;
- tem velocidade fixa por padrão;
- pode ter aceleração/desaceleração;
- pode ter massa;
- massa permite empurrar;
- sem massa não empurra;
- pode causar dano, cura, efeito ou explodir em área;
- pode atravessar/ricochetear/destruir em colisões;
- tem propriedades separadas para Pokémon, projéteis e objetos;
- alcance restante continua após ricochete;
- o projétil pode, ao colidir com Pokémon, disparar o **execute principal** e ainda assim ter um **comportamento de fim** separado, como destruir, atravessar ou ricochetear;
- além do execute principal, o projétil também pode usar **execute de estado** para gerar ação derivada ou mudar seu próprio estado depois do impacto;
- ricochete e atravessar devem possuir dicionários/blocos próprios separados no dado técnico;
- pode acertar o mesmo Pokémon novamente se a trajetória permitir após ricochete/atravessar.

Se o projétil nascer já colidindo com algo no mesmo tick da criação, essa colisão vale imediatamente.  
Nesse caso, a resolução depende das propriedades do projétil:

- atravessa;
- destrói;
- ricocheteia;
- ou outro comportamento técnico configurado.

Múltiplos projéteis:

- número de projéteis configurável;
- angulatura configurável;
- se número ímpar, um projétil fica no centro;
- se número par, distribui simetricamente ao redor da mira;
- a angulatura deve representar a separação angular configurada no JSON técnico;
- pode existir intervalo de lançamento entre projéteis;
- a ação termina no último lançamento.

### 19.4. Área

Área:

- é instantânea após intervalo;
- acerta tudo que estiver na área no tick de ativação;
- cada alvo é atingido uma vez por ativação;
- não possui friendly fire por padrão;
- usa posição fantasma se houver ação anterior de movimento/dash preparada.

Modos já citados:

- cone: usa alcance e abertura em graus;
- irregular/trapézio técnico: usa base, teto e altura em tiles.

### 19.5. Zona

Zona:

- é uma área circular posicionada pelo jogador;
- tem raio;
- tem alcance máximo para escolher o centro;
- é instantânea após intervalo;
- não permanece por vários ticks neste modelo;
- não causa dano periódico neste modelo.

### 19.6. Laser

Laser:

- é uma faixa/corredor com alcance e grossura;
- tem velocidade de avanço;
- não tem aceleração/desaceleração por enquanto;
- acerta quando a faixa passa pelo alvo;
- não ricocheteia;
- não atravessa parede da arena;
- é barrado por paredes da arena;
- o log deve guardar porcentagem de avanço por tick.

### 19.7. Dash

Dash:

- é um movimento ofensivo/rápido, não um filho puro da hierarquia principal de ataque;
- pode ter alcance fixo ou configurável;
- quando configurável, possui mínimo e máximo;
- usa velocidade percentual do Pokémon;
- causa colisão física;
- carrega execute ofensivo acoplado na colisão;
- pode atropelar ou ser interrompido conforme diferença de peso/potência;
- pode atravessar Pokémon se configurado.

### 19.8. Impulso

Impulso:

- é um movimento desacelerado controlado pelo jogador, não um filho puro da hierarquia principal de ataque;
- intensidade depende da distância do mouse;
- tem velocidade mínima e máxima em percentual da Vel;
- tem desaceleração;
- ricocheteia em colisões;
- não é simplesmente cancelado por colisão;
- pode causar dano por colisão;
- carrega execute ofensivo acoplado na colisão.

### 19.9. Passivo
Passivo não é preparado.  
Ele reage a flags/métodos apropriados.

No modelo atual, passivo não precisa ter uma classe própria obrigatória.  
Em muitos casos ele pode viver como executes/passivas reagindo às flags corretas ao longo do percurso.

### 20.1. Preparação visual

Ao selecionar um ataque, o preview aparece imediatamente.

Ao clicar na tela/alvo conforme o estilo, a ação é preparada.

Depois de preparar, o ataque selecionado é desselecionado.

### 20.2. Indicadores visuais

Indicadores de preview devem ser brancos.  
Indicadores preparados ficam no chão, mais transparentes e sem animação leve.

Impulso é exceção visual:

- usa seta;
- grossura aumenta com intensidade;
- transparência diminui com intensidade.

### 20.3. Movimento por arrasto

Movimento normal é feito arrastando o Pokémon.  
Enquanto arrasta, aparece construto/fantasma.  
Ao soltar, prepara movimento.

### 20.4. Posição fantasma

Se o Pokémon já tem movimento/dash preparado, ataques seguintes usam o construto/fantasma como origem visual para preview.

Isso não garante que o servidor terá a mesma posição, pois colisões podem mudar o resultado.  
Mas o preview deve representar a intenção planejada.

Se apagar uma ação anterior, ações posteriores e seus previews precisam recalcular origem, custo e validade.

### 20.5. Alvo

Ataque de alvo mostra alcance ao redor do executor.  
Alvos permitidos dentro do alcance ficam piscando.  
Ao clicar em alvo válido, prepara a ação.

### 20.6. Status

Status é preparado clicando no próprio Pokémon depois de selecionar o ataque.  
Esse clique não desseleciona o Pokémon.

### 20.7. Painel de ações

Ações preparadas aparecem em painel no canto esquerdo.  
Cada ação tem botão X para apagar.  
A ordem exibida é a ordem de criação e define a ordem das ações do mesmo Pokémon.

### 20.8. Energia visual

A barra de energia da ficha deve mostrar quanto será gasto.  
Se o gasto passar da energia disponível, o indicador pisca em branco/vermelho e a ação não pode ser preparada.

### 20.9. Sem botão de preparar jogada

Não precisa existir botão separado de preparar jogada.  
Clicar/soltar conforme o estilo já prepara.

### 20.10. Botão de pronto

Quando o jogador pressiona pronto ou o tempo acaba, as ações são enviadas ao servidor em ordem.

---

## 21. IA E PVP

### 21.1. IA
Contra treinador/IA, neste início do projeto, a IA deve ficar no client e o client envia ao servidor as ações que a IA montar.

Arquiteturalmente, a IA deve ser tratada como uma camada separada do resto da batalha:

- ela recebe a partida/estado atual;
- processa sua lógica;
- retorna uma lista de jogadas.

A IA deve respeitar o mesmo sistema lógico de montagem:

- energia;
- alcance;
- limites por lado;
- limites por Pokémon;
- ações diferentes;
- posição fantasma/previsão quando couber.

No futuro, a ideia é poder espelhar ou portar essa IA também para o servidor sem destruir esse contrato.

### 21.2. PvP

Contra player real, cada client envia suas próprias ações.  
O servidor espera as ações dos lados ou usa ações vazias se o tempo acabar.

### 21.3. Servidor decide tudo

Mesmo quando IA ou player montam ações no client, o servidor decide a simulação real.  
Preview do client pode errar por colisões futuras; o resultado real vem do histórico e do diff final.

### 21.4. Envio do pacote para o client

O client só anima o turno **depois de receber o pacote final** do servidor.  
Não há streaming parcial como regra atual.

---

## 22. LOGS, HISTÓRICO E RESULTADOS

### 22.1. Estrutura geral

O servidor deve enviar duas partes principais por turno:

- histórico;
- resultados.

Além disso, deve existir um **log geral da partida**.

### 22.2. Histórico do turno

O histórico do turno é uma lista de registros.  
Cada registro tem tick local.

Só ticks com eventos precisam aparecer.  
Pode haver mais de um registro no mesmo tick.

Mesmo eventos simultâneos podem ter uma ordem interna registrada quando necessário.


#### IDs únicos de entidades e eventos

Tudo que for importante para animação, histórico, diff ou replay deve possuir ID.

Isso inclui, pelo menos:

- ação;
- evento;
- Pokémon de batalha;
- projétil;
- construto;
- parede quando necessário;
- partida;
- turno;
- ataque técnico.

Esses IDs devem continuar sendo **globalmente únicos dentro do universo relevante da partida**, mas agora com um esquema numérico em que o **primeiro dígito já identifica a classe do ID**.

Leitura atual fechada:

- **Pokémon de batalha:** sempre possuem **3 dígitos**, no formato `0LS`;
- no ID de Pokémon, o primeiro dígito é sempre `0`;
- o segundo dígito é o lado (`0` ou `1`);
- o terceiro dígito é o slot normal do lado (`0` a `5`);
- projétil começa com `1`;
- construto começa com `2`;
- parede começa com `3`;
- ação começa com `4`;
- evento começa com `5`;
- turno começa com `6`;
- ataque começa com `7`.

Para as classes que não sejam Pokémon, a leitura é:

- o primeiro dígito identifica o tipo;
- os dígitos seguintes representam a ordem/sequência numérica daquele tipo dentro da partida.

Exemplos conceituais:

- `000` = Pokémon do lado 0, slot 0;
- `015` = Pokémon do lado 1, slot 5;
- `1001` = projétil 1;
- `2004` = construto 4;
- `4012` = ação 12;
- `5033` = evento 33;
- `6007` = turno 7;
- `7005` = ataque técnico 5.

Assim, o sistema mantém identificação humana simples, evita colisão entre classes diferentes e continua adequado para replay, reconciliação visual e debug.

### 22.3. Eventos que devem existir

O histórico deve registrar, entre outros:

- início de ação;
- ativação de ataque;
- término de ação;
- cancelamento de ação;
- passivas ativadas;
- dano aplicado com passo a passo;
- cura;
- barreira;
- mutação de status;
- aplicação de efeito;
- expiração de efeito;
- aplicação e remoção de clima;
- aplicação e consulta de efeitos de tile quando relevante;
- colisões;
- criação de projétil/objeto;
- finalização de projétil/objeto;
- movimento iniciado;
- movimento finalizado;
- morte;
- troca;
- rolagens aleatórias/seed;
- timeout, se ocorrer.

### 22.4. Movimento no histórico

Movimento deve ter registro de início com lista completa de posições por tick.  
Depois deve ter registro de finalização, colisões ou interrupções quando ocorrerem.

### 22.5. Projétil no histórico

Projétil deve ser logado como:

- criação;
- lista completa de posições por tick;
- colisões;
- finalização.

### 22.6. Laser no histórico

Laser deve guardar lista de porcentagens/avanço por tick, não apenas posição final.

### 22.7. Dano no histórico

Dano deve ter passo a passo suficiente para debug e replay.

Campos conceituais importantes:

- dano bruto;
- fonte usada;
- multiplicador da fonte;
- condicionais aplicados;
- STAB;
- crítico;
- multiplicador de tipo;
- Amp;
- passivas/executes;
- defesa original;
- perfuração;
- defesa final;
- dano pós-defesa;
- Dur;
- dano pós-Dur;
- barreira antes;
- barreira depois;
- vida antes;
- vida depois;
- dano que tirou vida;
- dano absorvido;
- Vamp;
- morte;
- flags pós-dano.

### 22.8. Resultados/diff final do turno
Resultados devem conter diff final **apenas do que mudou de fato** no turno.

O diff não deve repetir blocos inteiros sem necessidade.
Se um atributo, estado ou campo não mudou, ele não precisa aparecer no resultado final daquele turno.

Inclui, no mínimo, quando houver mudança:

- vida;
- energia;
- barreira;
- posição;
- efeitos, sempre incluindo a **duração restante em ticks**;
- clima atual, se tiver mudado;
- estado dos tiles alterados, quando houver;
- atributos temporários/permanentes que realmente mudaram;
- vivos/mortos;
- ativos/reservas;
- objetos/projéteis que persistirem, surgirem ou sumirem;
- estado da partida;
- `tick_global` final;
- IDs relevantes para reconciliar entidades persistentes;
- qualquer outra mudança relevante em Pokémon e partida.

Exemplo conceitual importante: se `Assertividade` não mudou, ela não precisa aparecer no diff do turno.
Já um efeito como `Paralisado`, se estiver ativo ou alterado, deve aparecer com sua duração restante em ticks.

### 22.9. Log geral da partida

No fim da partida deve existir um **log geral da partida**, usando `TickGlobal`.

Esse log é:

- paralelo ao log do turno;
- composto/somado a partir dos turnos, mas mantido como estrutura própria.

### 22.10. RNG e replay

O log deve incluir seed/rolls aleatórios relevantes.  
O servidor manda o resultado real de qualquer rolagem.

---

## 23. ESQUEMAS DE REFERÊNCIA TÉCNICA

Este tópico consolida exemplos de esquema para os contratos principais da batalha nova.

A ideia aqui não é dizer que todo campo do exemplo é obrigatório em todo caso, e sim fixar uma **estrutura-base de referência** para evitar ambiguidade entre client, server, log, replay e diff.

### 23.1. Estrutura-base de `PropriedadesAtaque`

Leitura geral recomendada:

- um bloco comum no topo;
- subblocos específicos por estilo;
- bloco explícito de executes do ataque;
- flags internas do fluxo fora do JSON base.

#### 23.1.1. Núcleo comum

```json
{
  "id": 7001,
  "code": "thunder_punch",
  "nome": "Thunder Punch",
  "tipo": "Eletrico",
  "estilo": "alvo",
  "custo": 35,
  "intervalo": 5,
  "multiplicador_dano": 1.2,
  "pode_criticar": true,
  "aplica_stab": true,
  "executes": {
    "principal": "thunder_punch_principal",
    "estado": null,
    "perifericos": []
  },
  "condicoes": {
    "respeita_provocando": true,
    "respeita_furtivo": true,
    "falha_se_alvo_morrer": true,
    "falha_se_alvo_sair_do_alcance": true
  },
  "visual": {
    "preview": {
      "forma": "circulo_alvo"
    },
    "efeito_alvo": "Choque_01",
    "projetil_imagem": null
  }
}
```

#### 23.1.2. Ataque de alvo

Os exemplos seguintes podem omitir o bloco `executes` quando ele for apenas repetição mecânica do mesmo padrão do núcleo comum.

```json
{
  "id": 7001,
  "code": "thunder_punch",
  "nome": "Thunder Punch",
  "tipo": "Eletrico",
  "estilo": "alvo",
  "custo": 35,
  "intervalo": 5,
  "multiplicador_dano": 1.2,
  "pode_criticar": true,
  "aplica_stab": true,
  "alvo": {
    "grupos_permitidos": ["inimigo"],
    "alcance": 4.0,
    "max_alvos": 1,
    "intervalo_entre_alvos": 0
  },
  "condicoes": {
    "respeita_provocando": true,
    "respeita_furtivo": true,
    "falha_se_alvo_morrer": true,
    "falha_se_alvo_sair_do_alcance": true
  },
  "visual": {
    "preview": {
      "forma": "circulo_alvo"
    },
    "efeito_alvo": "Choque_01",
    "projetil_imagem": null
  }
}
```

#### 23.1.3. Ataque de status

Status autouso puro não precisa de bloco de alvo obrigatório.

```json
{
  "id": 7002,
  "code": "focus_energy",
  "nome": "Focus Energy",
  "tipo": "Normal",
  "estilo": "status",
  "custo": 25,
  "intervalo": 3,
  "multiplicador_dano": 0,
  "pode_criticar": false,
  "aplica_stab": false,
  "condicoes": {
    "autouso": true
  },
  "visual": {
    "preview": {
      "forma": "status_autouso"
    },
    "efeito_alvo": "Buff_01",
    "projetil_imagem": null
  }
}
```

#### 23.1.4. Projétil

No projétil, o comportamento de colisão com Pokémon deve separar:

- o que acontece de execução (`execute_principal` automático pelo sistema);
- o que acontece de fim/comportamento físico (`destruir`, `atravessar`, `ricochetear` etc.).

Ricochete e atravessar devem ficar em blocos separados.

```json
{
  "id": 7003,
  "code": "shadow_ball",
  "nome": "Shadow Ball",
  "tipo": "Sombrio",
  "estilo": "projetil",
  "custo": 40,
  "intervalo": 8,
  "multiplicador_dano": 1.4,
  "pode_criticar": true,
  "aplica_stab": true,
  "projetil": {
    "raio": 0.35,
    "alcance": 8.0,
    "velocidade": 180,
    "aceleracao": 0,
    "massa": 0,
    "quantidade": 1,
    "angulo_entre_projeteis": 0,
    "intervalo_entre_projeteis": 0
  },
  "colisao": {
    "colide_com": ["pokemon", "parede", "projetil", "construto"],
    "pokemon": {
      "disparo": "executa_principal",
      "comportamento_fim": "destruir"
    },
    "parede": {
      "disparo": "nenhum",
      "comportamento_fim": "destruir"
    },
    "projetil": {
      "disparo": "nenhum",
      "comportamento_fim": "destruir"
    },
    "construto": {
      "disparo": "executa_principal",
      "comportamento_fim": "destruir"
    }
  },
  "ricochete": {
    "pokemon": {
      "permite": false,
      "max": 0
    },
    "parede": {
      "permite": false,
      "max": 0
    },
    "projetil": {
      "permite": false,
      "max": 0
    },
    "construto": {
      "permite": false,
      "max": 0
    }
  },
  "atravessar": {
    "pokemon": {
      "permite": false,
      "max": 0
    },
    "parede": {
      "permite": false,
      "max": 0
    },
    "projetil": {
      "permite": false,
      "max": 0
    },
    "construto": {
      "permite": false,
      "max": 0
    }
  },
  "visual": {
    "preview": {
      "forma": "linha_projetil"
    },
    "efeito_alvo": "Impacto_Sombrio",
    "projetil_imagem": "shadow_ball.png"
  }
}
```

#### 23.1.5. Área

```json
{
  "id": 7004,
  "code": "heat_wave",
  "nome": "Heat Wave",
  "tipo": "Fogo",
  "estilo": "area",
  "custo": 45,
  "intervalo": 10,
  "multiplicador_dano": 1.3,
  "pode_criticar": true,
  "aplica_stab": true,
  "area": {
    "modo": "cone",
    "alcance": 5.0,
    "abertura_graus": 70
  },
  "visual": {
    "preview": {
      "forma": "cone"
    },
    "efeito_alvo": "Fogo_Conico",
    "projetil_imagem": null
  }
}
```

#### 23.1.6. Zona

```json
{
  "id": 7005,
  "code": "poison_pool",
  "nome": "Poison Pool",
  "tipo": "Venenoso",
  "estilo": "zona",
  "custo": 50,
  "intervalo": 12,
  "multiplicador_dano": 1.0,
  "pode_criticar": false,
  "aplica_stab": true,
  "zona": {
    "raio": 2.0,
    "alcance_max_centro": 6.0
  },
  "visual": {
    "preview": {
      "forma": "circulo_zona"
    },
    "efeito_alvo": "Gas_Venenoso",
    "projetil_imagem": null
  }
}
```

#### 23.1.7. Laser

```json
{
  "id": 7006,
  "code": "solar_beam",
  "nome": "Solar Beam",
  "tipo": "Planta",
  "estilo": "laser",
  "custo": 60,
  "intervalo": 15,
  "multiplicador_dano": 1.8,
  "pode_criticar": true,
  "aplica_stab": true,
  "laser": {
    "alcance": 9.0,
    "grossura": 0.9,
    "velocidade_avanco": 0.25
  },
  "visual": {
    "preview": {
      "forma": "corredor_laser"
    },
    "efeito_alvo": "Laser_Planta",
    "projetil_imagem": null
  }
}
```

#### 23.1.8. Dash

Dash pode ter distância fixa ou distância configurável entre mínimo e máximo.

```json
{
  "id": 7007,
  "code": "horn_dash",
  "nome": "Horn Dash",
  "tipo": "Normal",
  "estilo": "dash",
  "custo": 35,
  "intervalo": 4,
  "multiplicador_dano": 1.1,
  "pode_criticar": false,
  "aplica_stab": true,
  "movimento_ofensivo": {
    "modo": "dash",
    "vel_percentual": 1.6,
    "distancia_fixa": null,
    "distancia_min": 2.0,
    "distancia_max": 5.0,
    "atravessa_pokemon": false
  },
  "visual": {
    "preview": {
      "forma": "seta_dash"
    },
    "efeito_alvo": "Impacto_Chifrada",
    "projetil_imagem": null
  }
}
```

#### 23.1.9. Impulso

```json
{
  "id": 7008,
  "code": "wild_charge",
  "nome": "Wild Charge",
  "tipo": "Eletrico",
  "estilo": "impulso",
  "custo": 45,
  "intervalo": 4,
  "multiplicador_dano": 1.5,
  "pode_criticar": false,
  "aplica_stab": true,
  "movimento_ofensivo": {
    "modo": "impulso",
    "vel_percentual_min": 0.8,
    "vel_percentual_max": 1.8,
    "desaceleracao_base": 12,
    "atravessa_pokemon": false
  },
  "visual": {
    "preview": {
      "forma": "seta_impulso"
    },
    "efeito_alvo": "Impacto_Eletrico",
    "projetil_imagem": null
  }
}
```

#### 23.1.10. Ataque derivado com imunes

Quando um ataque derivado precisar excluir alguém específico, a ação derivada pode nascer com uma lista de `imunes_ao_ataque`.

```json
{
  "id": 7009,
  "code": "climate_ball_zone",
  "nome": "Climate Ball Zone",
  "tipo": "Normal",
  "estilo": "zona",
  "custo": 0,
  "intervalo": 0,
  "multiplicador_dano": 0.7,
  "pode_criticar": false,
  "aplica_stab": false,
  "zona": {
    "raio": 1.8,
    "alcance_max_centro": 0
  },
  "acao_derivada": {
    "imunes_ao_ataque": ["alvo_gerador"]
  }
}
```

### 23.2. Estrutura de envio de jogada

Leitura geral recomendada:

- um pacote único por turno;
- cada ação com referência local do client;
- `payload` variável conforme a ação/estilo;
- o client envia **intenção**, não resultado.

#### 23.2.1. Pacote base

```json
{
  "partida_id": 81,
  "turno_numero": 4,
  "lado": "jogador_a",
  "acoes": [
    {
      "client_ref": "a1",
      "executor_id": "000",
      "tipo_acao": "ataque",
      "ataque_id": 7001,
      "ordem_local_executor": 1,
      "payload": {
        "alvos": ["010"]
      }
    }
  ]
}
```

#### 23.2.2. Payload de alvo

```json
{
  "alvos": ["010"]
}
```

#### 23.2.3. Payload de status autouso

Status autouso puro pode ir seco.

```json
{}
```

#### 23.2.4. Payload de projétil / laser

```json
{
  "direcao": {
    "x": 0.83,
    "y": -0.55
  }
}
```

#### 23.2.5. Payload de área / zona

```json
{
  "centro": {
    "x": 18.2,
    "y": 6.7
  }
}
```

#### 23.2.6. Payload de movimento normal

```json
{
  "destino": {
    "x": 11.4,
    "y": 8.2
  }
}
```

#### 23.2.7. Payload de dash

Como o dash pode ter distância fixa ou faixa de distância, faz sentido o payload poder carregar a distância planejada.

```json
{
  "direcao": {
    "x": 1.0,
    "y": 0.0
  },
  "distancia_planejada": 4.5
}
```

#### 23.2.8. Payload de impulso

```json
{
  "direcao": {
    "x": 0.42,
    "y": 0.90
  },
  "intensidade": 0.78
}
```

#### 23.2.9. Payload de troca

```json
{
  "reserva_id": "004"
}
```

### 23.3. Estrutura do histórico do turno

Leitura geral recomendada:

- lista plana de eventos;
- ordenação por `tick` e `ordem_tick`;
- campos comuns no topo;
- detalhes específicos em `dados`.

#### 23.3.1. Evento-base

```json
{
  "evento_id": 5001,
  "tick": 5,
  "ordem_tick": 2,
  "tipo": "dano",
  "acao_id": 4001,
  "origem_id": "000",
  "alvo_id": "010",
  "dados": {}
}
```

#### 23.3.2. Exemplo de `acao_inicio`

```json
{
  "evento_id": 5002,
  "tick": 0,
  "ordem_tick": 1,
  "tipo": "acao_inicio",
  "acao_id": 4001,
  "executor_id": "000",
  "dados": {
    "tipo_acao": "ataque",
    "ataque_id": 7001
  }
}
```

#### 23.3.3. Exemplo de `ataque_ativado`

```json
{
  "evento_id": 5003,
  "tick": 5,
  "ordem_tick": 1,
  "tipo": "ataque_ativado",
  "acao_id": 4001,
  "executor_id": "000",
  "dados": {
    "alvos": ["010"]
  }
}
```

#### 23.3.4. Exemplo de `dano`

```json
{
  "evento_id": 5004,
  "tick": 5,
  "ordem_tick": 2,
  "tipo": "dano",
  "acao_id": 4001,
  "origem_id": "000",
  "alvo_id": "010",
  "dados": {
    "dano_bruto": 120,
    "stab": 1.2,
    "critico": false,
    "multiplicador_tipo": 1.0,
    "amp": 1.0,
    "defesa_original": 80,
    "perfuracao": 15,
    "defesa_final": 65,
    "dano_pos_defesa": 73,
    "dur": 10,
    "dano_pos_dur": 66,
    "barreira_antes": 0,
    "barreira_depois": 0,
    "vida_antes": 300,
    "vida_depois": 234,
    "dano_que_tirou_vida": 66,
    "dano_absorvido": 0,
    "vamp": 0,
    "morte": false
  }
}
```

#### 23.3.5. Exemplo de `movimento_inicio`

```json
{
  "evento_id": 5005,
  "tick": 0,
  "ordem_tick": 2,
  "tipo": "movimento_inicio",
  "acao_id": 4002,
  "executor_id": "000",
  "dados": {
    "trajetoria": [
      {"tick": 0, "x": 10.5, "y": 6.5},
      {"tick": 1, "x": 10.8, "y": 6.5},
      {"tick": 2, "x": 11.1, "y": 6.5}
    ]
  }
}
```

#### 23.3.6. Exemplo de `movimento_finalizado`

```json
{
  "evento_id": 5006,
  "tick": 2,
  "ordem_tick": 3,
  "tipo": "movimento_finalizado",
  "acao_id": 4002,
  "executor_id": "000",
  "dados": {
    "motivo": "colisao"
  }
}
```

#### 23.3.7. Exemplo de `projetil_criado`

```json
{
  "evento_id": 5007,
  "tick": 8,
  "ordem_tick": 1,
  "tipo": "projetil_criado",
  "acao_id": 4003,
  "objeto_id": 1001,
  "executor_id": "000",
  "dados": {
    "trajetoria": [
      {"tick": 9, "x": 12.0, "y": 7.0},
      {"tick": 10, "x": 12.5, "y": 7.0},
      {"tick": 11, "x": 13.0, "y": 7.0}
    ]
  }
}
```

#### 23.3.8. Exemplo de `laser_inicio`

```json
{
  "evento_id": 5008,
  "tick": 7,
  "ordem_tick": 1,
  "tipo": "laser_inicio",
  "acao_id": 4004,
  "executor_id": "000",
  "dados": {
    "avanco_por_tick": [
      {"tick": 7, "percentual": 0.25},
      {"tick": 8, "percentual": 0.50},
      {"tick": 9, "percentual": 0.75},
      {"tick": 10, "percentual": 1.00}
    ]
  }
}
```

### 23.4. Estrutura do diff/finalização

Leitura geral recomendada:

- o diff traz só o que mudou;
- mas o que mudou pode vir em bloco suficientemente completo para o client reconciliar sem ambiguidade;
- efeitos devem carregar duração restante em ticks.

#### 23.4.1. Exemplo completo

```json
{
  "partida_id": 81,
  "turno_numero": 4,
  "tick_global_final": 128,
  "estado_partida_final": "MONTANDO_JOGADAS",
  "pokemons_alterados": {
    "000": {
      "vida_atual": 234,
      "energia_atual": 80,
      "posicao": {"x": 11.1, "y": 6.5}
    },
    "010": {
      "vida_atual": 234,
      "efeitos": [
        {
          "code": 5,
          "nome": "Paralisado",
          "duracao_restante_ticks": 47
        }
      ]
    }
  },
  "ativos_finais": {
    "lado_a": ["000", "001"],
    "lado_b": ["010", "011"]
  },
  "reservas_finais": {
    "lado_a": ["002", "003", "004", "005"],
    "lado_b": ["012", "013", "014", "015"]
  },
  "objetos_persistentes": {
    "1001": {
      "id": 1001,
      "tipo_objeto": "projetil",
      "posicao": {"x": 15.3, "y": 7.1},
      "ativo": true
    }
  },
  "objetos_removidos": [1002],
  "tiles_alterados": [
    {
      "x": 12,
      "y": 8,
      "efeito_tile": "Incendiado"
    }
  ],
  "clima_final": {
    "codigo": "Chuva",
    "ativo": true
  }
}
```

### 23.5. Esquema dos IDs globais

**Observação técnica importante:** como o esquema de Pokémon usa zero à esquerda (`0LS`), os exemplos JSON deste tópico mostram IDs de Pokémon como **string numérica de 3 dígitos** apenas para preservar essa leitura na documentação.
Conceitualmente, a regra fechada continua sendo a do ID numérico com prefixo/classe; se a implementação insistir em int puro até na serialização JSON, será preciso um formatador ou convenção equivalente para não perder a leitura do prefixo `0` dos Pokémon.

#### 23.5.1. Pokémons

```text
0LS
```

Onde:

- `0` = tipo Pokémon;
- `L` = lado (`0` ou `1`);
- `S` = slot (`0` a `5`).

Exemplos:

```text
000 = lado 0, slot 0
015 = lado 1, slot 5
```

#### 23.5.2. Demais classes

```text
1... = projétil
2... = construto
3... = parede
4... = ação
5... = evento
6... = turno
7... = ataque
```

Exemplos:

```text
1001 = projétil 1
2004 = construto 4
3002 = parede 2
4012 = ação 12
5033 = evento 33
6007 = turno 7
7005 = ataque 5
```

### 23.6. Estados macro da partida

Leitura atual recomendada:

```text
MONTANDO_JOGADAS
AGUARDANDO_ENVIO
RODANDO_TURNO
ANIMANDO_TURNO
ENCERRADA
```

Leitura prática:

- `MONTANDO_JOGADAS`: partida aberta para preparar jogadas;
- `AGUARDANDO_ENVIO`: um lado já enviou e o outro ainda não, ou a partida está em espera/timeout de envio;
- `RODANDO_TURNO`: servidor validando e simulando o turno;
- `ANIMANDO_TURNO`: turno já resolvido no servidor e apenas aguardando leitura/animação do resultado;
- `ENCERRADA`: fase final de conferência do resultado/log com o estado da partida e fechamento definitivo da batalha.

### 23.7. Convenção de coordenadas

Leitura atual recomendada:

- coordenada interna da simulação = **float contínuo**;
- origem interna = `(0,0)` no canto superior esquerdo;
- arena padrão 40x20 usa `x` em `[0,40)` e `y` em `[0,20)`;
- o tile correspondente é lido com `floor(x)` e `floor(y)`;
- o centro do tile `(0,0)` é `(0.5, 0.5)`;
- a visualização humana pode mostrar `(1,1)` no lugar de `(0,0)`.

Exemplo:

```text
posicao interna = (23.45803, 12.342445)
tile interno = (23, 12)
leitura visual para o jogador = (24, 13)
```

O client deve enviar e o server deve trabalhar com coordenada interna, não com a coordenada visual traduzida para o jogador.

---

## 24. VISUALIZADOR DE LOGS

O visualizador de logs deve transformar o histórico técnico em texto compreensível.

Quando possível, compilar uma ação em texto simples.

Mas alguns eventos devem aparecer como registros próprios:

- movimento;
- dash;
- impulso;
- projéteis criados/finalizados;
- colisões;
- passivas;
- mortes;
- trocas;
- ricochetes;
- eventos sem ação direta;
- clima;
- interações relevantes de tile.

---

## 25. ANIMAÇÃO

### 24.1. Fonte da animação

A animação do turno deve ler o histórico.  
Ela precisa ser extremamente fiel ao que realmente ocorreu no servidor.

Leitura importante: o leitor/animação não recalcula dano, cura, energia ou barreira.  
Ele apenas aplica os valores finais já calculados pelo servidor.

### 24.2. Movimento visual

Mesmo que a simulação seja por tick, o visual não deve parecer travado.  
O client deve interpolar/deslizar entre a posição de um tick e a posição do próximo tick.

### 24.3. PokemonAnimator

`PokemonAnimator` deve continuar existindo como base de animações prontas.

Animações necessárias incluem:

- tomar dano;
- receber cura;
- sofrer efeito/gif por cima;
- lançar projétil;
- mover;
- morrer;
- aplicar dano em área;
- aplicar dano em zona;
- aplicar dano em laser;
- mostrar efeito ativo abaixo do Pokémon.

### 24.4. Efeito visual ativo

Efeitos ativos devem aparecer como círculos abaixo do Pokémon, até 3 visíveis.

- fundo verde claro para positivo;
- fundo vermelho claro para negativo;
- borda circular como timer girando conforme a duração restante.

### 24.5. Visual dos tiles

Os tiles precisam comunicar visualmente seus efeitos sem depender de texto.

---

## 26. PONTOS IMPORTANTES DE MIGRAÇÃO DO LEGADO

### 25.1. Fórmulas atuais a substituir

O código atual usa fórmulas que não são mais oficiais, por exemplo:

- velocidade baseada em média de Vel dos Pokémon vivos;
- início em tick global + mínimo 1;
- segunda ação com acréscimo legado de 20%;
- velocidade antiga usando `+100` e divisão por `500`;
- deslocamentos físicos antigos sem a leitura atual de `velocidade_de_movimento`;
- efeitos antigos por turno em `FimTurno`;
- dano periódico antigo com percentuais diferentes;
- energia máxima sendo ajustada durante `Verifica()`;
- clima/arena fora do fluxo principal;
- tabela antiga de efeitos com nomes diferentes.

Essas partes devem ser substituídas pelo modelo deste documento.

### 25.2. Fluxos antigos

O modelo de `Fluxos.json` e `LeitorFluxos.py` não deve ser a base da batalha nova.  
As novas formas devem nascer do JSON técnico dos ataques.

Fluxos antigos podem continuar existindo fora da batalha se algum módulo externo ainda precisar deles.

### 25.3. Logs antigos

O formato atual de log em blocos pode inspirar a reprodução visual, mas deve ser trocado por histórico rico de eventos com tick local e trajetórias agregadas.

### 25.4. IA atual

A IA atual pode inspirar heurísticas, mas o contrato novo é: IA no client monta ações e envia ao servidor como se fosse jogador.

### 25.5. Falhas arquiteturais que este documento tenta evitar

As seguintes falhas devem ser evitadas como diretriz:

- ataque mexendo diretamente no estado interno do alvo sem passar por método do Pokémon;
- projétil sendo tratado como mera continuação do ataque, em vez de objeto com vida própria;
- excesso de flags de ataque para cobrir casos que o execute resolveria melhor;
- ausência de um dono explícito do estado global da batalha;
- fechamento do turno fora da classe Partida;
- mistura entre ação, ataque e objeto gerado como se fossem a mesma coisa.

---

## 27. CONSTANTES OFICIAIS ATUAIS

- tick local do turno começa em 0.
- `TickGlobal` representa a partida inteira.
- `tick_nascimento_acao = maior_Int_da_partida - Int_do_pokemon`.
- `tick_ativacao = tick_nascimento_acao + intervalo`.
- timeout do turno = 1000 ticks.
- limite por lado = 5 ações por turno.
- limite por Pokémon = 2 ações por turno.
- segunda ação custa +10% de energia.
- movimento normal como segunda ação não recebe o acréscimo de 10%.
- não existe terceira ação por Pokémon.
- troca dura 5 ticks.
- troca é concluída no tick 5.
- troca não custa energia.
- movimento normal usa `velocidade_de_movimento = max(0, Vel + 50)`.
- movimento normal usa `tiles_por_tick = velocidade_de_movimento / 400`.
- custo por tile movido = `min(30, round(Peso / 20)) + 5`.
- deslocamentos como movimento normal e dash descontam energia ao longo do deslocamento.
- velocidade real da física = velocidade de movimento.
- potência física = `(Peso / 10) * velocidade_de_movimento`.
- dano de colisão usa impacto compartilhado: `impacto = potencia_a + potencia_b`; depois `dano_a_em_b = impacto * 0.10 + Atk_a * 0.06` e `dano_b_em_a = impacto * 0.10 + Atk_b * 0.06`.
- STAB = +20% de dano.
- perfuração = `Per / 2`.
- perfuração não mexe em defesa já negativa.
- defesa positiva pós-perfuração tem mínimo 0.
- dano com defesa positiva = `dano * 100 / (100 + defesa)`.
- CrC é porcentagem direta.
- CrD é bônus percentual de dano crítico.
- crítico rola por alvo.
- Dur não pode passar de 100.
- Amp não pode passar de -100 para baixo.
- efeitos possuem duração em ticks e pausam durante preparação.
- reaplicação do mesmo efeito soma duração.
- duração máxima total de um mesmo efeito = 500 ticks.
- duração mínima de efeito = 50% da base.
- arredondamento de duração inicial = `round()`.
- duração interna de efeito pode ser decimal.
- arena padrão atual = 40 x 20 tiles.
- só pode existir um clima por vez.
- clima tem 25% de chance de sair ao final de cada turno.
- clima criado ou substituído durante o turno atual não rola saída nesse mesmo fim de turno.
- após Energizado acabar, energia excedente acima de EneM persiste, mas não pode continuar aumentando acima desse excedente sem o efeito ativo.
- tiles de efeito persistem na arena.
- tile não acumula múltiplos efeitos: o último substitui o anterior.
- parede é objeto fixo e usa colisão retangular.
- atrito base = `0.15`.
- atrito no tile Gelado = `0.05`.
- atrito no tile Destruído = `0.25`.
- desaceleração por atrito = `coeficiente_de_atrito * Peso`, com mínimo 5 e máximo 40.
- massa efetiva da colisão = `max(1, Peso / 10)`.
- fator tangencial base da colisão: normal = `0.85`, tile Gelado = `0.95`, tile Destruído = `0.70`.
- coeficientes de restituição base: Pokémon vs Pokémon = `0.20`, Pokémon vs parede = `0.35`, Dash vs parede = `0.45`, Impulso vs parede = `0.55`.
- colisões geram impulso, não “movimento com alvo” persistente.
- objetos criados durante um tick só passam a agir no próximo tick.
- projéteis não são afetados por tiles neste modelo.
- IDs usam primeiro dígito para representar a classe do identificador.
- Pokémon usam ID fixo de 3 dígitos no formato `0LS`, com lado e slot embutidos.
- projétil usa prefixo `1`; construto usa prefixo `2`; parede usa prefixo `3`; ação usa prefixo `4`; evento usa prefixo `5`; turno usa prefixo `6`; ataque usa prefixo `7`.
- estado `ENCERRADA` representa a fase final de conferência entre resultado/log e estado real da partida antes do fechamento definitivo.
- coordenada interna da arena é contínua, `0`-based e baseada em float; a leitura `(1,1)` é apenas visual para o jogador.
- verificação formal de vitória/derrota ocorre em `finalizar_turno()`.

---

## 28. PENDÊNCIAS AINDA EM ABERTO

Estas pendências ainda precisam ser fechadas depois:

1. Como o visualizador deve resumir eventos extremamente complexos.
2. Quais detalhes do dano ficam públicos e quais ficam apenas como debug.
3. Como modelar construtos altamente irregulares.
4. Até onde ataques futuros poderão alterar tipo do Pokémon.
5. Se tiles poderão futuramente afetar projéteis.
6. Se o tamanho da arena poderá mudar em modelos muito futuros.
7. Detalhes finos de ordenação em empates absolutos após aplicação do critério de velocidade e da ordem estável determinística.
8. Contrato final de retorno mínimo/útil dos métodos dos Pokémon.
9. Contrato final entre log do turno e log geral da partida.
10. Quanto da API de métodos também será espelhada para construtos ativos.
11. Se haverá dispatcher central de passivas ou se tudo ficará encapsulado nos métodos.

---

**FIM DAS DIRETRIZES DE BATALHA.**

---

# PARTE II — ARQUITETURA

## ARQUITETURA DA BATALHA

**Projeto:** Pokemon Global Server  
**Base de verdade:** seção de Diretrizes consolidada neste mesmo arquivo  
**Objetivo desta seção:** definir a arquitetura-alvo enxuta da nova batalha, com foco em arquivos, classes, responsabilidades e métodos principais, sem código real.

---

## 1. Critério usado para esta arquitetura

Esta arquitetura foi montada cruzando:

1. a seção consolidada de diretrizes da batalha neste mesmo arquivo, que define o modelo novo como **servidor autoritativo por ticks**, com **Partida** como dona do estado, **cliente como montador/animação**, **JSON técnico como fonte de verdade**, **ações como objetos temporais**, **objetos de batalha com vida própria**, e **histórico rico por eventos**;
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
O construtor monta a ação com seu `tick_nascimento_acao`, soma o intervalo e define o `tick_ativacao` antes de colocá-la na fila simples do turno.  
Quando a ação roda, os executes podem chamar métodos, mutar a própria ação, criar novas ações e criar objetos.

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
- guardar origem, posição, velocidade, raio, alcance restante, massa opcional e executes embutidos;
- possuir uma ação interna de movimento;
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
- rodar esse detector global todo tick para os objetos de batalha do sistema;
- impedir dupla resolução do mesmo par no mesmo tick;
- impedir sobreposição persistente no mesmo tick quando não houver atravessar;
- marcar estados de travessia quando um objeto estiver atravessando outro.

### Observação importante
Áreas e lasers não entram nesse detector global, porque não são filhos da hierarquia de objeto de batalha.  
Eles usam detecção própria dentro das próprias classes.

### Métodos principais
- `coletar_colisoes_tick()`: devolve lista de colisões do tick.
- `colisao_pokemon_pokemon()`: detecta colisão entre pokémons.
- `colisao_objeto_parede()`: detecta colisão com parede.
- `colisao_projetil_objeto()`: detecta colisão de projétil.
- `ja_processada()`: verifica se a colisão do par já foi tratada.
- `registrar_processada()`: marca par como já processado no tick.
- `marcar_atravessando()`: registra pares em travessia quando a propriedade permitir.
- `limpar_tick()`: limpa memória local da deduplicação para o próximo tick.

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
- ordenar ações pela fila simples do turno usando `tick_ativacao`, com velocidade como critério de desempate quando necessário.

### Métodos principais
- `receber_jogadas()`: recebe o pacote bruto de jogadas.
- `validar_jogadas()`: valida regras básicas de quantidade e formato.
- `normalizar_jogadas()`: normaliza os dados de entrada.
- `ordenar_jogadas()`: aplica ordenação por inteligência e ordem local.
- `custo_jogada_multiplas_acoes()`: calcula custo com regra da segunda ação.
- `jogadas_prontas()`: devolve jogadas prontas para o executor do turno.

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

### Observação arquitetural
As ações são criadas por pokémons ou construtos por método próprio e já existem como objetos Python enquanto aguardam na fila do turno.

### Classes principais
- `AcaoBase`: contrato comum de qualquer ação do turno.
- `AcaoAtaque`: filha de `AcaoBase`, base de ataques que não são movimento puro.
- `AcaoTroca`: filha de `AcaoBase`, responsável pela troca entre ativo e reserva.
- `AcaoMover`: filha de `AcaoBase`, base de deslocamentos.

### Métodos principais de `AcaoBase`
- `iniciar()`: marca a ativação oficial da ação.
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

# 9. `SimuladorServerJogo/Batalha/ConstrutorAtaque.py`

## 9.1. Papel
Arquivo que recebe `PropriedadesAtaque` e os dados enviados pelo jogador para construir a ação concreta do estilo correto.

### Leitura arquitetural
`PropriedadesAtaque` + envio do jogador (direção, alvo quando couber, intensidade quando couber) entram no construtor.  
O construtor escolhe a classe correta do estilo, acopla automaticamente execute principal, execute de estado e executes periféricos quando necessário, define a lista de imunes ao ataque quando couber, e devolve a ação pronta para a fila do turno.  
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
- `calcular_tick_ativacao()`: calcula o `tick_ativacao` da ação somando `tick_nascimento_acao` e intervalo.

### Métodos principais das classes de estilo
- `resolver_alvo()`: decide alvo real da ativação quando o estilo exigir.
- `criar_objeto()`: cria projétil ou construto quando o estilo exigir.
- `coletar_alvos_area()`: resolve área/zona quando o estilo exigir.
- `resolver_ticks_laser()`: executa a faixa do laser ao longo dos ticks.
- `resolver_impacto_movimento()`: resolve dash/impulso quando a colisão disparar execute.
- `resolver_comportamento_fim_colisao()`: aplica destruir/ricochetear/atravessar após colisão relevante, especialmente em projéteis.

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
- o **DetectorColisoes** manda no detector global de colisões entre objetos de batalha;
- o **LogBatalha** manda no histórico;
- o **ExecuteAtaques** centraliza apenas os três tipos de execute do ataque;
- passivas continuam onde já fazem mais sentido: nos métodos e nos arquivos `.py` próprios de item/habilidade.

---

# PARTE III — PLANO DE IMPLEMENTAÇÃO

## PLANO DE IMPLEMENTAÇÃO

**Projeto:** Pokemon Global Server  
**Escopo:** implementação do **novo modelo de batalha**  
**Base de verdade principal:** seção de Diretrizes deste mesmo arquivo  
**Base complementar:** seção de Arquitetura deste mesmo arquivo  
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
Mas, em caso de conflito, a referência mais autoritária é sempre a seção de **diretrizes** deste mesmo arquivo.

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
