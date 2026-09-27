description: Clone recurring asset maintenance and complete the original active maintenance with safety confirmations
agent: agent
---

Inputs

- Asset description: {{asset_description}}
- Maintenance description: {{maintenance_description}}
- Expected completion date (natural language): {{expected_date_natural_language}}

Task
Use the workspace MCP server configuration for the assets system to find the target asset, inspect only uncompleted maintenance records, match the maintenance using the maintenance description input, and then create a follow-up maintenance while completing the original active maintenance.

VS Code MCP connection requirements

- First look for the workspace MCP config at `.vscode/mcp.json`.
- Prefer the MCP server whose URL matches `https://assets.<domain>`.
- If the matching MCP server defines `inputs`, rely on VS Code to prompt for those values. Do not ask the user to paste the bearer token into chat.
- start the server connection in VS Code and wait for the connection to be established before making any MCP calls.
- Before making any asset calls, ensure the MCP server is connected in this chat session. If VS Code needs approval, token input, or reconnect confirmation, explicitly tell the user to complete the VS Code prompt and wait until the MCP connection is available.
- If no matching MCP config exists in the workspace, ask the user to provide or create it before continuing.

Required workflow

1. Find the MCP configuration in the workspace that connects to `https://assets.<domain>`.
2. Show the matching MCP server name and URL to the user, then ask for confirmation before making MCP calls.
3. If VS Code presents an MCP approval or credential prompt, pause and instruct the user to complete that prompt in VS Code before continuing.
4. Once confirmed and connected, search assets using the asset description input.
5. Always confirm the exact asset with the user before continuing.
6. If there is more than one matching asset, present a numbered list and ask the user to choose one.
7. After asset selection, list only uncompleted maintenances for that asset.
8. Use the maintenance description input to match the correct uncompleted maintenance. Show the candidate(s) to the user and ask for confirmation if there is more than one plausible match.
9. Never select a completed maintenance as the original maintenance. Exclude completed records from matching and from the original-selection process.
10. Treat `expected_completion_date` and `completed_at` as separate fields. `expected_completion_date` is never relevant to completion status, maintenance matching, or eligibility. Use `completed_at` to determine whether a maintenance is completed: a non-null value means completed, and a null value means uncompleted.
11. If there are no uncompleted maintenances for the selected asset, stop and ask the user to confirm whether they want to create a new maintenance instead of trying to clone an existing one.
12. If the user confirms creating a new maintenance, create the follow-up maintenance by copying the relevant details from the matched maintenance, but leave cost blank and supplier blank.
13. Interpret the expected date input as natural language (example: `in 6 months`) and set expected completion date from today. This user-provided date is the only use of expected completion date in this workflow; never use an existing maintenance's `expected_completion_date`.
14. Only after successful creation, complete the original active maintenance.
15. Return a concise summary with asset id, original maintenance id, new maintenance id, and expected completion date.

Safety rules

- Do not ask the user to paste bearer tokens, passwords, or other secrets into chat. Secrets must be entered only through VS Code input prompts tied to the MCP configuration.
- Do not make direct HTTPS API calls; use only the configured MCP server.
- Do not create or complete any maintenance until the user confirms the selected MCP server and the selected asset.
- If the MCP server is not connected yet, stop and ask the user to finish the VS Code connection prompt first.
- Do not create or complete any maintenance until the user confirms the selected asset.
- Never select a completed maintenance as the original. Completed maintenance records are not eligible.
- If input is ambiguous, ask a clarifying question instead of guessing.
- If no asset matches, report that and ask for a refined asset description.
- If no uncompleted maintenance matches the maintenance description, stop and ask the user to confirm whether to create a new maintenance instead of continuing with a completed or irrelevant record.
- If the user does not confirm creating a new maintenance, stop without creating or completing anything.
