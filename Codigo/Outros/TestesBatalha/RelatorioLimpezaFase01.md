# Relatório de Limpeza — Fase 1.1

## Arquivos deletados
- `Codigo/ModulosBatalha/ControladorFluxos.py`
- `Codigo/Paineis/PainelJogada.py`

## Arquivos criados para substituição
- `Codigo/Paineis/PainelAcoes.py` (substituto do painel antigo no núcleo da HUD de batalha).

## Arquivos mantidos temporariamente (LEGADO TEMPORÁRIO)
- `Codigo/ModulosBatalha/LeitorFluxos.py`  
  Motivo: ainda é dependência direta de `SimuladorServerJogo/Batalha/LeitorJogadas.py` (fluxo legado de servidor fora do caminho ativo da Fase 1.1).
- `Codigo/ModulosBatalha/SistemaBatalha.py`  
  Motivo: `ControladorBatalha.py` ainda depende desse adaptador para sincronização/snapshot/resultado atual de batalha cliente.
- `SimuladorServerJogo/Batalha/LeitorJogadas.py`  
  Motivo: ainda acoplado ao `GerenciadorBatalhas.py` do fluxo legado do servidor.
- `SimuladorServerJogo/Batalha/SistemaBatalha.py`  
  Motivo: ainda é estado autoritativo legado usado por `GerenciadorBatalhas.py`.
- `SimuladorServerJogo/Batalha/SimuladorFisica.py`  
  Motivo: ainda referenciado por `LeitorJogadas.py` no fluxo legado do servidor.

## Imports removidos no núcleo da Fase 1.1
- Removido import de `ControladorFluxos` em `Codigo/ModulosBatalha/ElementosHudBatalha.py`.
- Removido import de `PainelJogada` em `Codigo/ModulosBatalha/ElementosHudBatalha.py`.
- Migrado para `PainelAcoes` em `Codigo/ModulosBatalha/ElementosHudBatalha.py`.

## Dependências que ainda impedem deleção total nesta subfase
- `LeitorFluxos.py` depende do legado de servidor (`LeitorJogadas.py`).
- `SimuladorFisica.py` depende do legado de servidor (`LeitorJogadas.py`).
- `LeitorJogadas.py` e `SistemaBatalha.py` do servidor dependem de `GerenciadorBatalhas.py` (rotas antigas não migradas para Partida nesta fase).

## Confirmação do caminho ativo da Fase 1.1
- `TesteFase01.py` e `BatalhaTeste.py` **não dependem** de `Fluxos.json`, `LeitorFluxos.py` ou `ControladorFluxos.py`.
- `ElementosHudBatalha.py` **não depende** de `ControladorFluxos.py` e `PainelJogada.py`.

## Varredura textual executada
Comandos usados:
- `rg -n "PlayerControleBat" Codigo SimuladorServerJogo Dados || true`
- `rg -n "LeitorFluxos" Codigo SimuladorServerJogo Dados || true`
- `rg -n "ControladorFluxos" Codigo SimuladorServerJogo Dados || true`
- `rg -n "PainelJogada" Codigo SimuladorServerJogo Dados || true`
- `rg -n "Fluxos\.json" Codigo SimuladorServerJogo Dados || true`
- `rg -n "SimuladorFisica" Codigo SimuladorServerJogo Dados || true`
- `rg -n "LeitorJogadas" Codigo SimuladorServerJogo Dados || true`
