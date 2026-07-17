---
name: ask-claude
description: Run a read-only Claude CLI question or architecture plan against an explicit repository directory. Use for independent code review, plan critique, failure-mode analysis, or a second opinion that must not modify the working tree.
---

# Ask Claude

Use `scripts/ask_claude.py` when the `claude` CLI is installed and authenticated. The wrapper always uses read-only plan permissions and never enables unattended write access.

```bash
python3 __harness/skills/ask-claude/scripts/ask_claude.py \
  --mode plan \
  --dir . \
  'Review the ChatKit and design-state boundary. Cite the files you used.'
```

Include enough context in the prompt for a headless reviewer. Verify every cited path and test claim before adopting the response.
