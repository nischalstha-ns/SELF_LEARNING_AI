# Vena — Safety Model

What Vena can do, what it cannot do, and how permissions keep it safe.

## The short version

Vena runs **on your machine, for you**. It never phones home, never
opens a network port to the LAN, and asks before doing anything
consequential. Every consequential action is logged.

## What Vena CAN do

- **Hear and speak** — push-to-talk voice turns, text-to-speech replies.
  Playback can be interrupted at any time ("barge in").
- **Remember workflows** — record a completed multi-step task, edit it,
  dry-run it, replay it later. Replays stop at the first failure and
  can revert file changes via checkpoints.
- **Pair with your phone** — over a tunnel *you* control (Tailscale /
  `adb reverse`). The phone gets notifications and can approve/deny
  pending actions.
- **Back itself up** — online SQLite backups with one HTTP call.

## What Vena CANNOT do (hard limits)

Even if a task's instructions ask, Vena will not:

- Send Ctrl+Alt+Del, bypass the OS login/lock screen, or disable
  antivirus/firewall.
- Type, store, or read passwords, OTPs, card numbers, or API keys in
  plain text. Secrets live only in `.env` / the OS keyring — never in
  code, the database, logs, or git.
- Send email/messages, post publicly, buy anything, or permanently
  delete data without your explicit approval **for that action**.
- Run a command that isn't on the allowlist; never `shell=True`,
  `eval`, or `pickle`.
- Listen on the network: the HTTP service binds `127.0.0.1` only and
  **refuses** to start on any other address.
- Record audio without your knowledge: push-to-talk is the default;
  always-listening ("Hey Vena") requires explicit opt-in
  (`VENA_WAKEWORD_ENABLED=1`) and processes audio in small chunks that
  are discarded unless the wake phrase fires.

## Permission levels

Every tool is registered with one of four levels:

| Level | Meaning |
|---|---|
| `OBSERVE` | Look only (read state, take screenshots). |
| `SAFE` | Reversible changes. |
| `EXECUTE` | Low-risk changes the operator explicitly permitted. |
| `ELEVATED` | Consequential: mouse/keyboard, system changes — **always asks first**. |

During workflow replay, `ELEVATED` steps pause for an approver callback;
without approval the run stops as `awaiting_approval` — later steps
never execute.

## Audit & recovery

- Every replay run is recorded (`workflow_runs`): steps, results,
  timing, failures.
- File checkpoints: before a replay overwrites a file, the original is
  backed up; `POST /workflow-runs/{id}/revert` restores it.
- Dry-run mode validates every step and executes nothing.
- Pairing codes are single-use and expire in 10 minutes; only SHA-256
  hashes of codes and device tokens are stored.
- Backups sanity-check the database before restore and refuse garbage.

## Reporting a safety problem

If Vena does something it shouldn't: stop the service (Ctrl+C),
take a backup (`POST /backup`), and inspect the `workflow_runs` /
notification history to see exactly what ran.
