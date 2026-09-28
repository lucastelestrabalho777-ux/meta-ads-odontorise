# meta-ads-odontorise

Skill de Claude Code para os gestores de tráfego da OdontoRise operarem as contas Meta Ads
dos clientes (clínicas odontológicas) com campanhas de conversão ao WhatsApp.

Molde de estrutura: skill meta-ads-ratos (Ratos de IA). Conteúdo, regras e métricas próprios.

## Estado

Em construção, uma parte por vez. Parte 1 (biblioteca de conexão) pronta e testada em 28/09/2026.

## Onde ficam as coisas

| O quê | Onde | Entra no repositório? |
|---|---|---|
| Skill (regras, scripts, referências) | esta pasta | sim |
| Credencial de cada pessoa | `~/OdontoRise/credentials/meta-odontorise.env` | nunca |
| Cadastro de clientes, aprendizados locais, auditoria | `~/OdontoRise/meta-ads/` | nunca |

## Dependências

```bash
python3 -m pip install --user -r requirements.txt
```

## Regras de segredo

Token, chave secreta e senha ficam só no arquivo de credencial, com permissão 600.
Nunca em nota, memória, print, chat, WhatsApp, Drive ou neste repositório.
Os scripts mostram o token sempre mascarado.
