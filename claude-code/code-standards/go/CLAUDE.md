# Golang Package Standards

## Dependencies
- Minimum Go version: 1.23.0
- External dependencies managed through go modules

## Library Packages

Unless otherwise specified, you MUST use the following packages:

- Logging: `github.com/sirupsen/logrus`
    - Configure once at the entry point of the application. Pass down the logger to each package via the constructor.
    - When passing a logger to a method: if ctx is not present, the logger must be the first parameter. If ctx is present, it must be the first parameter, and the logger must be second.
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
- Implement context cancellation handling for long operations

## Concurrency Guidelines

### Core Principles

- **Concurrency is not parallelism**: Design for concurrent execution, let the runtime handle parallelism
- **Share memory by communicating**: Prefer channels over shared memory with mutexes
- **Don't communicate by sharing memory**: Avoid complex mutex-based designs when channels are clearer

### Goroutine Management

#### Lifecycle Control
```go
// Always know when and how goroutines terminate
type Worker struct {
    done chan struct{}
    wg   sync.WaitGroup
}

func (w *Worker) Start(ctx context.Context) error {
    w.wg.Add(1)
    go func() {
        defer w.wg.Done()
        for {
            select {
            case <-ctx.Done():
                return
            case <-w.done:
                return
            default:
                // Do work
            }
        }
    }()
    return nil
}

func (w *Worker) Stop() error {
    close(w.done)
    w.wg.Wait()
    return nil
}
```

#### Goroutine Leaks Prevention
- **Never start a goroutine without knowing how it will stop**
- **Always provide a way to signal goroutine termination**
- **Use context or done channels for cancellation**
- **Wait for goroutines to complete before returning**

### Channel Patterns

#### Channel Design Rules
- **Ownership**: The goroutine that creates a channel should close it
- **Direction**: Use directional channels in function signatures
- **Nil channels**: Leverage nil channel behavior in select statements
- **Buffering**: Only buffer when you have a measurable performance need

#### Common Patterns

```go
// Fan-out pattern
func fanOut(ctx context.Context, in <-chan int, workers int) []<-chan int {
    outs := make([]<-chan int, workers)
    for i := 0; i < workers; i++ {
        out := make(chan int)
        outs[i] = out
        go func() {
            defer close(out)
            for val := range in {
                select {
                case out <- val * 2:
                case <-ctx.Done():
                    return
                }
            }
        }()
    }
    return outs
}

// Timeout pattern
func doWithTimeout(ctx context.Context, timeout time.Duration) error {
    ctx, cancel := context.WithTimeout(ctx, timeout)
    defer cancel()

    done := make(chan struct{})
    go func() {
        defer close(done)
        // Do work
    }()

    select {
    case <-done:
        return nil
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

### Synchronization Primitives

#### When to Use What
- **Channels**: For passing ownership, signaling, or when the communication itself is important
- **Mutexes**: For protecting shared state when channels would add unnecessary complexity
- **Atomic operations**: For simple counters and flags
- **sync.Once**: For one-time initialization
- **WaitGroups**: For waiting on a collection of goroutines

#### Mutex Guidelines
```go
// Always defer unlock immediately after lock
type Cache struct {
    mu    sync.RWMutex
    items map[string]any
}

func (c *Cache) Get(key string) (any, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}

func (c *Cache) Set(key string, val any) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = val
}
```

### Error Handling in Concurrent Code

```go
// Use errgroup for concurrent operations that can fail
func processItems(ctx context.Context, items []string) error {
    g, ctx := errgroup.WithContext(ctx)

    // Limit concurrency
    sem := make(chan struct{}, 10)

    for _, item := range items {
        item := item // Capture loop variable
        g.Go(func() error {
            select {
            case sem <- struct{}{}:
                defer func() { <-sem }()
            case <-ctx.Done():
                return ctx.Err()
            }
            return processItem(ctx, item)
        })
    }

    return g.Wait()
}
```

### Race Condition Prevention

- **Always run tests with `-race` flag**
- **Never access shared memory without synchronization**
- **Use `go vet` to catch common concurrency mistakes**
- **Design APIs that make races impossible**

```go
// Bad: Racy counter
type Counter struct {
    value int
}
func (c *Counter) Inc() { c.value++ } // RACE!

// Good: Safe counter
type Counter struct {
    value atomic.Int64
}
func (c *Counter) Inc() { c.value.Add(1) }
```

### Performance Considerations

- **Don't create goroutines for very small tasks**: The overhead may exceed the benefit
- **Limit concurrency**: Use worker pools or semaphores to prevent resource exhaustion
- **Batch work**: Process items in batches rather than one at a time
- **Profile before optimizing**: Use pprof to identify actual bottlenecks

```go
// Worker pool pattern
func workerPool(ctx context.Context, jobs <-chan Job, workers int) {
    var wg sync.WaitGroup

    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for {
                select {
                case job, ok := <-jobs:
                    if !ok {
                        return
                    }
                    processJob(ctx, job)
                case <-ctx.Done():
                    return
                }
            }
        }()
    }

    wg.Wait()
}
```

### Testing Concurrent Code

- **Test with multiple GOMAXPROCS values**: `go test -cpu=1,2,4,8`
- **Must use race detector**: `go test -race`
- **Test cancellation paths**: Ensure goroutines stop when expected
- **Test timeout scenarios**: Verify behavior under time pressure
- **Use sync.WaitGroup in tests**: Ensure all goroutines complete

```go
func TestConcurrentOperation(t *testing.T) {
    // Test with different levels of concurrency
    for _, workers := range []int{1, 2, 10, 100} {
        t.Run(fmt.Sprintf("workers-%d", workers), func(t *testing.T) {
            ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
            defer cancel()

            // Run test with race detector enabled
            result := runConcurrentOperation(ctx, workers)
            require.NoError(t, result)
        })
    }
}
```

## Testing Standards

- Utilise table-driven tests for multiple scenarios.
- Use `testify/assert` or `testify/require` for assertions.
- Mock interfaces, not implementations.
- Aim for 70% test coverage of critical code-paths.

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
- Return errors with proper context information (line, position)
- Use `errors.Is()` and `errors.As()` for error checking

## Style

- Avoid overly long lines; aim for a soft line length limit of 99 characters.
- Always group similar dependencies/imports, ensuring they are ordered by standard library, followed by everything else.
- Follow standard Go conventions
- Add proper docstring comments for exported functions and types
- Replace `interface{}` with `any` type alias
- Replace type assertions with type switches where appropriate to avoid panics. Throw errors instead.

## Linting

- If the project contains a `.golangci.yml` file, please respect it as best you can.
- `golangci-lint` is our preferred linter and if executed, should always be done so with the `--new-from-rev="origin/master"` flag to ensure only your changes are linted.
