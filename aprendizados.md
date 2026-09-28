# Aprendizados (compartilhados)

Regras aprendidas na prática com a API. O Claude DEVE ler este arquivo antes de criar qualquer objeto.
Aprendizado pessoal de cada gestor fica em ~/OdontoRise/meta-ads/aprendizados-local.md.

### 2026-09-28: editar segmentação apaga o que não for reenviado
Regra: antes de editar o targeting de um conjunto, ler o targeting atual e reenviar o objeto inteiro com a mudança.
Contexto: um POST só com a idade apagou públicos, exclusões e raio do conjunto.

### 2026-09-28: aprimoramentos sem a chave standard_enhancements
Regra: desligar os aprimoramentos Advantage+ recurso por recurso e nunca enviar a chave standard_enhancements.
Contexto: a chave foi descontinuada e a Meta recusa o criativo com o erro 3858504.

### 2026-09-28: público explícito no conjunto
Regra: enviar targeting_automation.advantage_audience com 0 ou 1 em todo conjunto novo.
Contexto: sem o campo a Meta recusa o conjunto com o erro 1870227.

### 2026-09-28: explore_home exige explore
Regra: ao incluir explore_home nas posições do Instagram, incluir também explore.
Contexto: erro 2490392 ao criar o conjunto.

### 2026-09-28: reel com música protegida não vira anúncio
Regra: antes de transformar um post em anúncio, conferir se o reel usa música com direitos autorais; se usar, escolher outro post.
Contexto: erro 2875030 ao criar o criativo a partir do post.

### 2026-09-28: data de início só na criação do conjunto
Regra: definir start_time ao criar o conjunto; depois de criado, a data não muda pela API.
Contexto: tentativa de ajustar o início após a criação foi ignorada.
