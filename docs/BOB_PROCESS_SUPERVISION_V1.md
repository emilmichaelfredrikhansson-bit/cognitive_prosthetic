# Bob Process Supervision V1

This document defines the local child-process lifecycle boundary for Bob V1.

## Separation of concerns

Bob has three independent concurrency layers:

1. **Repository execution** — up to 3 active runs per repository.
2. **Cognition** — at most one RUNNING cognition per run; browser capacity is separately bounded.
3. **Local process lifecycle** — `ProcessSupervisor` owns explicitly started Bob child processes.

Remote Desktop Commander is control transport, not Bob's process manager. Shell/RDC sessions must not be the durable owner of Bob API, bridge, cognition clients, tests or probes.

## Durable record

Every supervised child records:

```text
process_id
run_id
repository_id
purpose
pid
process_identity
command_class
started_at
state
owns_ports
log_path
cleanup_policy
```

## Ownership and PID reuse

PID alone is never process identity. On Windows Bob binds ownership to PID plus OS process creation time; Linux `/proc` start identity is used when available. If the current identity differs from the durable record, the process becomes `STALE_IDENTITY` and Bob refuses to signal it.

The supervisor may terminate only a process with a durable Bob record whose current identity still matches. It never kills Chrome, PowerShell, Python or any other process by name. Unknown external port owners are reported and left untouched.

## Process classes

- `LONG_LIVED_RUNTIME` — Bob API and ChatGPT bridge.
- `UNTIL_EXIT` — bounded child expected to run until its own normal completion.
- `COGNITION_CLIENT` — bounded cognition transport client.
- `TEST` — deterministic test process.
- `PROBE` — short diagnostic probe.

V1 allowlists executables at supervisor construction. Commands are argv lists rather than shell strings. Environment values are used for spawn but are not copied into durable process records.

## Ports and single-instance safety

A process may declare loopback ports it owns. Startup fails closed when any declared port is already bound. If the port belongs to another supervised record, Bob reports that owner; if the port belongs to an unknown process, Bob refuses to replace it.

This is the second-instance gate for Bob Local Companion. No supervisor action may resolve a collision by killing an unowned process.

On Windows, a virtual-environment `python.exe` may be a redirector while its child base-interpreter process owns the actual listening socket. After health succeeds, Bob therefore binds each declared port to the exact listener PID + creation-time identity and verifies that listener is the supervised root or its descendant. Shutdown verifies both root and listener identities before terminating the owned process tree. Windows liveness also requires `STILL_ACTIVE`; a terminated process object retained by an open handle is not treated as running.

## Logs and cleanup

Long-running stdout/stderr is redirected to per-process log files. Consumers read only bounded tails: V1 caps a single tail at 256 KiB and 1,000 lines, with much smaller defaults.

Completed `TEST` and `PROBE` children can be reaped explicitly. Durable records are retained after reaping for observability. Dirty or unknown external state is not silently deleted.

## Restart semantics

Supervisor state is durable JSON written atomically under `.bob/runtime/`. On restart, every previously active record is compared with current OS process identity:

- matching live identity stays `RUNNING`;
- dead long-lived runtime becomes `FAILED`;
- dead bounded child becomes `EXITED`;
- reused/stale PID becomes `STALE_IDENTITY`.

There is no automatic restart loop in V1. `restart_count` remains explicit evidence; recovery is operator/orchestrator-driven and bounded.

## Bob Local Companion

`bob_local.py` is the lifecycle parent. It starts Bob API and ChatGPT bridge through `ProcessSupervisor`, records repository ownership and expected ports, waits for health, monitors durable state and stops only those owned children during shutdown.
