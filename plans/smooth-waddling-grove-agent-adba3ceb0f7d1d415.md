# Plan: Fetch and Document 25 BitMEX API Endpoints

## Goal
Use WebFetch to read 25 BitMEX API documentation pages and compile a structured document with all endpoint details.

## Execution Steps

### Step 1: Fetch all 25 pages in parallel batches
WebFetch can be called in parallel. I'll batch them into groups of ~5 to avoid overwhelming:

**Batch 1 (Execution/Trading - 6 pages):**
1. https://docs.bitmex.com/zh-CN/api-explorer/get-execution
2. https://docs.bitmex.com/zh-CN/api-explorer/get-execution-trade-history
3. https://docs.bitmex.com/zh-CN/api-explorer/get-execution-history
4. https://docs.bitmex.com/zh-CN/api-explorer/get-quote-fill-ratio
5. https://docs.bitmex.com/zh-CN/api-explorer/get-trading-volume
6. https://docs.bitmex.com/zh-CN/api-explorer/get-volume-rank

**Batch 2 (Market/Instruments part 1 - 6 pages):**
7. https://docs.bitmex.com/zh-CN/api-explorer/get-funding
8. https://docs.bitmex.com/zh-CN/api-explorer/get-instruments
9. https://docs.bitmex.com/zh-CN/api-explorer/get-active-instruments
10. https://docs.bitmex.com/zh-CN/api-explorer/get-indices-instruments
11. https://docs.bitmex.com/zh-CN/api-explorer/get-active-and-indices-instruments
12. https://docs.bitmex.com/zh-CN/api-explorer/get-active-intervals

**Batch 3 (Market/Instruments part 2 - 6 pages):**
13. https://docs.bitmex.com/zh-CN/api-explorer/get-composite-index
14. https://docs.bitmex.com/zh-CN/api-explorer/get-instrument-usd-volume
15. https://docs.bitmex.com/zh-CN/api-explorer/get-insurances
16. https://docs.bitmex.com/zh-CN/api-explorer/get-liquidation
17. https://docs.bitmex.com/zh-CN/api-explorer/get-quote
18. https://docs.bitmex.com/zh-CN/api-explorer/get-quote-bucketed

**Batch 4 (Market/Instruments part 3 + Orderbook - 7 pages):**
19. https://docs.bitmex.com/zh-CN/api-explorer/get-settlements
20. https://docs.bitmex.com/zh-CN/api-explorer/get-stats
21. https://docs.bitmex.com/zh-CN/api-explorer/get-stats-history
22. https://docs.bitmex.com/zh-CN/api-explorer/get-stats-history-usd
23. https://docs.bitmex.com/zh-CN/api-explorer/get-trade
24. https://docs.bitmex.com/zh-CN/api-explorer/get-trade-bucketed
25. https://docs.bitmex.com/zh-CN/api-explorer/get-market-data

### Step 2: For each page, extract
- Category (Execution/Trading, Market/Instruments, Orderbook)
- HTTP Method + Path
- Description
- ALL parameters: name, type, required/optional, description
- Response fields
- Any notes or warnings

### Step 3: Compile into structured document
Output everything as a well-organized document, grouped by category.

## Output
The final output will be directly in the conversation response, formatted as a structured reference document.

## Notes
- These are public API doc pages, should be accessible without auth
- The prompt for WebFetch should ask for ALL details to ensure nothing is missed
- If any page fails or redirects, retry or note the failure
