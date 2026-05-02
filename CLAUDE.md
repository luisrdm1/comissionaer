# ComissionAER — instruções para o agente

## Git: push

Sempre pushar para os dois remotes ao commitar:

```bash
git push forgejo master
git push origin master
```

`forgejo` = servidor local (forgejo.lan). `origin` = GitHub (luisrdm1/comissionaer).

## Stack

- Python 3.14, uv, pyright strict, ruff
- fpdf2 para PDF, xlrd/xlwt para XLS, PyYAML para YAML
- Decimal para todos os valores monetários (nunca float)

## Regras de cálculo

- Diárias: `(dias - 0.5) × valor_categoria + R$ 95,00 × num_deslocamentos`
- Dias: inclusivo em ambas as extremidades (`termino - inicio + 1`)
- Duração LONGO exige > 90 dias totais de missões
- Ajuda de custo: `fator_ida × base_abertura + fator_volta × base_encerramento`
- Compensação orgânica: usar o valor **transitório** (20% se voando), não apenas cotas incorporadas — confirmado pela planilha IAOp

## Cotas de voo

Válidas de 0 a 10 (cada cota = 2%, máximo 20%). Perguntar como inteiro no CLI.
