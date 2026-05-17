# AIOS Agents Registry

Machine-local source: `~/.aios/agents.json` or `$AIOS_AGENT_HOME/agents.json`.

| Agent ID | Substrate | Capabilities | Registered By |
| --- | --- | --- | --- |
| claude@myworld | claude_code | operator, reviewer, verifier | codex@myworld |
| claude_at_myworld_dev | claude_code | operator, reviewer | self-bootstrap |
| codex@CapabilityOS | codex_cli | child_agent, researcher | codex@myworld |
| codex@GenesisOS | codex_cli | critic, researcher | codex@myworld |
| codex@hivemind | codex_cli | child_agent, executor | codex@myworld |
| codex@memoryOS | codex_cli | child_agent, reviewer | codex@myworld |
| codex@myworld | codex_cli | child_agent, operator, reviewer | codex@myworld |
| test_outsider | ollama | outsider | self-bootstrap |
