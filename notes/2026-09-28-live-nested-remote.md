# Live nested tool calls in Docker and SSH

On 2026-09-28, the isolated `.212` Hermes source and installed LifeOS plugin passed live `execute_code` probes against disposable Docker and SSH workspaces.

The Docker test used the cached `composer:2.8` image. A synthetic file existed only in the container workspace. An inner `hermes_tools.read_file` returned its marker, and the outer session's LifeOS transcript contained a `Read` tool row. The test removed the container and temporary Docker socket access afterward.

The SSH test used a loopback SSH connection to a disposable project directory. It created a temporary SSH key, added the public key to the test account, and removed both key and authorization afterward. An inner `hermes_tools.read_file` returned the remote file marker, and the outer session's LifeOS transcript contained a `Read` tool row. The test removed the project directory afterward.

The committed optional regressions are `test_nested_execute_code_read_uses_container_and_outer_session` and `test_execute_code_inner_read_uses_ssh_workspace_and_outer_session`. They require the Hermes source, installed plugin, and explicit Docker image or SSH fixture configuration. This verifies the inner Read path and session ID on `.212`. It does not verify other inner tools or a separate SSH host.
