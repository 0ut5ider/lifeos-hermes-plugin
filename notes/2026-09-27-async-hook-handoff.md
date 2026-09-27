# 2026-09-27: An async hook lost its input when Hermes exited

The bridge originally launched an async hook with a pipe and fed it from a daemon thread. A one-shot Hermes process can exit while that thread is blocked writing. A test made the hook wait 200 milliseconds before reading a one-megabyte prompt, then ended the parent with `os._exit(0)`. The hook never produced its completion marker.

The bridge now writes each async request to a mode-0600 file inside a mode-0700 transcript directory. It launches a detached Python runner with only the file path in its arguments. The runner reads and removes the file, then executes the native hook with a timeout. The same test now receives all 1,048,576 prompt characters after the parent exits.

This proves survival across a normal one-shot parent exit. It does not prove survival when a service manager kills the whole control group. Async hook output remains outside the model context, as in the previous bridge behavior.
