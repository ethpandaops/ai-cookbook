# Golang Standards

## Package Structure

### Domain-Driven Package Structure

Each package should be organized around a business domain or capability, with types and their implementations co-located:

```
domain/
├── domain.go      # Main domain logic and client implementation
├── config.go      # Domain-specific configuration
└── types.go       # Domain-specific types (if file gets too large)

```
### Claude MUST NOT create Grab-Bag Packages:
- `types/` - Types belong with their domain logic
- `utils/` - Utility functions should live in their relevant domains
- `common/` - Shared code should be in properly named domain packages
- `models/` - Domain models belong in their respective domains
- `helpers/` - Helper functions should be part of their domain

### Claude MUST NOT create "Grab-Bag" files:
- `helpers.go` - Helper functions should be part of their domain
- `utils.go` - Utility functions should live in their relevant domains
