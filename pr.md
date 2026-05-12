## Summary
- Added support for private VPC network attachments in Vertex AI Agent Engine deployments.
- Updated the python `deploy.py` template to support Click options for `--network-attachment`, `--vpc-network`, and `--dns-peering-domains`.
- Updated the base python `Makefile` template `deploy` target to accept and pipe through environment or command-line variables (`NETWORK_ATTACHMENT`, `VPC_NETWORK`, and `DNS_PEERING_DOMAINS`).
- Regenerated standard regression baseline makefile snapshots and hashes for tests verification.

## Solution
- Imported standard Vertex AI PSC attachment models (`PscInterfaceConfig` and `DnsPeeringConfig`) inside `deploy.py`.
- Constructed and passed the `psc_interface_config` configuration into standard and real-time (`adk_live`) `AgentEngineConfig` instantiations if `--network-attachment` is supplied.
- Piping the new variables inside the python `Makefile` template is completely backwards-compatible and maintains public/standard deployments out-of-the-box.

## Testing
- [x] Tested combination: `adk,agent_engine`
- [x] Tested alternate: `adk_live,agent_engine`
- [x] Tested alternate: `adk,cloud_run` (regression unit tests passing)
- [x] Makefile and CLI unit test suite fully PASSED (all 498 unit test cases verified)
