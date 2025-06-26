# Golang Package Standards

## Library Packages

Unless otherwise specified, you MUST use the following packages:

- Logging: `github.com/sirupsen/logrus`
    - Configure once at the entry point of the application. Pass down the logger to each package via the constructor.
    - Each package must have a `logrus.FieldLogger` instance passed in via the constructor. The package should add its own fields to its log instance. E.g. `log.WithField("package", "user")`
    - Use `log.WithField("field", "value")` to add fields to the log instance.
    - Use `log.WithFields(logrus.Fields{"key": "value", "key2": "value2"})` to add multiple fields to the log instance.
    - NEVER log any sensitive information
- CLI: `github.com/spf13/cobra`

## Domain-Driven Structure

Each package represents a cohesive business capability. Related types and implementations should be co-located when they:
- Share the same lifecycle
- Change for the same reasons
- Are always used together

```
user/
├── user.go      # Domain logic + client implementation
├── config.go    # Domain-specific configuration
└── user_test.go # Domain tests

order/
├── order.go     # Order service and core types
├── item.go      # OrderItem logic (tightly coupled)
├── status.go    # OrderStatus state machine (tightly coupled)
└── order_test.go
```

## Layered Package Architecture

### When to Use Layers

Create sub-packages when components:
- Have different reasons to change
- Could be used independently
- Need separate testing boundaries

Otherwise, use files within a single package.

### Dependency Rules

```
node/
├── node.go      # Orchestrates child packages
├── p2p/         # Child package (if needed)
└── api/         # Child package (if needed)
```

If siblings need to communicate, the parent must orchestrate this.

### Example: When to Split vs. Keep Together

```go
// Split: Independent components
node/
├── p2p/         # Could be its own library
└── api/         # Could serve different p2p impls

// Together: Tightly coupled logic
p2p/
├── p2p.go       # Main logic
├── reqresp.go   # Just another file
└── pubsub.go    # Just another file
```

**Key: Start with clear interfaces and boundaries. Refactor based on actual needs, not speculation.**

## Required Interface Pattern

Each package represents a cohesive business capability. Related types and implementations should be co-located when they:
- Share the same lifecycle
- Change for the same reasons
- Are always used together

```
user/
├── user.go      # Domain logic + client implementation
├── config.go    # Domain-specific configuration
└── user_test.go # Domain tests

order/
├── order.go     # Order service and core types
├── item.go      # OrderItem logic (tightly coupled)
├── status.go    # OrderStatus state machine (tightly coupled)
└── order_test.go
```

## Required Interface Pattern

Every domain package MUST:

1. Define a public interface (e.g., `UserService`)
2. Provide `NewUserService()` constructor that:
   - Returns the interface, not the struct
   - Does minimal initialization only
3. Implement lifecycle methods:
   - `Start(ctx context.Context) error` - Heavy initialization here
   - `Stop() error` - Cleanup

Additionally:

- You almost never need a pointer to an interface. You should be passing interfaces as values—the underlying data can still be a pointer.
- Always verify interface compliance at compile time where appropriate, eg: `var _ http.Handler = (*Handler)(nil)`

## Initialising

You must:
- Prefer `make(..)` for empty maps and maps populated dynamically.
- Always provide capacity hints when initializing maps with `make()`
- Always provide capacity hints when initializing slices with `make()`, particularly when appending.

## Context Propagation

- All methods that do I/O or can block MUST accept `context.Context` as first parameter
- Context should flow through the entire call stack
- Avoid storing context in structs

## Testing Standards

- Utilise table-driven tests for multiple scenarios.
- Use `testify/assert` or `testify/require` for assertions.
- Mock interfaces, not implementations.
- Aim for 70% test coverage of critical code-paths.
- You MUST always include the `-race` flag when executing `go test`.

## Naming Rules

- NO package stuttering: `user.User` not `user.UserUser`
- NO generic packages: `types/`, `utils/`, `common/`, `models/`, `helpers/`
- NO generic files: `helpers.go`, `utils.go`, `types.go`

### Example

```go
// user/user.go
package user

type Service interface {
    Start(ctx context.Context) error
    Stop() error
    GetUser(id string) (*User, error)
}

type User struct {
    ID   string
    Name string
}

func NewService(cfg Config) Service {
    return &service{cfg: cfg}
}
```

**Key: Package by cohesion - types, functions, and helpers that change together belong together.**

### Error Handling
- No errors are to be left unchecked.
- Wrap errors with context using `fmt.Errorf` with `%w` verb
- Create custom error types when needed for error handling logic
- Log errors at appropriate levels (debug, info, warn, error)

## Style

- Avoid overly long lines; aim for a soft line length limit of 99 characters.
- Always group similar dependencies/imports, ensuring they are ordered by standard library, followed by everything else.
- Follow standard Go conventions

## Linting

- If the project contains a `.golangci.yml` file, please respect it as best you can.
- `golangci-lint` is our preferred linter and if executed, should always be done so with the `--new-from-rev="origin/master"` flag to ensure only your changes are linted.
