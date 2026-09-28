# Image prompt hook shape

Date: 2026-09-27. Target: isolated `lifeos-hermes@192.168.8.212` account.

Claude Code v2.1.272 received one user message through its stream JSON input with a text block, a one-pixel PNG image block, and a second text block. A temporary `UserPromptSubmit` hook captured `prompt: "First sentence.\nSecond sentence."`. The hook blocked the synthetic prompt before any model call. The CLI exited zero without stderr.

The bridge's regression test uses Hermes's `image_url` block between the same two text blocks. Its `UserPromptSubmit` hook captured the same prompt string. The image data remained in the bridge transcript. This verifies text extraction and separator placement for that three-block case. A second native probe with only an image block captured an empty prompt string and exited zero. The bridge also supplies an empty string for an image-only prompt, as a separate child-process test confirms. Other attachment formats and pasted content markers have not been compared to the native CLI.
