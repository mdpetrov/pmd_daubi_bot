# Project agent workflow

For user-requested implementation tasks, delegate to these three subagents. Give each agent the task context and tell them how to contact the others.

- `implementation` owns the code changes requested by the user. Keep the change focused, run relevant checks, and address reproducible findings from `testing`.
- `testing` checks the implementation through its normal entry points and runs the relevant test suite. Send reproducible failures directly to `implementation` with expected and actual behavior. Retest after fixes and report any remaining gaps. Leave production edits to `implementation`.
- `process_review` reviews how the change fits the project, flags workflow and integration risks, and suggests practical optimizations. Share findings with the other agents and leave implementation to the designated agent.

The coordinating agent resolves conflicting findings, verifies the final changes, and reports the outcome to the user.
