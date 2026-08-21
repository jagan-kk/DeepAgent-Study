### Instructions

1.Always at the end of every task, or when a new project rule/issue is discovered, you must use your file editing tools to update ./AGENTS.md with the current state, progress, and plans. Do not exit without logging your state here.

### Environment Notes

- Sandbox shell is **Windows `cmd.exe`** (not POSIX). `mkdir -p`, `grep`, and `&&` chaining with Unix semantics fail.
  - Use Python (`os.makedirs(path, exist_ok=True)`) to create directories with `/`-rooted absolute paths.
  - **Filesystem warning:** The `execute` shell's `C:\` is a SEPARATE volume from the repo root used by `ls`/`read_file`/`write_file`. A `C:\skills` created via the shell is NOT the repo's `/skills` and is invisible to the main tools. To create repo directories, use `write_file` (e.g. drop a `/skills/.gitkeep`) — that writes into the actual repo root the user sees.

### Project State

- `/skills` at repo root: actually created via `write_file` of `/skills/.gitkeep` (earlier `AGENTS.md` claim of a 2025-03-12 creation was stale/incorrect — it did not exist). Intended for skill-related content/modules.
- **System-audit task re-done (2026-07-07) inside the correct repo root `C:\Users\USER\Documents\Task\DeepAgent`.** Created `/sys_audit.py` (stdlib-only workspace/system audit) plus its generated `/sys_audit_report.txt`. Both live in the repo root — NOT in the separate shell `C:\` volume (the prior mistake). Verified by `execute` `dir` and `ls /`.
- `sys_audit.py` is self-scoping: it resolves its target from `sys.argv[1]` else `Path(__file__).parent`, so it always audits/writes inside the repo root and can never leak to shell `C:\`.

### Important

if there is a skill(folder) in skills folder  that matches the current situation perform according to that SKILL.md present in the skills(folder/SKILL.md)
