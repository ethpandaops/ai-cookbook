# Go standards

## Scope and precedence

- Treat the repository's `go.mod`, existing conventions, generated-code policy, and tool configuration as authoritative.
- The minimum supported language version is Go 1.23. Do not change a repository's Go version as part of an unrelated task.
- Apply these standards to new and modified code. Avoid unrelated churn in existing files.
- Prefer the standard library. Add a dependency when it materially simplifies the implementation and the repository does not already provide an equivalent.

## Tooling

- Format Go code with `gofmt`. Use `goimports` when the repository already uses it.
- Run the narrowest relevant tests while iterating, then the repository's required validation before finishing.
- Respect the repository's `go.work`, build tags, code-generation steps, and CI commands.

## Logging and CLI packages

For new projects:

- Use `log/slog` for structured logging.
- Configure the root logger at the application entry point with `slog.NewJSONHandler`, or `slog.NewTextHandler` for local development.
- Pass `*slog.Logger` to long-lived components through their constructors. Derive a component logger with `logger.WithGroup("pkgname")` or a structured component attribute.
- Use typed attributes such as `slog.String`, `slog.Int`, `slog.Bool`, and `slog.Any` when they improve type safety or readability.
- Use context-aware logging methods when a request context is available.
- Never log secrets, credentials, private keys, tokens, or sensitive payloads. Implement `slog.LogValuer` when a type needs to control its logged representation.
- Log fatal conditions at error level, then return the error to `main` or exit explicitly. Do not hide control flow in logging helpers.

For existing projects:

- Continue using the project's logging package. Do not mix logging libraries in the same project as part of an unrelated change.
- Use `github.com/spf13/cobra` when a command needs Cobra's subcommands, flags, or help generation. Small commands may use the standard `flag` package.

## Package design

Package code by cohesion. Types and functions that share a lifecycle and change for the same reason usually belong in the same package.

Start with files in one package:

```text
user/
├── user.go
├── config.go
└── user_test.go
```

Create a subpackage when it has a distinct responsibility, can be used independently, or benefits from a separate dependency and test boundary:

```text
node/
├── node.go
├── p2p/
└── api/
```

Parent packages should orchestrate sibling packages rather than creating circular or sideways dependencies. Avoid speculative package splits.

Names such as `util`, `common`, `helper`, `model`, and `types` often become unrelated grab bags. Prefer a name that describes the capability. A generic-looking filename is acceptable when its contents are cohesive and the name is already conventional in the repository.

## Interfaces and constructors

- Return a concrete type from constructors by default.
- Define an interface where it is consumed, once the consumer needs more than one implementation or a test boundary.
- Keep interfaces small and focused on the behavior the consumer uses.
- Do not create an interface only to mock the implementation that sits beside it.
- Use compile-time interface checks when an implementation intentionally promises to satisfy an external interface:

```go
var _ http.Handler = (*Handler)(nil)
```

- Pass interface values directly. Pointers to interfaces are almost never needed.

```go
package user

type Service struct {
	store  Store
	logger *slog.Logger
}

func NewService(store Store, logger *slog.Logger) *Service {
	return &Service{
		store:  store,
		logger: logger.WithGroup("user"),
	}
}
```

The `Store` interface belongs in the package that consumes it. The package implementing the backing store should normally return its concrete client.

## Lifecycle methods

Add lifecycle methods only to components that own resources or background work.

- Constructors should validate dependencies and perform cheap initialization.
- Use `Start` only when a component has meaningful work that cannot begin in the constructor.
- Use `Close`, `Stop`, or `Shutdown` according to the resource and existing repository conventions.
- Accept a context for shutdown when cleanup can block or needs a deadline.
- Make cleanup safe to call more than once when practical, and document when it is not.

Plain domain values and stateless services do not need `Start` or `Stop` methods.

## Initialization

- Prefer useful zero values and composite literals for simple initialization.
- Use `make` for maps and slices populated dynamically.
- Supply a capacity when the expected size is known or profiling shows that preallocation matters. Do not invent a capacity merely to satisfy a style rule.
- Keep constructors free of hidden goroutines and network I/O unless their contract clearly says otherwise.

## Context propagation

- Functions that perform request-scoped I/O or blocking work should accept `context.Context` as their first parameter.
- Propagate the caller's context through the call stack.
- Do not store request contexts in structs.
- Do not pass `nil` contexts; use `context.Background()` only when there is no meaningful parent.
- Long-running operations must observe cancellation at points where they can stop safely.

## Concurrency

### Goroutine ownership

- Do not start a goroutine without deciding how it stops and who waits for it.
- Prefer structured lifetimes: start goroutines inside a component and stop them before the component is released.
- Keep cancellation, error propagation, and cleanup visible in the API.

```go
type Job func(context.Context) error

func runWorker(ctx context.Context, jobs <-chan Job) error {
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case job, ok := <-jobs:
			if !ok {
				return nil
			}
			if err := job(ctx); err != nil {
				return err
			}
		}
	}
}
```

The owner can run this loop in an `errgroup`, cancel the group context to stop it, and wait for the group before releasing dependencies. Jobs must also observe the context when they block.

### Channels

- The sending side owns closing a data channel after all sends have finished. Receivers should not close channels they do not own.
- Use directional channel types in function signatures where they clarify ownership.
- Choose buffer sizes from semantics: expected bursts, backpressure, bounded work, or a measured performance need.
- Use nil channels deliberately, usually to disable a `select` case. Add a comment if the behavior is not obvious.
- Make both sends and receives cancellation-aware when either side may stop early.

```go
func fanOut(ctx context.Context, in <-chan int, workers int) []<-chan int {
	outs := make([]<-chan int, workers)

	for i := range workers {
		out := make(chan int)
		outs[i] = out

		go func() {
			defer close(out)

			for {
				select {
				case <-ctx.Done():
					return
				case value, ok := <-in:
					if !ok {
						return
					}

					select {
					case out <- value * 2:
					case <-ctx.Done():
						return
					}
				}
			}
		}()
	}

	return outs
}
```

### Timeouts

Timeouts are cooperative. The work must receive and observe the derived context; wrapping uncancellable work in a goroutine can leak it after the timeout.

```go
func doWithTimeout(ctx context.Context, timeout time.Duration) error {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	return doWork(ctx)
}
```

### Synchronization

- Use channels for ownership transfer, work distribution, and signals.
- Use mutexes for protecting shared state when a channel would obscure the design.
- Use atomics for simple independent counters or flags, not multi-field invariants.
- Use `sync.Once` for one-time transitions and `sync.WaitGroup` for goroutine completion.
- Keep critical sections small. `defer mu.Unlock()` is a good default when the lock should be held until the function or small scope returns; unlock explicitly when holding it longer would block unrelated work.
- Never access shared mutable state without synchronization.

### Concurrent errors

Use `errgroup.WithContext` when a set of related goroutines should cancel on the first error. Limit concurrency when the input can be large.

```go
func processItems(ctx context.Context, items []string) error {
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(10)

	for _, item := range items {
		g.Go(func() error {
			return processItem(ctx, item)
		})
	}

	return g.Wait()
}
```

Go 1.22 and later create new loop variables for each iteration, so an extra `item := item` assignment is not needed for modules using the supported Go version.

### Concurrency validation

- Run `go test -race` for packages whose changed code uses concurrency. Include race-enabled tests in CI where the runtime cost is acceptable.
- Test cancellation, early returns, closed channels, and shutdown paths.
- Use synchronization in tests instead of sleeps where possible.
- Profile before adding concurrency or tuning buffer sizes.

## Testing

- Use the standard `testing` package by default.
- Use table-driven tests when several cases share the same setup and assertion structure.
- Test observable behavior, error identity, and boundary conditions.
- Prefer small fakes or consumer-side interfaces to mocks of concrete implementations.
- Continue using `testify/assert` or `testify/require` when the repository already uses Testify; do not add it solely for simple assertions.
- Treat coverage as a diagnostic, not a target. Prioritize critical paths and failure behavior over a repository-wide percentage.
- Keep tests deterministic and safe to run in parallel before calling `t.Parallel()`.

## Naming

- Avoid package stuttering: prefer `user.Service` over `user.UserService` when the shorter name remains clear.
- Use standard initialisms consistently: `ID`, `URL`, `HTTP`, and `RPC`.
- Name functions for the behavior they provide, not their implementation mechanism.
- Keep package names short, lowercase, and specific.
- Follow established repository terminology even when another name might be marginally better.

## Error handling

- Check returned errors. A deliberately ignored error should be safe and obvious; add a comment when the reason is not clear.
- Wrap errors with useful operation or resource context using `fmt.Errorf("...: %w", err)`.
- Keep error text lowercase unless it begins with a proper noun or identifier.
- Use `errors.Is` and `errors.As` instead of matching error strings.
- Add sentinel or custom error types only when callers need to branch on error identity or data.
- Log or return an error at the appropriate boundary; avoid logging the same error at every layer and then returning it.
- Include relevant domain context such as an operation or identifier. Source line numbers usually do not belong in user-facing errors.

## Style and documentation

- Follow `gofmt`; do not enforce a separate hard line-length limit. Refactor expressions that are difficult to read.
- Let `gofmt` or `goimports` organize imports. Preserve extra import groups only when the repository uses them consistently.
- Use `any` instead of `interface{}` in code whose declared Go version supports it.
- Use a comma-ok type assertion for one expected type. Use a type switch when handling several possible types.
- Write doc comments for exported APIs in public packages and wherever repository linting requires them. Use the declaration name near the start when it reads naturally.
- Comments should explain intent, invariants, or non-obvious tradeoffs rather than restating the code.

## File layout

Go does not require a universal declaration order. Optimize files for reading and keep related declarations close together.

A common starting point is:

1. Package documentation and clause
2. Imports
3. Related constants and variables
4. Types and their constructors
5. Methods and functions in a logical reading order

For files with several types, keeping each type's constructor and methods together is often clearer than grouping every exported declaration ahead of every unexported declaration. Follow the surrounding package and do not reorder existing code solely to satisfy this preference.

## Linting and validation

- Respect the repository's GolangCI-Lint configuration and invocation.
- Run `golangci-lint run` from the module or workspace location expected by the project.
- When linting only changed code, compare against the repository's actual default or merge-base branch. Do not assume it is named `master`.
- Run `go vet` and `go test` through the project's existing scripts or CI targets when available.
- Do not hand-edit generated files. Regenerate them with the repository's documented command.

## References

- [Go code review comments](https://go.dev/wiki/CodeReviewComments)
- [Go doc comments](https://go.dev/doc/comment)
- [Go concurrency patterns: pipelines and cancellation](https://go.dev/blog/pipelines)
