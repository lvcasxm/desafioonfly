# Declaração de uso de IA

## Ferramenta e modelo

- **Ferramenta:** Claude Code (app desktop, aba Code)
- **Modelo:** Claude Opus 5.5 (`claude-opus-5-5`)

A exportação da sessão está em `sessao.md` nesta pasta.

## O que a IA fez

- Leu o README e o código-fonte, perfilou os CSVs de dados e rodou o baseline de testes.
- Identificou os cinco defeitos e suas causas raiz, e aplicou as correções.
- Validou o resultado contra a amostra do README e com um recálculo independente do dataset completo.
- Escreveu `tests/test_additional_rules.py` e o rascunho de `entrega/README-ENTREGA.md`.

## O que eu fiz

- Defini a tarefa e conduzi a sessão com o assistente.
- Revisei cada uma das cinco correções, conferindo a alteração no código contra a regra correspondente do README.
- Criei o repositório público no GitHub, organizei os arquivos para a entrega e enviei o link.
