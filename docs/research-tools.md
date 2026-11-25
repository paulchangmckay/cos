# Research tool ladder

Research agents use several search and read tools. Credits are limited. Use the cheapest tool that works, and move down the ladder on failure.

## Ladder (search, then read)

| Step | Search | Read | Cost |
|------|--------|------|------|
| 1 | `WebSearch` | `WebFetch` | free |
| 2 | Jina `search_web`, `search_arxiv`, `search_ssrn` | Jina `read_url` with `question` set | free tier |
| 3 | Tavily `tavily_search` | Tavily `tavily_extract` on 1 to 2 URLs | free tier |
| 4 | Firecrawl `firecrawl_search` | Firecrawl `firecrawl_scrape` | scarcest; last |

Use `search_arxiv` and `search_ssrn` first for papers.

## Caps per sub-question

- At most 4 searches and 6 page reads, counted across all tools combined. Stop when the budget is spent; record what is unresolved as a low-confidence claim or an open question, not another call.
- Stop early only after the minimum below is met and two independent sources answer the sub-question.
- Use Firecrawl only for a page steps 1 to 3 could not read (JS-heavy, blocked, PDF).
- Never set `scrapeOptions` on a search. Never call crawl, agent, research, or interact tools.
- Pass `question` to Jina `read_url` so only the relevant passages return.

## Minimum tool mix

The cap must never push a worker onto built-in tools alone. Unless every non-built-in tool is in `exhausted_tools`:

- At least one search goes through a non-built-in tool (Jina, Tavily, or Firecrawl).
- At least one page read goes through a non-built-in tool.
- The cost order above decides which tool to use for the remaining calls. It does not excuse skipping the minimum.

Cover three query types per sub-question, within the 4-search cap: an overview query, a primary-source or data query, and a counter-argument or criticism query.

## Failure handling

1. A credit, quota, rate-limit, or auth error means the tool is exhausted. Do not retry it.
2. Add the tool name to `exhausted_tools` in your worker state file.
3. Continue with the next step on the ladder.
4. Skip any tool already listed in `exhausted_tools` in `state.json`.
5. If every tool fails for a source, record the claim as `search-only` with `confidence: low`.

A page-not-found or paywall error is not exhaustion. Try the next reader for that URL only.
