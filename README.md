# Company Intel

A multi-agent system that researches a company from its SEC filings, financials
and hiring signals, and evaluates it against your own goals through a **lens**
(a profile file). Phase 1 ships the job-seeker lens.
一个多智能体系统：从公司的 SEC 文件、财务数据和招聘信号中研究一家公司，并通过一个**视角（lens）**按你自己的目标进行评估。第一阶段先做"求职者视角"。

See [`docs/decision-log.html`](docs/decision-log.html) for the design decisions
and milestone progress. · 设计决策与里程碑进度见 `docs/decision-log.html`。

## Status · 状态

**Milestone 1 — SEC ingest.** Pulls filings and XBRL financials for seed
companies into Postgres. No agents yet (those arrive at Milestone 3).
**里程碑 1 —— SEC 数据采集。** 将种子公司的文件与 XBRL 财务数据采集进 Postgres。暂无智能体（里程碑 3 才加入）。

## Quickstart · 快速上手

```bash
cp .env.example .env          # then set SEC_USER_AGENT to "Your Name you@example.com"
pip install -e ".[dev]"       # install the package and dev tools
docker compose up -d          # start Postgres 16 + pgvector
company-intel init-db         # create tables and the read-only role
company-intel ingest STX MU GRAB SE   # ingest filings + financials
company-intel facts STX       # print the last 3 fiscal years of revenue & R&D
```

Run the tests with `pytest` (no database required — HTTP is mocked and parsing
uses fixtures). · 运行测试：`pytest`（无需数据库，HTTP 已 mock，解析使用 fixtures）。

## Layout · 结构

```
src/company_intel/
  config.py            settings from .env
  cli.py               company-intel init-db | ingest | facts
  ingest/
    sec_client.py      polite SEC client (rate limit, retries, cache)
    xbrl.py            companyfacts -> normalized financial facts
    filings.py         10-K / 20-F HTML -> item sections
  store/
    schema.sql         tables + read-only role
    db.py              Postgres access layer
tests/                 unit tests (sec_client, xbrl, filings)
```

## Notes · 说明

- **SEC etiquette.** `SEC_USER_AGENT` must contain your name and email; requests
  are rate-limited under 10 req/s and cached to disk. · `SEC_USER_AGENT` 必须含姓名与邮箱；请求限速低于 10 次/秒并落盘缓存。
- **CLI tickers.** `ingest` takes tickers as positional arguments
  (`company-intel ingest STX MU`). · `ingest` 以位置参数接收股票代码。
- **Not financial advice.** Every claim is sourced; the system refuses to
  predict prices. · 非投资建议；每条结论都有来源，系统拒绝预测价格。
