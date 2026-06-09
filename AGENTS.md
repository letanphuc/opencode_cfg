# Memory

You have access to `npx kratos-memory` for persistent, cross-session memory. Use it proactively — the goal is that any context you discover should never need to be rediscovered.

## Before starting any task

Always search kratos-memory for relevant context:

```
npx kratos-memory search "<query>" --json
```

Also check recent memories and project summary:

```
npx kratos-memory recent --limit 10 --json
npx kratos-memory summary --json
```

## During work

Save important observations as you go. Do NOT batch saves at the end — save in real time as you learn:

```
npx kratos-memory save "<what you learned>" --tags <tag1,tag2> --importance <1-5>
```

### What to save

- Architecture decisions and rationale (why X over Y)
- Codebase conventions, patterns, naming rules
- Bug root causes and fixes
- User preferences, constraints, or requirements
- API endpoints, auth flows, environment setup
- File structure discoveries, key files and their roles
- Anything you would want to know next session

### Tag conventions

Use these tags: `architecture`, `convention`, `config`, `bug`, `api`, `auth`, `database`, `frontend`, `deployment`, `testing`, `dependency`, `pattern`, `workaround`, `security`

### Importance

- 5: Critical — project fundamentals, auth, secrets setup
- 4: Important — architecture decisions, key patterns
- 3: Useful — conventions, common workflows
- 2: Notes — minor observations, tips
- 1: Trivia — ephemeral or low-value context

## When switching projects

If the user works in a different directory, run:

```
npx kratos-memory switch <path>
```

Then search memories for that project before starting.

## Never forget

- Never skip the search step at the start of a session
- Never batch saves — save immediately after learning
- kratos-memory is local-only, zero network, always available — use it
