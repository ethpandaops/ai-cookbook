# Rust Package Standards

## Dependencies
- Minimum Rust version: 1.88.0 (stable)
- Use `Cargo.toml` for dependency management
- Pin versions for production applications
- Keep toolchain updated with `rustup update`

## Required Crate Patterns

Unless otherwise specified, you MUST use the following crates:

- **Logging**: `tracing` and `tracing-subscriber`
    - Use structured logging with `tracing::info!`, `tracing::error!`, etc.
    - Add context with `tracing::Span` and fields: `tracing::info!(user_id = %id, "User logged in")`
    - Configure once at application entry point
    - NEVER log sensitive information
- **CLI**: `clap` with derive macros
- **Error Handling**: `anyhow` for applications, `thiserror` for libraries
- **Async Runtime**: `tokio` for async applications (or `trpl` for learning/examples)
- **JSON**: `serde` with `serde_json`
- **Testing**: Use built-in `#[test]` with `assert_eq!`, `assert!` macros

## Project Structure

### Cargo Workspace Pattern

For multi-crate projects, use workspace structure:

```
project/
├── Cargo.toml           # Workspace definition
├── crates/
│   ├── core/            # Core business logic
│   │   ├── Cargo.toml
│   │   └── src/
│   ├── api/             # HTTP API layer
│   │   ├── Cargo.toml
│   │   └── src/
│   └── cli/             # Command-line interface
│       ├── Cargo.toml
│       └── src/
└── examples/
```

### Single Crate Structure

```
src/
├── main.rs             # Application entry point
├── lib.rs              # Library root (if applicable)
├── config.rs           # Configuration types
├── error.rs            # Error types
├── models/             # Domain models
│   ├── mod.rs
│   ├── user.rs
│   └── order.rs
├── services/           # Business logic
│   ├── mod.rs
│   ├── user.rs         # UserService (not user_service.rs)
│   └── order.rs        # OrderService
└── storage/            # Database/persistence layer
    ├── mod.rs
    └── database.rs
```

**Note**: Avoid generic module names like `utils/`, `helpers/`, `common/`. Instead, use specific names that describe the domain or functionality.

## Required Interface Pattern

Every service module MUST:

1. **Define a trait** for the service interface
2. **Provide constructor** that returns `impl Trait` or `Box<dyn Trait>`
3. **Implement lifecycle methods** when needed:
   - `async fn start(&mut self) -> Result<()>`
   - `async fn stop(&mut self) -> Result<()>`

```rust
// user.rs
use anyhow::Result;

pub trait UserService {
    async fn get_user(&self, id: u64) -> Result<User>;
    async fn create_user(&self, data: CreateUserRequest) -> Result<User>;
}

pub struct UserServiceImpl {
    db: Arc<Database>,
}

impl UserServiceImpl {
    pub fn new(db: Arc<Database>) -> impl UserService {
        Self { db }
    }
}

impl UserService for UserServiceImpl {
    async fn get_user(&self, id: u64) -> Result<User> {
        // Implementation
    }
}
```

## Error Handling Standards

### Library Crates
- Use `thiserror` for custom error types
- Implement `std::error::Error` trait
- Provide context with error variants

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum UserError {
    #[error("User not found: {id}")]
    NotFound { id: u64 },
    #[error("Database error")]
    Database(#[from] sqlx::Error),
    #[error("Validation failed: {0}")]
    Validation(String),
}
```

### Application Crates
- Use `anyhow` for error handling
- Use `?` operator for error propagation
- Add context with `.context()` or `.with_context()`

```rust
use anyhow::{Context, Result};

async fn process_user(id: u64) -> Result<()> {
    let user = get_user(id)
        .await
        .with_context(|| format!("Failed to get user {}", id))?;
    
    user.validate()
        .context("User validation failed")?;
    
    Ok(())
}
```

### Result Handling Patterns

- **Always handle `Result` types** - never ignore with `let _ = `
- **Use `?` operator** for early returns and chaining
- **Use `match` for complex error handling**
- **Use `unwrap_or_else` for fallback values**
- **Use `expect` with meaningful messages** only when you're certain failure indicates a programming error

```rust
// Good: Handle all cases
let user = match get_user(id).await {
    Ok(user) => user,
    Err(UserError::NotFound { .. }) => return Ok(None),
    Err(e) => return Err(e.into()),
};

// Good: Use ? for propagation and chaining
let content = std::fs::File::open("config.toml")?.read_to_string()?;

// Good: Provide fallback
let config = load_config().unwrap_or_else(|_| Config::default());

// Good: expect with context when failure is a programming error
let config_file = include_str!("config.toml")
    .parse::<Config>()
    .expect("built-in config should always be valid");
```

## Memory Safety & Ownership

### Ownership Guidelines
- **Prefer owned types** in public APIs unless lifetime parameters are necessary
- **Use `&str` for string parameters**, `String` for owned return values
- **Use `&[T]` for slice parameters**, `Vec<T>` for owned collections
- **Minimize `Clone` usage** - prefer references or moves

```rust
// Good: Take references, return owned
pub fn process_text(input: &str) -> String {
    input.to_uppercase()
}

// Good: Take slice, return owned
pub fn filter_items(items: &[Item]) -> Vec<Item> {
    items.iter().filter(|item| item.active).cloned().collect()
}
```

### Reference Lifetimes
- **Avoid lifetime parameters** in public APIs when possible
- **Use `'static` for global references**
- **Use named lifetimes** when relationships are complex

```rust
// Simple case - avoid lifetime parameters
pub fn find_user(users: &[User], id: u64) -> Option<User> {
    users.iter().find(|u| u.id == id).cloned()
}

// Complex case - use named lifetimes
pub fn find_user_ref<'a>(users: &'a [User], id: u64) -> Option<&'a User> {
    users.iter().find(|u| u.id == id)
}
```

## Async/Await Patterns

### Async Function Design
- **Use `async fn` for I/O operations**
- **Return `Result` for fallible operations** 
- **Use `tokio::spawn` for concurrent tasks**
- **Use `select!` for cancellation and racing**
- **Use `join!` for concurrent operations that should all complete**

```rust
use tokio::{select, join};
use tokio::time::{timeout, Duration};

pub async fn fetch_with_timeout(url: &str) -> Result<String> {
    let response = timeout(Duration::from_secs(10), fetch_url(url))
        .await
        .context("Request timed out")?;
    
    response.context("Failed to fetch URL")
}

pub async fn run_service(mut shutdown: tokio::sync::oneshot::Receiver<()>) -> Result<()> {
    loop {
        select! {
            _ = &mut shutdown => {
                tracing::info!("Shutdown signal received");
                break;
            }
            result = process_next_item() => {
                result.context("Failed to process item")?;
            }
        }
    }
    Ok(())
}

// Concurrent operations with join!
pub async fn fetch_multiple_urls(urls: &[&str]) -> Result<Vec<String>> {
    let futures = urls.iter().map(|url| fetch_url(*url));
    let results = join_all(futures).await;
    results.into_iter().collect()
}
```

### Working with Dynamic Futures
- **Use `Box<dyn Future>` for heterogeneous future collections**
- **Use `Pin<Box<dyn Future>>` when futures need to be pinned**
- **Use `join_all` for concurrent execution**

```rust
use std::future::Future;
use std::pin::Pin;

// For heterogeneous futures that need to be collected
pub async fn run_mixed_tasks() -> Result<()> {
    let futures: Vec<Pin<Box<dyn Future<Output = Result<()>> + Send>>> = vec![
        Box::pin(fetch_data()),
        Box::pin(process_queue()),
        Box::pin(cleanup_temp_files()),
    ];
    
    join_all(futures).await
        .into_iter()
        .collect::<Result<Vec<_>>>()?;
    
    Ok(())
}

// Alternative using the pin! macro for stack pinning
pub async fn run_mixed_tasks_stack_pinned() -> Result<()> {
    use std::pin::pin;
    
    let fetch_fut = pin!(fetch_data());
    let process_fut = pin!(process_queue());
    let cleanup_fut = pin!(cleanup_temp_files());
    
    let futures: Vec<Pin<&mut dyn Future<Output = Result<()>>>> = 
        vec![fetch_fut, process_fut, cleanup_fut];
    
    join_all(futures).await
        .into_iter()
        .collect::<Result<Vec<_>>>()?;
    
    Ok(())
}
```

### Stream Processing
- **Use `StreamExt` trait** for stream operations (requires `use` import)
- **Handle stream errors properly** with proper channel error handling
- **Use `stream::iter` to convert iterators** to streams

```rust
use futures::stream::{self, StreamExt};
use tokio::sync::mpsc;

// Converting iterator to stream
pub async fn process_items_as_stream(items: Vec<Item>) -> Result<()> {
    let mut stream = stream::iter(items.into_iter())
        .map(|item| async move { process_item(item).await });

    while let Some(result) = stream.next().await {
        result?;
    }
    Ok(())
}

// Channel-based stream with error handling
pub fn create_message_stream() -> impl Stream<Item = String> {
    let (tx, rx) = mpsc::unbounded_channel();
    
    tokio::spawn(async move {
        for i in 1..=10 {
            if let Err(send_error) = tx.send(format!("Message {}", i)) {
                eprintln!("Cannot send message: {}", send_error);
                break;
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
    });

    tokio_stream::wrappers::UnboundedReceiverStream::new(rx)
}

// Processing multiple streams concurrently
pub async fn merge_streams() -> Result<()> {
    let stream1 = create_message_stream();
    let stream2 = create_interval_stream();
    
    let mut merged = stream::select(stream1, stream2);
    
    while let Some(value) = merged.next().await {
        println!("Received: {}", value);
    }
    
    Ok(())
}
```

## Concurrency Guidelines

### Thread Safety
- **Use `Arc<T>` for shared ownership across threads**
- **Use `Mutex<T>` or `RwLock<T>` for shared mutable state**
- **Prefer `tokio::sync` primitives for async code**
- **Use channels for communication between tasks**

```rust
use std::sync::Arc;
use tokio::sync::{Mutex, mpsc};

#[derive(Clone)]
pub struct SharedState {
    counter: Arc<Mutex<u64>>,
}

impl SharedState {
    pub fn new() -> Self {
        Self {
            counter: Arc::new(Mutex::new(0)),
        }
    }
    
    pub async fn increment(&self) -> u64 {
        let mut counter = self.counter.lock().await;
        *counter += 1;
        *counter
    }
}

// Channel pattern for task communication
pub async fn worker_pool() -> Result<()> {
    let (tx, mut rx) = mpsc::channel::<WorkItem>(100);
    
    // Spawn workers
    for _ in 0..4 {
        let rx = rx.clone();
        tokio::spawn(async move {
            while let Some(item) = rx.recv().await {
                process_item(item).await;
            }
        });
    }
    
    Ok(())
}
```

## Testing Standards

### Unit Tests
- **Use `#[cfg(test)]` for test modules**
- **Use descriptive test names** that explain what is being tested
- **Follow AAA pattern**: Arrange, Act, Assert
- **Use `assert_eq!`, `assert!`, and `assert_ne!` macros**

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_user_validation_succeeds_with_valid_data() {
        // Arrange
        let user = User {
            id: 1,
            name: "John Doe".to_string(),
            email: "john@example.com".to_string(),
        };

        // Act
        let result = user.validate();

        // Assert
        assert!(result.is_ok());
    }

    #[test]
    fn test_user_validation_fails_with_empty_name() {
        // Arrange
        let user = User {
            id: 1,
            name: "".to_string(),
            email: "john@example.com".to_string(),
        };

        // Act
        let result = user.validate();

        // Assert
        assert!(result.is_err());
        assert_eq!(result.unwrap_err().to_string(), "Name cannot be empty");
    }
}
```

### Async Tests
- **Use `#[tokio::test]` for async tests**
- **Test both success and failure cases**
- **Use `timeout` for long-running tests**

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::{timeout, Duration};

    #[tokio::test]
    async fn test_async_service_responds_correctly() {
        let service = TestService::new();
        
        let result = timeout(Duration::from_secs(1), service.process())
            .await
            .expect("Test should not timeout")
            .expect("Service should succeed");
            
        assert_eq!(result.status, "completed");
    }
}
```

### Integration Tests
- **Place in `tests/` directory**
- **Use `common` module for shared test utilities**
- **Test public API only**

```rust
// tests/integration_test.rs
use myapp::UserService;

#[tokio::test]
async fn test_user_creation_workflow() {
    let service = UserService::new_test();
    
    let user = service.create_user(CreateUserRequest {
        name: "Test User".to_string(),
        email: "test@example.com".to_string(),
    }).await.expect("User creation should succeed");
    
    assert_eq!(user.name, "Test User");
    assert!(!user.id.is_empty());
}
```


## Naming Conventions

### Avoiding Repetition
- **No package stuttering**: Avoid repeating module names in types (e.g., `user::UserUser`)
- **File names should match primary type**: `user.rs` contains `UserService`, not `user_service.rs`
- **Balance clarity with brevity**: Use `UserService` not just `Service` - imports are clearer
- **Avoid redundant suffixes** only when context is unambiguous

### Module and File Names
- **Use snake_case** for module and file names
- **Keep module names descriptive** and specific
- **NO generic names** like `utils`, `helpers`, `common`, `types`
- **Use domain-specific names**: `storage`, `auth`, `metrics` instead of `database`, `security`, `monitoring`

### Type Names
- **Use PascalCase** for types, structs, enums
- **Use descriptive names** that indicate purpose
- **Avoid redundant suffixes** when context is clear
- **Use module hierarchy for disambiguation**

### Function and Variable Names
- **Use snake_case** for functions and variables
- **Use verb phrases** for functions: `get_user`, `create_order`
- **Use noun phrases** for variables: `user_count`, `total_amount`
- **NO redundant prefixes**: In `UserService`, use `get` not `get_user`

```rust
// Good naming examples balancing clarity with brevity
pub struct UserService;  // Clear when imported
pub struct UserNotFoundError;
pub enum UserStatus { Active, Inactive, Suspended }

impl UserService {
    pub fn new() -> Self { Self }
    pub async fn get(&self, id: u64) -> Result<User> { todo!() }
    pub async fn create(&self, request: CreateUserRequest) -> Result<User> { todo!() }
}

// Usage is clear without aliasing:
use services::user::{UserService, CreateUserRequest};
let user_service = UserService::new();
let user = user_service.get(123).await?;
```

## Style Guidelines

### Code Formatting
- **Use `rustfmt`** with default settings
- **Line length limit**: 100 characters (default)
- **Use trailing commas** in multi-line expressions

### Documentation
- **Document all public items** with `///` comments
- **Include examples** in documentation when helpful
- **Use `#[doc = "..."]` for conditional documentation**

```rust
/// Represents a user in the system.
/// 
/// # Examples
/// 
/// ```
/// let user = User::new(1, "John Doe", "john@example.com");
/// assert_eq!(user.name, "John Doe");
/// ```
pub struct User {
    pub id: u64,
    pub name: String,
    pub email: String,
}

impl User {
    /// Creates a new user with the given details.
    /// 
    /// # Arguments
    /// 
    /// * `id` - The unique identifier for the user
    /// * `name` - The user's full name
    /// * `email` - The user's email address
    /// 
    /// # Returns
    /// 
    /// A new `User` instance.
    pub fn new(id: u64, name: String, email: String) -> Self {
        Self { id, name, email }
    }
}
```

### Import Organization
- **Group imports**: std, external crates, local modules
- **Use `use` statements** rather than fully qualified paths
- **Prefer glob imports** only for preludes and test modules

```rust
// Standard library
use std::collections::HashMap;
use std::sync::Arc;

// External crates
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use tokio::sync::Mutex;
use tracing::{info, error};

// Local modules
use crate::config::Config;
use crate::models::User;
```

## Performance Guidelines

### Memory Efficiency
- **Use `Box<T>` for large types** to avoid stack overflow
- **Use `Cow<'_, T>` for conditional ownership**
- **Use `&str` over `String`** when possible
- **Use iterators** instead of collecting when possible

```rust
use std::borrow::Cow;

// Good: Use iterator chains
pub fn filter_active_users(users: &[User]) -> impl Iterator<Item = &User> {
    users.iter().filter(|user| user.active)
}

// Good: Use Cow for conditional cloning
pub fn normalize_name(name: Cow<'_, str>) -> Cow<'_, str> {
    if name.chars().any(|c| c.is_uppercase()) {
        Cow::Owned(name.to_lowercase())
    } else {
        name
    }
}
```

### Allocation Optimization
- **Pre-allocate collections** when size is known
- **Use `with_capacity`** for `Vec` and `HashMap`
- **Reuse allocations** when possible

```rust
// Good: Pre-allocate with known capacity
pub fn process_items(items: &[Item]) -> Vec<ProcessedItem> {
    let mut results = Vec::with_capacity(items.len());
    
    for item in items {
        results.push(process_item(item));
    }
    
    results
}
```

## Security Guidelines

### Data Validation
- **Validate all input** at boundaries
- **Use type-safe parsing** with `FromStr` or serde
- **Sanitize user input** before database operations

```rust
use serde::Deserialize;

#[derive(Deserialize)]
pub struct CreateUserRequest {
    #[serde(deserialize_with = "validate_name")]
    name: String,
    #[serde(deserialize_with = "validate_email")]
    email: String,
}

fn validate_name<'de, D>(deserializer: D) -> Result<String, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let name: String = Deserialize::deserialize(deserializer)?;
    if name.trim().is_empty() {
        return Err(serde::de::Error::custom("Name cannot be empty"));
    }
    if name.len() > 100 {
        return Err(serde::de::Error::custom("Name too long"));
    }
    Ok(name.trim().to_string())
}
```

### Secrets Management
- **Never hardcode secrets** in source code
- **Use environment variables** for configuration
- **Use secure random generation** for tokens

```rust
use std::env;
use anyhow::Result;

pub struct Config {
    pub database_url: String,
    pub api_key: String,
}

impl Config {
    pub fn from_env() -> Result<Self> {
        Ok(Self {
            database_url: env::var("DATABASE_URL")
                .context("DATABASE_URL environment variable not set")?,
            api_key: env::var("API_KEY")
                .context("API_KEY environment variable not set")?,
        })
    }
}
```

## Linting and Tools

### Required Tools
- **`rustfmt`**: Code formatting (run before commits)
- **`clippy`**: Linting and suggestions (run with `--deny warnings`)
- **`cargo deny`**: License and security auditing
- **`cargo audit`**: Security vulnerability scanning
- **`cargo update`**: Keep dependencies current
- **`rustup update`**: Keep toolchain updated

### CI/CD Requirements
```bash
# Required checks in CI
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
cargo audit
cargo deny check

# Optional but recommended
cargo test --doc  # Test documentation examples
```

### Modern Clippy Configuration
Add to `Cargo.toml` for Rust 1.88+:

```toml
[lints.clippy]
# Deny these lints for better code quality
unwrap_used = "deny"
expect_used = "warn"  # Allow with good messages
indexing_slicing = "deny"
panic = "deny"
todo = "deny"
unimplemented = "deny"

# Async-specific lints
future_not_send = "warn"
large_futures = "warn"

# Performance lints
inefficient_to_string = "warn"
string_add = "warn"

# Allow these pedantic lints that can be overly strict
module_name_repetitions = "allow"
type_complexity = "allow"
too_many_arguments = "allow"
```

### Rust Edition and Features
```toml
[package]
edition = "2021"  # Use latest stable edition
rust-version = "1.88"  # MSRV

# Enable useful features
[dependencies]
tokio = { version = "1.0", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
```
