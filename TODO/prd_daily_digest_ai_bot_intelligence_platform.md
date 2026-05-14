# PRD — Daily Digest AI Bot como AI Intelligence Platform

## 1. Visão do Produto

O **Daily Digest AI Bot** deve evoluir de um bot que coleta e envia notícias para uma plataforma de inteligência sobre IA.

A proposta não é simplesmente coletar mais fontes, links ou artigos. O objetivo é transformar centenas de sinais espalhados pela internet em poucos insights realmente relevantes, organizados, ranqueados e prontos para consumo.

O produto final deve funcionar como um **AI Intelligence Briefing** para desenvolvedores, builders e pessoas que querem acompanhar o ecossistema de IA sem precisar ler centenas de conteúdos por dia.

Em vez de entregar:

```txt
200 links soltos por dia
```

O sistema deve entregar:

```txt
5 a 10 tendências importantes, explicadas com contexto, impacto e links relevantes.
```

---

## 2. Mudança Principal de Mentalidade

### Antes

```txt
source-driven system
```

O sistema era orientado por fontes:

- coletar RSS;
- coletar GitHub;
- coletar blogs;
- resumir cada item;
- enviar item por item.

### Depois

```txt
signal-driven intelligence system
```

O sistema deve ser orientado por sinais:

- detectar tendências;
- correlacionar múltiplas fontes;
- eliminar ruído;
- identificar novidade real;
- entender impacto técnico;
- gerar um digest consolidado;
- enviar apenas o que merece atenção.

---

## 3. Problema Atual

O bot já possui uma base técnica boa, com pipeline distribuído, processamento assíncrono, cache, deduplicação, extração multi-layer, scoring, análise com IA, dispatch automatizado, circuit breaker, rate limiting e DLQ.

Porém, o problema principal agora é outro:

```txt
coletar conteúdo não é mais o gargalo.
```

O gargalo real é:

```txt
separar sinal de ruído.
```

### Problemas observados

1. **Excesso de mensagens no Telegram**  
   O modelo atual ainda se aproxima de `1 item = 1 mensagem`, gerando spam e fadiga de informação.

2. **Pouca correlação entre fontes**  
   Um paper, um repo, um tweet e um artigo sobre o mesmo assunto são tratados como itens separados.

3. **Baixa inteligência de tendência**  
   O sistema coleta conteúdo, mas ainda não detecta momentum, crescimento, adoção ou impacto real.

4. **Fontes ainda muito estáticas**  
   O sistema depende demais de feeds pré-configurados e pouca descoberta dinâmica.

5. **Resumo sem contexto suficiente**  
   O usuário não quer apenas saber “o que aconteceu”, mas sim “por que isso importa”.

---

## 4. Objetivo do Produto

Transformar o bot de:

```txt
news bot
```

Para:

```txt
AI Intelligence Platform
```

E transformar o Telegram de:

```txt
lista de links
```

Para:

```txt
painel diário de inteligência de IA
```

O usuário deve abrir o Telegram e sentir:

```txt
“se apareceu aqui, é porque realmente importa.”
```

---

## 5. Resultado Esperado

O sistema deve entregar um digest com:

- poucas mensagens;
- alta densidade de informação;
- contexto claro;
- explicação de impacto;
- links relevantes;
- tópicos agrupados;
- tendências detectadas;
- recomendações práticas;
- leitura rápida;
- baixa repetição;
- baixa quantidade de ruído.

---

## 6. Arquitetura Atual

A arquitetura atual pode ser resumida assim:

```txt
collect
↓
extract
↓
analyze
↓
score
↓
summarize
↓
dispatch
```

Ela funciona bem para coletar, resumir e enviar conteúdos individuais.

Mas ela ainda não é suficiente para produzir inteligência consolidada.

---

## 7. Arquitetura-Alvo

A nova arquitetura deve ser:

```txt
source discovery
↓
collect
↓
extract
↓
entity detection
↓
semantic clustering
↓
cross-source correlation
↓
trend detection
↓
ranking
↓
structured summarization
↓
formatter.py
↓
dispatch
```

Ou, em visão por camadas:

```txt
[DISCOVERY]
Source discovery engine
↓

[COLLECT]
GitHub + Papers + Blogs + Reddit + HN + Twitter/X + YouTube
↓

[EXTRACT]
Crawl4AI + Jina + Trafilatura + transcripts
↓

[UNDERSTANDING]
Entity detection + embeddings + semantic clustering
↓

[TREND ENGINE]
Novelty + momentum + cross-source validation
↓

[SCORING]
Technical depth + authority + adoption + implementation value
↓

[SUMMARIZATION]
Why this matters + implications + use cases + structured JSON
↓

[FORMATTER]
Telegram HTML/Markdown-safe visual formatting
↓

[DISPATCH]
Realtime alerts + daily digest
```

---

## 8. Princípio Central do Novo Sistema

O sistema não deve mais perguntar apenas:

```txt
“isso é um conteúdo válido?”
```

Ele deve perguntar:

```txt
“isso merece a atenção do usuário?”
```

Essa pergunta vira a base do novo score.

---

## 9. Attention Economy Score

Criar uma métrica central chamada **Attention Economy Score**.

Ela deve responder:

```txt
vale interromper o usuário por isso?
```

### O sistema deve priorizar

- novo modelo lançado;
- novo benchmark importante;
- mudança importante de API;
- novo framework relevante;
- repo crescendo rapidamente;
- ferramenta que muda workflow de desenvolvedor;
- técnica nova para agents, RAG, reasoning, inference ou automação;
- paper com código disponível;
- lançamento de empresa relevante;
- tópico aparecendo em múltiplas fontes confiáveis.

### O sistema deve ignorar

- wrappers genéricos;
- clickbait;
- “10 prompts para ChatGPT”;
- tutoriais rasos;
- hype sem adoção;
- artigos repetidos;
- conteúdo reciclado;
- startups irrelevantes sem sinal técnico;
- conteúdo sem impacto prático.

---

## 10. Requisitos Funcionais

### RF01 — Agrupar conteúdos por tópico

O sistema deve agrupar múltiplas fontes que falam sobre o mesmo assunto.

Exemplo:

```txt
MCP ecosystem
├── artigo Anthropic
├── repo GitHub
├── discussão Hacker News
├── tweets técnicos
├── vídeo demo
└── paper relacionado
```

Isso deve virar um único item consolidado:

```txt
🔥 MCP ecosystem accelerating
```

---

### RF02 — Detectar entidades

Implementar uma camada de **Entity Detection / Entity Resolution** para reconhecer e normalizar:

- empresas;
- frameworks;
- modelos;
- autores;
- papers;
- repositórios;
- conceitos técnicos;
- organizações;
- ferramentas.

Exemplo:

```txt
Claude Code
├── repo GitHub
├── artigo Anthropic
├── tutorial
├── vídeo
└── discussão HN
```

Tudo deve ser tratado como parte de um mesmo tópico quando houver forte relação.

---

### RF03 — Semantic Clustering

Implementar agrupamento semântico via embeddings.

Objetivo:

- identificar conteúdos similares;
- reduzir duplicidade;
- agrupar por tendência;
- evitar mensagens repetidas;
- preservar fontes relevantes dentro do tópico.

Regra inicial sugerida:

```py
cosine_similarity > 0.92
```

Importante: clustering não deve apagar informação relevante. Ele deve agrupar conteúdos em um tópico consolidado.

---

### RF04 — Cross-Source Correlation

O sistema deve detectar quando um mesmo tópico aparece em múltiplas fontes.

Fontes possíveis:

- GitHub;
- Arxiv;
- blogs técnicos;
- OpenAI;
- Anthropic;
- Google DeepMind;
- Meta AI;
- Reddit;
- Hacker News;
- Twitter/X;
- YouTube;
- documentação oficial.

Quanto mais fontes confiáveis apontarem para o mesmo tópico, maior deve ser a confiança do sinal.

---

### RF05 — Trend Engine

Criar um motor de tendências para identificar:

- crescimento rápido;
- momentum;
- novidade;
- adoção da comunidade;
- profundidade técnica;
- impacto prático;
- validação cruzada por múltiplas fontes.

Exemplo inicial de score:

```py
trend_score = (
    cross_source_mentions * 0.30 +
    github_velocity * 0.30 +
    paper_authority * 0.20 +
    social_buzz * 0.20
)
```

---

### RF06 — Novelty Detection

O sistema deve responder:

```txt
isso é realmente novo?
```

A camada deve reduzir a pontuação de:

- hype reciclado;
- tutoriais repetidos;
- posts sem contribuição nova;
- forks superficiais;
- wrappers sem diferencial;
- conteúdo já coberto anteriormente.

E deve aumentar a pontuação de:

- técnica nova;
- framework novo com adoção real;
- benchmark novo;
- paper com contribuição relevante;
- repo recente com crescimento acelerado;
- nova API ou mudança estrutural relevante.

---

### RF07 — GitHub Velocity Scoring

O GitHub Collector não deve olhar apenas estrelas totais.

Deve medir:

- `stars_per_hour`;
- `stars_per_day`;
- `forks_recent`;
- `commits_last_24h`;
- `contributors_last_7d`;
- releases recentes;
- frequência de releases;
- issues/discussions ativas;
- README quality;
- presença de demo/documentação.

Score inicial sugerido:

```py
repo_score = (
    stars_24h * 0.40 +
    forks_recent * 0.20 +
    contributors_recent * 0.20 +
    release_recent * 0.10 +
    external_mentions * 0.10
)
```

---

### RF08 — README Intelligence

O sistema deve usar IA para entender o README dos repositórios e classificar:

- categoria do projeto;
- problema resolvido;
- público-alvo;
- maturidade;
- complexidade;
- tipo de ferramenta;
- valor prático;
- se é wrapper superficial ou ferramenta real.

---

### RF09 — Topic Expansion no GitHub

Expandir os tópicos monitorados além de AI/ML/LLM.

Lista inicial:

```txt
agents
mcp
rag
vector-database
browser-use
voice-ai
multi-agent
ai-agents
llmops
inference
reasoning
tool-calling
memory
computer-use
workflow-automation
coding-agents
ai-browser
ai-search
agent-framework
local-llm
model-serving
observability
synthetic-data
evals
```

---

### RF10 — Papers Intelligence

Melhorar a inteligência sobre papers.

O sistema deve classificar papers como:

- breakthrough;
- benchmark;
- survey;
- implementation;
- educational;
- research infrastructure;
- incremental;
- low-signal.

Também deve aplicar boost para papers de fontes com autoridade, como:

- OpenAI;
- Anthropic;
- Google DeepMind;
- Meta AI / FAIR;
- Stanford;
- Berkeley;
- CMU;
- MIT.

Critérios importantes:

- paper tem código?
- tem benchmark relevante?
- propõe técnica nova?
- vem de laboratório importante?
- já apareceu em GitHub, HN ou Twitter?
- tem potencial de virar ferramenta prática?

---

### RF11 — Source Discovery Engine

Criar um sistema de descoberta automática de novas fontes.

Exemplo:

```txt
novo repo relevante
↓
identifica organização
↓
encontra site oficial
↓
encontra blog
↓
encontra documentação
↓
encontra Twitter/X ou GitHub org
↓
sugere ou adiciona nova fonte
```

Objetivo:

```txt
self-expanding intelligence system
```

Inicialmente, a descoberta pode gerar apenas sugestões para revisão humana.

---

### RF12 — Digest por JSON Estruturado

O LLM não deve gerar o HTML final do Telegram.

O LLM deve retornar apenas JSON estruturado.

Exemplo:

```json
{
  "title": "Anthropic expands MCP ecosystem",
  "importance": 9.2,
  "category": "agent_ecosystem",
  "trend_type": "ecosystem_acceleration",
  "why_it_matters": "MCP is becoming a standard interface layer for AI agents and tools.",
  "key_points": [
    "New official integrations appeared",
    "Multiple repos are gaining traction",
    "Developers are adopting MCP for tool orchestration"
  ],
  "worth_testing": true,
  "testing_reason": "Relevant for agent automation and developer tooling.",
  "links": [
    {
      "title": "Official announcement",
      "url": "https://example.com",
      "source_type": "official_blog"
    }
  ],
  "score_breakdown": {
    "novelty": 8.5,
    "momentum": 9.4,
    "authority": 9.0,
    "implementation_value": 8.7,
    "cross_source_validation": 9.1
  }
}
```

---

### RF13 — Formatter.py para Telegram

Criar ou refatorar um `formatter.py` responsável por:

- montar HTML seguro para Telegram;
- aplicar emojis;
- aplicar espaçamento;
- organizar seções;
- truncar mensagens longas;
- escapar caracteres problemáticos;
- manter padrão visual consistente;
- reaproveitar templates;
- separar lógica visual da lógica de IA.

O LLM não deve decidir tags HTML, Markdown ou layout final.

Fluxo correto:

```txt
conteúdo bruto
↓
LLM analysis
↓
JSON estruturado
↓
formatter.py
↓
Telegram
```

---

## 11. Estrutura Ideal do Digest

### Cabeçalho

```txt
🔥 AI Intelligence Digest — Hoje
```

### Seções principais

1. **Top Trends**  
   Grandes movimentos do ecossistema.

2. **Emerging Repositories**  
   Repositórios crescendo rapidamente.

3. **Important Papers**  
   Papers realmente relevantes.

4. **AI Engineering**  
   Ferramentas práticas para desenvolvedores.

5. **Agent Ecosystem**  
   Agents, MCP, orchestration, tool-calling e memory.

6. **Infrastructure**  
   Inference, deployment, vector DBs, observability e LLMOps.

7. **Breaking News**  
   Modelos novos, APIs, releases e anúncios críticos.

---

## 12. Estrutura de Cada Item do Digest

Cada item consolidado deve ter:

### 1. Título

Curto, claro e impactante.

Exemplo:

```txt
🔥 MCP ecosystem is accelerating
```

### 2. Why This Matters

Explicar por que aquilo importa.

Deve responder:

- qual impacto técnico?
- muda algum workflow?
- melhora agents, RAG, inference, coding ou automação?
- tem valor prático?
- indica uma tendência maior?

### 3. Principais Mudanças

Lista curta.

Exemplo:

```txt
• novos repos surgindo rápido
• adoção crescente por ferramentas de agents
• mais integrações oficiais
• discussões fortes em HN e Reddit
```

### 4. Vale Testar?

Resposta objetiva:

```txt
Sim. Relevante para quem trabalha com agents e automação.
```

Ou:

```txt
Ainda não. Parece promissor, mas falta maturidade.
```

### 5. Links Relevantes

Incluir apenas links úteis:

- repo principal;
- paper;
- anúncio oficial;
- documentação;
- thread técnica;
- demo relevante.

### 6. Score de Relevância

Exemplo:

```txt
Score: 9.4/10
```

---

## 13. Sistema de Prioridade

### Tier S — Crítico

Enviar como alerta em tempo real.

Exemplos:

- lançamento de modelo importante;
- mudança crítica de API;
- breakthrough relevante;
- release de grande impacto;
- vulnerabilidade ou mudança operacional importante.

### Tier A — Alto Sinal

Entrar no digest diário.

Exemplos:

- framework relevante;
- repo explodindo;
- paper importante;
- tooling útil;
- agents, RAG, MCP ou inference com adoção real.

### Tier B — Interessante

Entrar apenas se houver espaço ou se complementar uma tendência maior.

Exemplos:

- tutorial bom;
- comparação útil;
- discussão técnica relevante;
- análise prática.

### Tier C — Ruído

Descartar.

Exemplos:

- clickbait;
- wrappers inúteis;
- hype vazio;
- conteúdo reciclado;
- posts genéricos.

---

## 14. Realtime Alerts vs Daily Digest

### Realtime Alerts

Usar apenas para Tier S.

Deve ser raro.

Exemplos:

- novo modelo de OpenAI, Anthropic, Google DeepMind ou Meta;
- mudança importante de API;
- release crítico;
- notícia que afeta diretamente developers;
- benchmark ou paper com impacto imediato.

### Daily Digest

Resumo consolidado do dia.

Deve incluir:

- Top Trends;
- Emerging Repositories;
- Important Papers;
- AI Engineering;
- Agent Ecosystem;
- Infrastructure;
- Breaking News não urgente.

---

## 15. Score Final Ideal

Criar um score final com múltiplas dimensões.

Exemplo:

```py
final_score = (
    technical_depth * 0.20 +
    novelty * 0.20 +
    momentum * 0.20 +
    community_adoption * 0.15 +
    authority * 0.15 +
    implementation_value * 0.10
)
```

### Dimensões recomendadas

#### Technical Depth

Mede se o conteúdo tem profundidade técnica real.

#### Novelty

Mede se há algo realmente novo.

#### Momentum

Mede crescimento recente.

#### Community Adoption

Mede adoção real por devs, pesquisadores ou empresas.

#### Authority

Mede confiabilidade da fonte.

#### Implementation Value

Mede utilidade prática para quem cria produtos, agentes, automações ou sistemas de IA.

#### Cross-Source Validation

Mede se o tópico aparece em múltiplas fontes independentes.

---

## 16. Fontes Recomendadas

### AI / Research

- OpenAI Blog;
- Anthropic News;
- Google DeepMind Blog;
- Meta AI / FAIR;
- HuggingFace Blog;
- LangChain Blog;
- Perplexity Blog;
- Papers With Code;
- Arxiv.

### Infra / Engineering

- Vercel Blog;
- Cloudflare Blog;
- Modal Labs;
- Replicate;
- Firecrawl;
- Pinecone;
- Weaviate;
- Supabase;
- Databricks;
- Anyscale.

### AI Engineering

- Latent Space;
- The Rundown AI;
- Ben’s Bites;
- Cognition;
- CrewAI;
- AutoGen;
- LlamaIndex;
- LangChain.

### Social Intelligence

#### Reddit

- r/LocalLLaMA;
- r/MachineLearning;
- r/OpenAI;
- r/singularity;
- r/ClaudeAI.

#### Hacker News

Importante para detectar:

- lançamentos;
- discussões técnicas;
- frameworks;
- papers;
- infra early-stage.

#### Twitter/X

Usar com cuidado por causa do ruído.

Critérios importantes:

- autoridade do autor;
- densidade técnica;
- qualidade do engajamento;
- conexão com GitHub, paper ou release oficial.

#### YouTube

Extrair transcript e classificar:

- demo;
- lançamento;
- tutorial relevante;
- análise técnica;
- conteúdo genérico.

Canais úteis:

- Fireship;
- AI Explained;
- Two Minute Papers;
- Y Combinator;
- Matthew Berman;
- NetworkChuck.

---

## 17. Knowledge Graph

No médio/longo prazo, criar um grafo de conhecimento conectando:

- tópicos;
- ferramentas;
- papers;
- autores;
- empresas;
- frameworks;
- repositórios;
- conceitos;
- fontes.

Exemplo:

```txt
MCP
├── Anthropic
├── repos
├── tutoriais
├── vídeos
├── papers
├── ferramentas
└── discussões técnicas
```

Esse grafo pode ajudar em:

- entity resolution;
- histórico de tendências;
- detecção de novidade;
- ranking por contexto;
- recomendação de links;
- explicações mais ricas.

---

## 18. Requisitos Não Funcionais

### RNF01 — Baixo custo local

Como o sistema roda em servidor próprio com GPU limitada, priorizar:

- JSON curto;
- prompts eficientes;
- etapas determinísticas em Python;
- uso do LLM apenas onde ele agrega inteligência;
- cache forte;
- deduplicação antes de chamadas ao LLM.

### RNF02 — Robustez

Manter:

- circuit breaker;
- rate limiting;
- DLQ;
- retry controlado;
- logs estruturados;
- fallback quando o LLM falhar.

### RNF03 — Observabilidade

Adicionar métricas como:

- conteúdos coletados;
- conteúdos descartados;
- clusters gerados;
- tendências detectadas;
- itens enviados;
- score médio;
- fontes mais relevantes;
- taxa de duplicidade;
- custo estimado de inferência;
- tempo por etapa.

### RNF04 — Modularidade

Separar claramente:

- collectors;
- extractors;
- analyzers;
- clustering;
- scoring;
- formatter;
- dispatch;
- storage.

---

## 19. Modelo de Dados Sugerido

### RawItem

```json
{
  "id": "string",
  "source": "github|arxiv|blog|reddit|hn|twitter|youtube",
  "url": "string",
  "title": "string",
  "content": "string",
  "author": "string|null",
  "published_at": "datetime|null",
  "collected_at": "datetime",
  "metadata": {}
}
```

### AnalyzedItem

```json
{
  "raw_item_id": "string",
  "entities": [],
  "category": "string",
  "summary": "string",
  "technical_depth": 0.0,
  "novelty": 0.0,
  "authority": 0.0,
  "implementation_value": 0.0,
  "noise_risk": 0.0,
  "embedding": []
}
```

### TopicCluster

```json
{
  "cluster_id": "string",
  "topic_name": "string",
  "items": [],
  "entities": [],
  "sources": [],
  "cross_source_count": 0,
  "momentum_score": 0.0,
  "novelty_score": 0.0,
  "trend_score": 0.0,
  "final_score": 0.0
}
```

### DigestItem

```json
{
  "title": "string",
  "category": "string",
  "tier": "S|A|B|C",
  "importance": 0.0,
  "why_it_matters": "string",
  "key_points": [],
  "worth_testing": true,
  "testing_reason": "string",
  "links": [],
  "score_breakdown": {}
}
```

---

## 20. Prompt Base para o LLM

O LLM deve ser instruído a retornar JSON, não mensagem final.

### Prompt conceitual

```txt
Você é um analisador de inteligência técnica sobre IA.

Sua tarefa é avaliar o conteúdo abaixo e retornar apenas JSON válido.

Não gere HTML.
Não gere Markdown.
Não gere texto fora do JSON.

Avalie:
- categoria
- entidades principais
- novidade
- profundidade técnica
- autoridade da fonte
- valor prático
- risco de ruído
- por que isso importa
- se vale testar
- pontos principais

Conteúdo:
{{content}}

Retorne no schema:
{
  "category": "...",
  "entities": [],
  "summary": "...",
  "technical_depth": 0-10,
  "novelty": 0-10,
  "authority": 0-10,
  "implementation_value": 0-10,
  "noise_risk": 0-10,
  "why_it_matters": "...",
  "worth_testing": true/false,
  "key_points": []
}
```

---

## 21. Template Visual do Telegram

O formatter pode gerar algo nesse estilo:

```txt
🔥 AI Intelligence Digest — 13/05/2026

Hoje o sinal forte está em: agents, MCP, coding workflows e inference.

━━━━━━━━━━━━━━
🚀 TOP TRENDS
━━━━━━━━━━━━━━

1. MCP ecosystem is accelerating
Score: 9.4/10

Why this matters:
MCP está virando uma camada padrão para conectar agents a ferramentas externas.

Principais sinais:
• 4 repos novos crescendo rápido
• discussão forte em HN
• novas integrações oficiais
• aumento de demos práticas

Vale testar?
Sim. Muito relevante para automação com agents.

Links:
• Repo principal
• Artigo oficial
• Discussão HN
```

---

## 22. Roadmap de Implementação

### Fase 1 — Arrumar o formato do Telegram

Objetivo: parar de enviar mensagens soltas e criar digest consolidado.

Tarefas:

- criar `formatter.py`;
- definir schema `DigestItem`;
- fazer LLM retornar JSON;
- criar template único para Telegram;
- limitar quantidade de mensagens por digest;
- separar realtime alerts de daily digest.

Resultado esperado:

```txt
menos spam, mais clareza e digest com padrão visual consistente.
```

---

### Fase 2 — Semantic Clustering

Objetivo: agrupar conteúdos parecidos.

Tarefas:

- gerar embeddings dos itens analisados;
- agrupar por similaridade;
- criar `TopicCluster`;
- detectar duplicatas semânticas;
- consolidar múltiplos itens em um único tópico.

Resultado esperado:

```txt
1 tendência = múltiplas fontes agrupadas.
```

---

### Fase 3 — GitHub Velocity Scoring

Objetivo: detectar repos emergentes de verdade.

Tarefas:

- salvar histórico de stars;
- calcular stars por hora/dia;
- coletar releases recentes;
- coletar commits e contributors recentes;
- analisar README;
- criar `repo_score`.

Resultado esperado:

```txt
detectar ferramentas novas antes de virarem óbvias.
```

---

### Fase 4 — Trend Engine

Objetivo: detectar tendências a partir de múltiplos sinais.

Tarefas:

- calcular cross-source mentions;
- calcular momentum;
- calcular novelty;
- combinar GitHub + papers + blogs + social;
- gerar `trend_score`;
- ranquear clusters.

Resultado esperado:

```txt
o sistema começa a entender o que está crescendo no ecossistema.
```

---

### Fase 5 — Papers Intelligence

Objetivo: reduzir ruído em papers e priorizar impacto.

Tarefas:

- classificar tipo do paper;
- detectar autoridade da instituição;
- detectar se há código disponível;
- correlacionar paper com GitHub;
- pontuar potencial de impacto.

Resultado esperado:

```txt
menos papers irrelevantes e mais pesquisa realmente importante.
```

---

### Fase 6 — Cross-Source Correlation

Objetivo: aumentar confiança quando múltiplas fontes apontam para o mesmo tópico.

Tarefas:

- mapear fontes por cluster;
- aplicar boost por diversidade de fontes;
- reduzir score de tópicos isolados sem autoridade;
- destacar sinais confirmados.

Resultado esperado:

```txt
tópicos com validação cruzada aparecem com prioridade.
```

---

### Fase 7 — Source Discovery Engine

Objetivo: tornar o sistema autoexpansível.

Tarefas:

- extrair organização de repos importantes;
- buscar blog/docs/site oficial;
- sugerir novas fontes;
- criar fila de revisão;
- adicionar fontes aprovadas ao sistema.

Resultado esperado:

```txt
o bot descobre novas fontes relevantes sozinho.
```

---

### Fase 8 — Knowledge Graph

Objetivo: criar memória estrutural do ecossistema de IA.

Tarefas:

- armazenar entidades;
- criar relações entre tópicos, empresas, repos e papers;
- usar grafo para novelty detection;
- usar grafo para explicar tendências.

Resultado esperado:

```txt
o sistema entende contexto histórico e conexões entre sinais.
```

---

## 23. Prioridades Recomendadas

Ordem recomendada para implementação:

1. **Formatter + JSON estruturado para Telegram**
2. **Semantic clustering**
3. **GitHub velocity scoring**
4. **Trend engine**
5. **Papers intelligence**
6. **Cross-source correlation**
7. **Source discovery engine**
8. **Knowledge graph**

Motivo: primeiro é preciso melhorar a entrega no Telegram, porque isso já aumenta o valor percebido. Depois, adicionar inteligência progressivamente no pipeline.

---

## 24. Critérios de Sucesso

O projeto será considerado melhorado quando:

- o Telegram parar de parecer dump de notícias;
- o digest tiver poucas mensagens;
- cada item tiver contexto e impacto;
- conteúdos repetidos forem agrupados;
- repos emergentes forem detectados cedo;
- papers ruins forem filtrados;
- tópicos fortes aparecerem com múltiplas fontes;
- o usuário conseguir entender o dia em poucos minutos;
- o sistema explicar “why this matters”;
- o usuário confiar que o que chegou é realmente importante.

---

## 25. Definição de Pronto para o MVP

O MVP desta evolução deve conter:

- schema JSON para análise;
- schema JSON para digest;
- `formatter.py` separado;
- agrupamento simples por embeddings;
- ranking por score final;
- digest diário consolidado;
- limite de itens enviados;
- seções fixas no Telegram;
- campo `why_it_matters` obrigatório;
- campo `worth_testing` obrigatório;
- realtime alert apenas para Tier S.

---

## 26. Observações para o Codex

Ao implementar, seguir estas regras:

1. Não misturar lógica de IA com formatação visual.
2. Não deixar o LLM gerar HTML final do Telegram.
3. Sempre preferir JSON estruturado entre etapas.
4. Manter módulos pequenos e testáveis.
5. Criar funções puras para score e ranking.
6. Adicionar logs para entender por que um item foi enviado ou descartado.
7. Garantir fallback quando JSON vier inválido.
8. Evitar chamadas desnecessárias ao LLM.
9. Fazer deduplicação antes de sumarização pesada.
10. Preservar links originais dentro dos clusters.
11. Não apagar fontes relevantes; agrupar e priorizar.
12. Criar testes para formatter, scoring e clustering.

---

## 27. Resumo Executivo

O projeto já tem uma infraestrutura forte para coleta e processamento.

Agora, o próximo salto é transformar o sistema em uma plataforma de inteligência.

O foco deve sair de:

```txt
coletar mais conteúdo
```

E ir para:

```txt
identificar sinais fortes, conectar fontes e explicar o que realmente importa.
```

A principal entrega para o usuário é um Telegram digest que funcione como uma curadoria inteligente de IA:

```txt
poucas mensagens, alto sinal, contexto claro e insights acionáveis.
```

Esse é o caminho para transformar o bot em um verdadeiro:

```txt
AI Intelligence Platform
```
