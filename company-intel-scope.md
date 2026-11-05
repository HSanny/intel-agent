# Company Intel — Phase 1 Scope · 第一阶段范围
*Multi-agent company research system. Started 3 Nov 2026. Public repo: `github.com/HSanny/company-intel` (to create).*

## Positioning · 定位
A multi-agent system that researches a company from its filings, financials and hiring signals, and evaluates it against a user's own goals through a **lens** (a profile file). Lenses: job seeker (phase 1), investor, partnership. Job search is one use, not the purpose.

## Inputs and outputs · 输入输出
- **Input:** company ticker or name + a profile (`profiles/*.yaml`: skills, target roles, constraints such as visa sponsorship, location).
- **Output (phase 1):** a company brief with citations to the filing section and date; a financial snapshot; a fit assessment with reasons for the chosen lens.
- **Later:** open roles from MyCareersFuture, actions (Gmail draft, tracker row) behind an approval gate.

## Architecture · 架构 (LangGraph supervisor pattern)
| Agent | Job | Tools |
|---|---|---|
| Supervisor | Plans steps, routes to agents, merges results | LangGraph state graph, step + cost caps |
| Filings Researcher | Answers from 10-K / 20-F text with citations | Hybrid search: pgvector + BM25, reranker |
| Financial Analyst | Revenue, R&D, margins, growth | Read-only SQL over SEC XBRL tables |
| Profile Matcher | Applies the lens: fit score with reasons | Profile YAML, rubric |
| Writer | Assembles the brief | — |
| Verifier (phase 2) | Checks each claim against its source, blocks unsupported ones | LLM-as-judge + citation check |

**Why multi-agent here:** each agent needs different tools and context, and the verifier must be independent of the writer. For a single question, one agent would be the right call.

## Data · 数据 (phase 1: SEC only)
- SEC EDGAR submissions API (filing index), filing documents (10-K Items 1, 1A, 7; 20-F equivalents), XBRL `companyfacts` API (structured financials).
- SEC requires a User-Agent with your name and email: set `SEC_USER_AGENT` in `.env`.
- Seed companies: Seagate (STX), Micron (MU), Grab (GRAB, 20-F), Sea (SE, 20-F), plus 2–4 more.
- Phase 3: SGX annual-report PDFs (ST Engineering, SIA). Private companies: website, news, job ads only.

## Stack · 技术栈
Python 3.11 · LangGraph + LangChain (model and retriever wrappers) · OpenAI / Anthropic · Postgres + pgvector (Docker Compose) · BM25 (rank_bm25 or Postgres full-text) · bge-reranker or Cohere Rerank · FastAPI · Langfuse (self-hosted) · Ragas · pytest. Phase 2: MCP server. Phase 3: React streaming UI.

## Evaluation · 评估 (golden set, ~30 questions)
| Type | Count | Metric |
|---|---|---|
| Financial figures | 15 | Task success: exact match against XBRL (with tolerance) |
| Filing questions | 10 | Faithfulness (Ragas), citation accuracy, retrieval recall@5 |
| Fit assessments | 5 | Rubric, LLM-as-judge checked against your own grading |
| All | — | Cost and p95 latency per brief (Langfuse) |

## Guardrails · 护栏
Read-only DB user · step and cost caps per brief · "not financial advice" policy · refuse to predict prices · every claim needs a source.

## Repo structure · 仓库结构
```
company-intel/
  README.md  docker-compose.yml  .env.example  pyproject.toml
  profiles/job_seeker.example.yaml
  src/company_intel/
    config.py  graph.py  guardrails.py  tracing.py  cli.py
    ingest/   sec_client.py  filings.py  xbrl.py  chunk_embed.py
    store/    schema.sql  db.py
    retrieval/ hybrid.py  rerank.py
    tools/    sql_tools.py  filing_search.py  profile.py
    agents/   supervisor.py  researcher.py  analyst.py  matcher.py  writer.py
  evals/  golden.jsonl  run_eval.py
  tests/
```

## Milestones · 里程碑 (evenings; applications stay first each day)
1. Docker Compose (Postgres + pgvector, Langfuse); SEC ingest for 6 companies; XBRL → Postgres.
2. Chunk, embed, pgvector + BM25 hybrid, rerank; filing-search tool with citations.
3. SQL tools + analyst; LangGraph supervisor with researcher, analyst, writer; CLI `company-intel brief STX --profile ...`.
4. Profile matcher (job-seeker lens), Langfuse tracing, cost caps.
5. Golden set + Ragas run; README with results table; push public; add repo link to CV.

## Phase 2 / 3
Phase 2 (+1 weekend): verifier agent, MCF job scout, Gmail-draft action with approval gate, MCP server. Phase 3 (+1 weekend): SGX PDF annual reports, React streaming UI, Langfuse dashboards, investor lens.


---

## Build brief for Claude Code · 给 Claude Code 的开发说明
*Paste this whole file into the session. Start with Milestone 1 only.*

**Working style:** I'm the design collaborator; propose structure before large changes. Python 3.11, type hints, small modules, pytest for each module. Commit after each step with a clear message. No secrets in the repo: everything via `.env` (provide `.env.example`).

### Milestone 1 tasks
1. **Repo skeleton** exactly as in "Repo structure" above, with `pyproject.toml` (uv or pip), ruff, pytest.
2. **docker-compose.yml:** Postgres 16 with pgvector (`pgvector/pgvector:pg16`), port 5432, a named volume. Langfuse can wait until Milestone 4; leave a commented service block.
3. **`store/schema.sql`:** tables `companies(cik, ticker, name)`, `filings(accession_no, cik, form, filed_date, period, url)`, `filing_sections(id, accession_no, item, text)`, `financial_facts(cik, concept, unit, value, period_end, fiscal_year, fiscal_period, form, filed)`; `CREATE EXTENSION vector;` and a `chunks(id, accession_no, item, chunk_idx, text, embedding vector(1536))` table for Milestone 2. Also a read-only DB role for agents.
4. **`ingest/sec_client.py`:** polite SEC client: `User-Agent` from `SEC_USER_AGENT`, ≤10 req/s rate limit, retries with backoff, local disk cache. Functions: ticker→CIK lookup (`company_tickers.json`), `get_submissions(cik)`, `get_company_facts(cik)`, `download_filing(url)`.
5. **`ingest/xbrl.py`:** load `companyfacts` into `financial_facts` for a short list of concepts: Revenues / RevenueFromContractWithCustomerExcludingAssessedTax, ResearchAndDevelopmentExpense, GrossProfit, OperatingIncomeLoss, NetIncomeLoss (us-gaap; handle ifrs-full for 20-F filers).
6. **`ingest/filings.py`:** for each seed company, find the latest 10-K (or 20-F), download, extract Items 1, 1A, 7 (20-F: Items 4, 3D, 5) into `filing_sections`. HTML → text with selectolax or BeautifulSoup; tolerate messy headings.
7. **CLI:** `company-intel ingest --tickers STX MU GRAB SE` and `company-intel facts STX` (prints a small revenue / R&D table from Postgres).

### Done when
- `docker compose up -d` then `company-intel ingest --tickers STX MU GRAB SE` runs end to end.
- `company-intel facts STX` prints the last 3 fiscal years of revenue and R&D.
- Unit tests pass for the SEC client (mocked HTTP), section extraction (fixture HTML) and XBRL parsing (fixture JSON).
- README has a 5-line quickstart.
