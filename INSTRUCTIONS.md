# ContextHub Codex Instructions

## Goal

Implement ContextHub incrementally according to the project
documentation. Favor correctness, maintainability, and clean
architecture over speed.

------------------------------------------------------------------------

## Read Order

Before starting any implementation task, read the documents in this
order:

1.  `00_Project_Overview.md`
2.  `01_System_Architecture.md`
3.  `02_Data_Model.md`
4.  `03_Technical_Design.md`
5.  `04_Implementation_Plan.md`

------------------------------------------------------------------------

## Source of Truth

When documentation overlaps, use the following precedence:

1.  **04_Implementation_Plan.md** --- defines **what** phase to
    implement.
2.  **03_Technical_Design.md** --- defines **how** each component should
    be implemented.
3.  **02_Data_Model.md** --- defines the domain models and contracts.
4.  **01_System_Architecture.md** --- defines system boundaries and
    component interactions.
5.  **00_Project_Overview.md** --- defines project goals and scope.

Do not invent a different architecture unless explicitly instructed.

------------------------------------------------------------------------

## Working Rules

-   Implement only the requested phase.
-   Do not implement future phases.
-   Preserve existing interfaces unless the documentation requires a
    change.
-   Do not introduce libraries or frameworks that are not part of the
    approved design.
-   Keep domain models independent of infrastructure.
-   Keep application services dependent on abstractions rather than
    concrete implementations.
-   When requirements are ambiguous, explain the ambiguity before coding
    instead of guessing.

------------------------------------------------------------------------

## Before Coding

Summarize:

-   the requested phase;
-   assumptions;
-   files expected to change.

------------------------------------------------------------------------

## After Coding

Report:

-   files created or modified;
-   commands executed;
-   tests executed;
-   deviations from the specification;
-   remaining work for the current phase.

------------------------------------------------------------------------

## Quality Gates

Run (when applicable):

``` bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
docker build .
```

Testing must not require hosted LLM calls or production credentials.

------------------------------------------------------------------------

## Version 1 Constraints

Unless a later phase explicitly introduces them, do **not** add:

-   LangChain
-   LlamaIndex
-   Chroma
-   Pinecone
-   PostgreSQL
-   Agents
-   Authentication
-   Runtime document uploads
-   Cloud infrastructure

Stay within the documented Version 1 architecture.
