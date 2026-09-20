---
name: python-style
description: Lance's Python design philosophy — deep modules, minimal caller knowledge, sensible defaults, errors-out-of-existence, general-but-not-generic, strategic-over-tactical (Ousterhout's "A Philosophy of Software Design"), composition over inheritance (Hynek Schlawack's "Subclassing in Python Redux"), consistent type-hinted return types (functools.singledispatch over Union, Pydantic for explicit/validated data mindful of overhead, frozen dataclasses for trusted high-volume data), DRY/single-source-of-truth via constants and enums, and terse high-signal docstrings/comments. Use this whenever writing, editing, refactoring, or reviewing Python code — function/class/module design, "review this code", "refactor this", "write a function/class for X" — even if the user doesn't explicitly ask for style or design guidance. Applies by default to any Python authored in this conversation.
---

# Python Style: deep, composed, terse

Five defaults for Python code, in priority order. Apply them by default when
writing code; check for them when reviewing. They're defaults, not laws — see
"Pragmatism" at the end.

Underlying all of them: write **strategically**, not tactically — a bit of
extra design effort now (a cleaner interface, one more level of hiding) to
keep the codebase simple later, rather than the fastest thing that makes
today's task pass. This is a bias, not a blank check for gold-plating —
weigh it against Pragmatism, below, same as everything else here.

## 1. Deep modules, not shallow ones

From Ousterhout: complexity is the real enemy, and the best defense is a
**deep** module — a simple interface hiding real work — over a **shallow**
one, where the interface is nearly as complicated as what's behind it.

- A class or function earns its existence by hiding something (a data
  structure, an edge case, a protocol) behind a small, obvious interface.
- Watch for pass-through methods/classes that just forward a call and add
  no value — that's a sign the abstraction is shallow and should probably
  be inlined or merged with its caller/callee.
- It's fine — often better — for a function to be a bit more complex
  internally if that keeps every caller simple. Push complexity down and
  in, not up and out to callers.
- Minimize what a caller needs to know to use something correctly, not just
  what they need to *type*. A function with 6 required parameters is
  costly to call even with full type hints — give configuration knobs
  sensible defaults so the common case is a short call, and the rarely-
  changed parameters recede into the signature rather than crowding it.
- **Define errors out of existence** where you can: design the API so the
  common "error" case is just a normal return, not a special path every
  caller has to handle. (E.g. a `dict.get(key, default)` needs no
  try/except; a bespoke `KeyError`-raising lookup forces one everywhere.)
  Doesn't apply to genuine failures — those should still raise (see rule 3)
  — this is about cases that aren't really exceptional, just modeled as if
  they were.
- Aim for **general-but-not-generic**: a module a little more general-
  purpose than today's one call site (so the next similar need doesn't
  force a rewrite), but not built out for hypothetical futures that may
  never come. If every parameter/branch traces back to one caller's exact
  need, it's too specific; if half the surface exists for cases nothing
  calls yet, it's over-built.
- When reviewing: flag shallow wrappers and pass-throughs by name; suggest
  either deepening the interface (hide more) or removing the layer. Also
  flag highly-configurable functions with no defaults, and APIs that force
  error-handling for what's really a normal case.

## 2. Composition over inheritance

From Schlawack's "Subclassing in Python Redux": inheritance for *code reuse*
tightly couples subclass to superclass internals (the fragile base class
problem) and ages badly. Prefer composition.

- Default to composition (an object holds and delegates to another) when
  you want to reuse behavior.
- Reserve inheritance for genuine "is-a" interface conformance — implementing
  an ABC or `Protocol` — not for sharing implementation.
- If you do inherit, keep the hierarchy shallow (one level, ideally). Deep
  chains are a smell.
- When reviewing: if a subclass exists mainly to reuse a method or two,
  call out that composition (or a mixin, if genuinely narrow and documented)
  would decouple it better.

## 3. Type hints, and one consistent return type

- Every function/method gets type hints — parameters and return.
- A function should return one consistent *shape* of type. If real API needs
  require multiple return shapes, prefer **dispatch** over a `Union` return
  that pushes `isinstance` checks onto every caller. For the common
  overload-style case (same operation, behavior varies by input type),
  reach for `functools.singledispatch` specifically, rather than hand-rolled
  `isinstance` branching or `@overload` stubs.
- For structured data — an interface or data structure worth making
  explicit — pick based on validation and performance needs:
  - **`Pydantic` (`BaseModel`)** by default whenever making a shape explicit
    genuinely helps — boundary data (API payload, config, file I/O) or just
    for developer-experience clarity on an internal interface. Be conscious
    of its runtime overhead in hot paths (parsing/validation cost, object
    size) — don't reach for it inside tight loops or performance-critical
    code without weighing that cost.
  - **Frozen `dataclass`** when validation isn't needed and/or the overhead
    matters more than the DX win — hot paths, high-volume internal data.
- Reach for `Protocol`, `Literal`, etc. too, where they make a contract more
  precise — not just to add hints for their own sake.

## 4. Don't repeat yourself — one source of truth

- If the same literal, threshold, mapping, or piece of logic shows up more
  than once, it should have exactly one place it's defined — a constants
  module, an `Enum`, a `Pydantic` model/`Literal`, or a single function —
  and everywhere else refers to that, not a copy of it.
- This is about *duplicated knowledge*, not duplicated syntax. `singledispatch`
  implementations that look similar per-type aren't a violation — each
  handles genuinely different information, not a copy of the same rule.
- When reviewing: flag a magic number/string that already exists elsewhere
  in the codebase, or logic that's plainly the same rule copy-pasted.

## 5. Terse, high-signal documentation

- Every word in a docstring or comment earns its place. Cut anything a
  reader could infer from the signature or the code itself.
- Comments and docstrings explain **why**, not what — the code already says
  what.
- Use whitespace and structure (short `Args:`/`Returns:` lines, a blank line
  between summary and detail) to make scanning fast. Don't write dense
  prose paragraphs.

## How to apply this

**Writing code:** apply these by default, silently — don't narrate that
you're "applying Lance's style guide." Just write code that reflects it.

**Reviewing/refactoring:** call out violations concisely, one bullet per
issue, naming the principle (e.g. "shallow wrapper — 1. deep modules") and
the concrete fix. Don't relitigate a call that's genuinely the pragmatic
choice (see below) — note it and move on.

## Pragmatism — these are defaults, not commandments

None of the above is set in stone. When code (yours or the code under
review) deviates from a principle because the alternative would add more
complexity than it removes, that's a legitimate call — but flag it briefly
rather than silently overriding:

- In code, a short inline comment: `# shallow on purpose — this only ever
  forwards to boto3; adding depth here is pure indirection`
- In a review reply, one clause: "shallow, but matches the DB row 1:1 and a
  deeper interface would just be overhead — leaving it."

One line, stated plainly, no hedging or over-justifying. If it needs more
than a sentence to defend, that's a sign to reconsider the deviation
instead.

## Explicitly out of scope

- **Line length, formatting, import order** — that's the project's
  formatter/linter's job (black, ruff, etc.), not a design call. Don't
  flag it in review.
- **Function length / cyclomatic complexity thresholds** — no fixed number.
  Judge via rule 1 (deep modules) instead: split when a function is doing
  more than one thing an interface should hide, not because it crossed a
  line count.
- **Errors-as-values (`Result`/`Either`-style returns)** — not a default
  here. Exceptions are the Python-idiomatic path; no stance on this beyond
  "use exceptions" unless asked to reconsider.

## Examples

**Dispatch over Union return:**
```python
# Avoid — pushes isinstance onto every caller
def render(shape: Circle | Square) -> str: ...

# Prefer — functools.singledispatch, one implementation per type
@singledispatch
def render(shape) -> str: ...

@render.register
def _(shape: Circle) -> str: ...

@render.register
def _(shape: Square) -> str: ...
```

**Composition over inheritance for reuse:**
```python
# Avoid — Cache inherits from OrderedDict just to reuse eviction logic
class Cache(OrderedDict): ...

# Prefer — Cache owns an OrderedDict, exposes only what it needs
class Cache:
    def __init__(self) -> None:
        self._store: OrderedDict[str, Any] = OrderedDict()
```

**Single source of truth:**
```python
# Avoid — the threshold is duplicated and will drift
if latency_ms > 500: ...       # billing.py
if latency_ms > 500: ...       # alerting.py

# Prefer — defined once, imported everywhere
class Thresholds:
    SLOW_LATENCY_MS: Final = 500
```

**Terse docstring:**
```python
# Avoid
def retry(fn, times: int) -> Any:
    """
    This function takes a callable and a number of times, and it will
    call the function repeatedly until it succeeds or the number of
    times has been exhausted, at which point it raises the last error.
    """

# Prefer
def retry(fn: Callable[[], T], times: int) -> T:
    """Retries fn up to `times`; re-raises the last error on exhaustion."""
```
