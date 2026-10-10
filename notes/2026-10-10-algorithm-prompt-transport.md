# Algorithm overview argument overflow

The installed synthetic profile generates its file cards, then fails to generate the overview. The first job returns exit code 2 after 530.862 seconds. A repeat preserves 24 cards and fails after 11.091 seconds. The native command reports only `Algorithm summaries unavailable`.

A diagnostic copy retains the actual native implementation and prints the caught exception. The exception is `E2BIG: argument list too long, posix_spawn 'bun'`. The stack points to the overview inference call. The copy is removed after observation, and the selected native source stays unchanged. Increasing the owner-job deadline cannot fix this exception.

The Algorithm module passes both prompts as individual arguments to the Inference command. Linux limits the size of each argument. The shared exported inference function already sends the user prompt through standard input. It stores a large system prompt in a private temporary file and removes that file after the child finishes.

The correction calls that existing function from the Algorithm module. It preserves the requested low or high level, the existing timeout, failed-inference handling, and trailing-note removal. The model mapping and the current source and owner checks stay in place. The native patch applies after the existing 23 patches.

The transport test uses real processes and a diagnostic child that reads complete inputs and returns exit code 7. It does not return model output. Before the correction, the 200,000-byte ASCII user prompt, 180,000-byte UTF-8 user prompt, and 200,000-byte system prompt all fail with E2BIG. After the correction, all three inputs reach the child intact. The large system prompt file no longer exists when the request ends. This unit test does not prove model success. Actual installed model generation and neighboring lifetime tests remain separate checks.

The first neighboring test invocation uses the system Python without httpx and a fresh native source without its existing YAML dependency tree. It fails before useful application validation. The corrected invocation reuses the existing test virtual environment and the locked native dependencies. The original output remains evidence of the failed invocation.
