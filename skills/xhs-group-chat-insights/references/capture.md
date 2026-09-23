# Capture and topic extraction

Use the bundled read-only wrapper and setup script. Do not recreate platform API calls.

## Runtime

- Default runtime: `~/.local/share/xhs-group-chat-insights/Spider_XHS`
- Default Cookie: `~/.config/xhs-group-chat-insights/xhs-cookie.txt`
- CLI: `<skill-dir>/scripts/xhs_group_tool.py`

Environment variables or explicit CLI arguments can override both paths. If the runtime or authentication is missing, read [setup.md](setup.md). Run `doctor` before the first live operation when readiness is uncertain. Never display Cookie contents.

```bash
python3 <skill-dir>/scripts/xhs_group_tool.py doctor
```

## Full export

```bash
python3 <skill-dir>/scripts/xhs_group_tool.py \
  group-chat --chat-url 'USER_SUPPLIED_GROUP_URL_OR_ID' \
  --output-dir /abs/task-output/chat-exports \
  --max-pages 1000
```

The output root contains `<group_id>/messages.json`, `messages.csv`, and `checkpoint.json`.

## Resume and incremental update

- Use `--resume` to continue an incomplete export from its checkpoint.
- Use `--update` to fetch new pages until known messages appear, then merge and deduplicate.
- Use `--overwrite` only when the user explicitly asks for a fresh replacement.
- Never combine these three modes.

After capture, verify:

- declared and actual message counts agree;
- `store_id` values are unique;
- JSON parses;
- earliest and latest timestamps are plausible;
- `checkpoint.completed` accurately records whether pagination reached its natural end;
- an update reports both newly added and total messages.

Newly created private export files should be mode `600` and directories mode `700`. Audit permissions after capture. If the user supplied an existing export with broader permissions, warn about it instead of silently changing the file.

## Extract group topics

Topic extraction is offline and does not require authentication:

```bash
python3 <skill-dir>/scripts/xhs_group_tool.py \
  group-topics --messages-json /abs/group/messages.json \
  --output-dir /abs/group/topics
```

Outputs include unique topic definitions, member topic submissions, direct-reply state, topic-related original messages, and directly-unreplied member submissions.

Use `--unreplied-only` only when the user requests that filter. It applies to member topic posts, not topic-definition cards or ordinary comments. Report complete-source totals separately from selected/filter totals.
