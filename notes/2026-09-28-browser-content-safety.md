# Browser content and LifeOS Safety hooks

On 2026-09-28, the isolated LifeOS installation registered `Safety.hook.ts` for `WebFetch`, `WebSearch`, MCP tools, and `ToolSearch`. Hermes also returns page-controlled text from native browser tools. The bridge previously kept browser tool names, so its generic PostToolUse hooks ran, but the `WebFetch` Safety registration did not.

Hermes source inspection showed that `browser_navigate` returns a compact page snapshot, `browser_snapshot` returns the accessibility tree, `browser_console` returns page console text, and `browser_get_images` returns page image URLs and alt text. Browser vision, CDP, browser script, and page dialog tools can also return page content. The bridge now lets these eight result types match `WebFetch` PostToolUse registrations. It passes `WebFetch` to that matching hook group while generic groups and transcript rows retain the original Hermes tool name. Browser actions that return only status or a URL are outside this list.

A regression with eight browser tool names failed before the change because the Safety matcher produced no context. After the change, each result reached one generic hook and one `WebFetch` hook, and the transcript kept the eight Hermes names. The `.212` plugin suite passed 110 tests with native hook paths available. A direct `.212` probe ran the installed `Safety.hook.ts` with synthetic `browser_snapshot` text containing an instruction attempt. The hook returned its external-content warning, and the transcript still named `browser_snapshot`.

The native probe did not start a browser or fetch a page. The isolated account has no configured browser service, so live browser output remains unverified.
