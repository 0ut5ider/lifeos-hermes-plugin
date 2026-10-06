# Web extraction status

The live Hermes web corpus test passed ordinary and injection-shaped search results. Extraction returned a document with content and `error: null`, but LifeOS produced zero Safety hook calls. The Hermes display and guardrail classifiers searched the first 500 result characters for an `"error"` key. The successful extraction therefore became a failure event and bypassed the PostToolUse safety registration.

Three classifier regressions failed: a null error on a successful result, document text with error-like keys, and a mixed result containing one successful page. The structured extraction classifier now checks execution fields and successful content independently of document text. Both classifiers use that decision. Complete extraction failure remains a failure.

The HTTP fixture uses Hermes's actual provider interface, actual search and extract tools, installed plugin middleware, and private FlashNext generation. Its provider serves a small document corpus. It does not emulate Firecrawl or establish a native Claude Code web dispatch. The provider implementation follows the pinned extraction dispatcher, which expects a list, rather than the developer guide's conflicting success-envelope example.
