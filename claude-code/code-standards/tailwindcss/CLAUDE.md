# Tailwind CSS Rules and Best Practices

## Core Principles

- **Always use Tailwind CSS v4.3+** - Ensure the codebase is using the latest stable version (v4.3.x as of mid-2026)
- **Do not use deprecated or removed utilities** - ALWAYS use the replacement
- **Never use `@apply`** - Use `@utility`, CSS variables, the `--spacing()` function, or framework components instead
- **Never construct class names dynamically** - Tailwind detects classes by scanning source files for complete, unbroken strings
- **Check for redundant classes** - Remove any classes that aren't necessary
- **Group elements logically** to simplify responsive tweaks later

## Class Detection and Source Files

Tailwind v4 scans source files as plain text and only generates CSS for class names it finds as **complete strings**:

```jsx
// ❌ Never build class names dynamically - these classes won't be generated
<div class={`text-${error ? 'red' : 'green'}-600`}></div>

// ✅ Always map to complete class names
<div class={error ? 'text-red-600' : 'text-green-600'}></div>
```

- Use `@source "../node_modules/@my-company/ui-lib"` to scan paths not covered by automatic source detection (e.g. libraries, monorepo packages)
- Use `@source not "../src/legacy"` to exclude paths from scanning
- Use `@source inline("underline")` to safelist classes that never appear in source files (supports brace expansion: `@source inline("{hover:,}bg-red-{50,{100..900..100},950}")`)

## Legacy Utilities Reference

LLMs are trained on large amounts of v3 code - never emit these legacy class names.

### Removed Utilities (NEVER use these in v4)

| ❌ Deprecated           | ✅ Replacement                                    |
| ----------------------- | ------------------------------------------------- |
| `bg-opacity-*`          | Use opacity modifiers like `bg-black/50`          |
| `text-opacity-*`        | Use opacity modifiers like `text-black/50`        |
| `border-opacity-*`      | Use opacity modifiers like `border-black/50`      |
| `divide-opacity-*`      | Use opacity modifiers like `divide-black/50`      |
| `ring-opacity-*`        | Use opacity modifiers like `ring-black/50`        |
| `placeholder-opacity-*` | Use opacity modifiers like `placeholder-black/50` |
| `flex-shrink-*`         | `shrink-*`                                        |
| `flex-grow-*`           | `grow-*`                                          |
| `overflow-ellipsis`     | `text-ellipsis`                                   |
| `decoration-slice`      | `box-decoration-slice`                            |
| `decoration-clone`      | `box-decoration-clone`                            |
| `start-*` / `end-*`     | `inset-s-*` / `inset-e-*` (deprecated in v4.2)    |

### Renamed Utilities (ALWAYS use the v4 name)

| ❌ v3              | ✅ v4              |
| ------------------ | ------------------ |
| `bg-gradient-*`    | `bg-linear-*`      |
| `shadow-sm`        | `shadow-xs`        |
| `shadow`           | `shadow-sm`        |
| `drop-shadow-sm`   | `drop-shadow-xs`   |
| `drop-shadow`      | `drop-shadow-sm`   |
| `blur-sm`          | `blur-xs`          |
| `blur`             | `blur-sm`          |
| `backdrop-blur-sm` | `backdrop-blur-xs` |
| `backdrop-blur`    | `backdrop-blur-sm` |
| `rounded-sm`       | `rounded-xs`       |
| `rounded`          | `rounded-sm`       |
| `outline-none`     | `outline-hidden`   |
| `ring`             | `ring-3`           |

Notes on the renames:

- The bare utilities (`shadow`, `blur`, `rounded`, `ring`) are still valid v4 classes, but they map to different values than in v3 - only use them when you actually mean the v4 value
- `outline-none` in v4 sets a real `outline-style: none`; use `outline-hidden` for an invisible outline that still shows in forced-colors mode (the accessible default for focus styles)
- Bare `ring` in v4 is a 1px ring in `currentColor`; use `ring-3` when you want the old v3 appearance (3px)

## v4 Syntax Rules

- **Important modifier goes at the end**: `bg-red-500!` (not `!bg-red-500`)
- **CSS variable shorthand uses parentheses**: `bg-(--brand-color)` instead of the ambiguous v3 form `bg-[--brand-color]`
- **Prefixes are variant-style**: `@import "tailwindcss" prefix(tw);` then `tw:flex tw:hover:bg-red-500`
- **Stacked variants apply left-to-right** (v3 was right-to-left): `*:first:pt-0`, not `first:*:pt-0`
- **`theme()` is deprecated** - use CSS theme variables like `var(--color-red-500)` instead

## Layout and Spacing Rules

### Flexbox and Grid Spacing

#### Always use gap utilities for internal spacing

Gap provides consistent spacing without edge cases (no extra space on last items). It's cleaner and more maintainable than margins on children.

```html
<!-- ❌ Don't do this -->
<div class="flex">
  <div class="mr-4">Item 1</div>
  <div class="mr-4">Item 2</div>
  <div>Item 3</div>
  <!-- No margin on last -->
</div>

<!-- ✅ Do this instead -->
<div class="flex gap-4">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
</div>
```

#### Gap vs Space utilities

- **Never use `space-x-*` or `space-y-*` in flex/grid layouts** - always use gap
- Space utilities add margins to children and have issues with wrapped items
- Gap works correctly with flex-wrap and all flex directions

```html
<!-- ❌ Avoid space utilities in flex containers -->
<div class="flex flex-wrap space-x-4">
  <!-- Space utilities break with wrapped items -->
</div>

<!-- ✅ Use gap for consistent spacing -->
<div class="flex flex-wrap gap-4">
  <!-- Gap works perfectly with wrapping -->
</div>
```

### General Spacing Guidelines

- **Prefer top and left margins** over bottom and right margins (unless conditionally rendered)
- **Use logical properties when direction matters** - `ms-*`/`me-*` for inline start/end, and `mbs-*`/`mbe-*`/`pbs-*`/`pbe-*` (v4.2) for block start/end; these adapt automatically to RTL and vertical writing modes
- **Use padding on parent containers** instead of bottom margins on the last child
- **Always use `min-h-dvh` instead of `min-h-screen`** - `min-h-screen` is buggy on mobile Safari
- **Prefer `size-*` utilities** over separate `w-*` and `h-*` when setting equal dimensions
- For max-widths, prefer the container scale (e.g., `max-w-2xs` over `max-w-72`)

## Typography Rules

### Line Heights

- **Never use `leading-*` classes** - Always use line height modifiers with text size
- **Always use fixed line heights from the spacing scale** - Don't use named values

```html
<!-- ❌ Don't do this -->
<p class="text-base leading-7">Text with separate line height</p>
<p class="text-lg leading-relaxed">Text with named line height</p>

<!-- ✅ Do this instead -->
<p class="text-base/7">Text with line height modifier</p>
<p class="text-lg/8">Text with specific line height</p>
```

### Font Size Reference

Be precise with font sizes - know the default theme values (projects can override these via `--text-*` theme variables):

- `text-xs` = 12px
- `text-sm` = 14px
- `text-base` = 16px
- `text-lg` = 18px
- `text-xl` = 20px

## Color and Opacity

### Opacity Modifiers

**Never use `bg-opacity-*`, `text-opacity-*`, etc.** - use the opacity modifier syntax:

```html
<!-- ❌ Don't do this -->
<div class="bg-red-500 bg-opacity-60">Old opacity syntax</div>

<!-- ✅ Do this instead -->
<div class="bg-red-500/60">Modern opacity syntax</div>
```

## Responsive Design

### Breakpoint Optimization

- **Check for redundant classes across breakpoints**
- **Only add breakpoint variants when values change**

```html
<!-- ❌ Redundant breakpoint classes -->
<div class="px-4 md:px-4 lg:px-4">
  <!-- md:px-4 and lg:px-4 are redundant -->
</div>

<!-- ✅ Efficient breakpoint usage -->
<div class="px-4 lg:px-8">
  <!-- Only specify when value changes -->
</div>
```

## Dark Mode

### Dark Mode Best Practices

- Use the plain `dark:` variant pattern
- Put light mode styles first, then dark mode styles
- When stacking variants, write `dark:` first as a convention (e.g. `dark:hover:bg-gray-800`) - note that stacked variants apply left-to-right in v4

```html
<!-- ✅ Correct dark mode pattern -->
<div class="bg-white text-black dark:bg-black dark:text-white">
  <button class="hover:bg-gray-100 dark:hover:bg-gray-800">Click me</button>
</div>
```

## Gradient Utilities

- **ALWAYS Use `bg-linear-*` instead of `bg-gradient-*` utilities** - The gradient utilities were renamed in v4
- Use the new `bg-radial` or `bg-radial-[<position>]` to create radial gradients
- Use the new `bg-conic` or `bg-conic-*` to create conic gradients

```html
<!-- ✅ Use the new gradient utilities -->
<div class="h-14 bg-linear-to-br from-violet-500 to-fuchsia-500"></div>
<div
  class="size-18 bg-radial-[at_50%_75%] from-sky-200 via-blue-400 to-indigo-900 to-90%"
></div>
<div
  class="size-24 bg-conic-180 from-indigo-600 via-indigo-50 to-indigo-600"
></div>

<!-- ❌ Do not use bg-gradient-* utilities -->
<div class="h-14 bg-gradient-to-br from-violet-500 to-fuchsia-500"></div>
```

## Working with CSS Variables

### Accessing Theme Values

Tailwind CSS v4 exposes all theme values as CSS variables:

```css
/* Access colors, and other theme values */
.custom-element {
  background: var(--color-red-500);
  border-radius: var(--radius-lg);
}
```

### The `--spacing()` Function

Use the dedicated `--spacing()` function for spacing calculations:

```css
.custom-class {
  margin-top: calc(100vh - --spacing(16));
}
```

### The `--alpha()` Function

Use `--alpha()` to adjust the opacity of a color in custom CSS:

```css
.custom-element {
  color: --alpha(var(--color-lime-300) / 50%);
}
```

### Extending theme values

Use CSS to extend theme values:

```css
@import "tailwindcss";

@theme {
  --color-mint-500: oklch(0.72 0.11 178);
}
```

```html
<div class="bg-mint-500">
  <!-- ... -->
</div>
```

### Custom Utilities and Variants

Use `@utility` (not `@apply` or plain CSS classes) to define custom utilities - they work with all variants and are sorted into the correct cascade layer:

```css
/* Simple utility */
@utility content-auto {
  content-visibility: auto;
}

/* Functional utility with a value, using --default() for a fallback (v4.3) */
@utility tab-* {
  tab-size: --value(integer, --default(4));
}
```

Use `@custom-variant` to define new variants, and `@variant` to use variants inside custom CSS (v4.3 supports stacked `@variant hover:focus` and compound `@variant hover, focus`):

```css
@custom-variant theme-midnight (&:where([data-theme="midnight"] *));

.button {
  background: var(--color-sky-500);
  @variant hover, focus {
    background: var(--color-sky-600);
  }
}
```

Use `@reference "../app.css";` at the top of CSS modules or Vue/Svelte `<style>` blocks to access theme variables and variants without duplicating the emitted CSS.

## New v4 Features

### Container Queries

Use the `@container` class and size variants:

```html
<article class="@container">
  <div class="flex flex-col @md:flex-row @lg:gap-8">
    <img class="w-full @md:w-48" />
    <div class="mt-4 @md:mt-0">
      <!-- Content adapts to container size -->
    </div>
  </div>
</article>
```

### Container Query Units

Use container-based units like `cqw` for responsive sizing:

```html
<div class="@container">
  <h1 class="text-[50cqw]">Responsive to container width</h1>
</div>
```

### Text Shadows (v4.1)

Use text-shadow-\* utilities from text-shadow-2xs to text-shadow-lg:

```html
<!-- ✅ Text shadow examples -->
<h1 class="text-shadow-lg">Large shadow</h1>
<p class="text-shadow-sm/50">Small shadow with opacity</p>
```

### Masking (v4.1)

Use the new composable mask utilities for image and gradient masks:

```html
<!-- ✅ Linear gradient masks on specific sides -->
<div class="mask-t-from-50%">Top fade</div>
<div class="mask-b-from-20% mask-b-to-80%">Bottom gradient</div>
<div class="mask-linear-from-white mask-linear-to-black/60">
  Fade from white to black
</div>

<!-- ✅ Radial gradient masks -->
<div class="mask-radial-[100%_100%] mask-radial-from-75% mask-radial-at-left">
  Radial mask
</div>
```

### Text Wrapping (v4.1)

Use `wrap-break-word` and `wrap-anywhere` to control how long words break:

```html
<p class="wrap-break-word">Breaks long words at arbitrary points if needed</p>
<div class="flex">
  <p class="wrap-anywhere">Use in flex layouts where break-word alone won't shrink</p>
</div>
```

### Useful v4.0/v4.1 Variants

- `not-*` - negate variants or media queries: `not-hover:opacity-75`, `not-supports-hanging-punctuation:px-4`
- `starting:` - `@starting-style` entry transitions without JavaScript
- `in-*` - like `group-*` but without needing a `group` class on the parent
- `nth-*` / `nth-last-*` - `nth-3:bg-blue-500`, `nth-[2n+1_of_li]:bg-gray-100`
- `pointer-coarse:` / `pointer-fine:` - adapt to touch vs mouse input: `pointer-coarse:p-4`
- `user-valid:` / `user-invalid:` - form validation styles only after user interaction
- `inert`, `noscript:`, `inverted-colors:` - accessibility and environment states
- Safe alignment: `justify-center-safe` falls back to `start` when content overflows

### Logical Properties (v4.2)

Use logical utilities for direction-aware layouts (RTL, vertical writing modes):

```html
<!-- Block-direction margin, padding, and borders -->
<div class="mbs-6 mbe-2 pbs-4 pbe-8 border-bs border-be-2"><!-- ... --></div>

<!-- Logical sizing -->
<div class="block-64 inline-full max-inline-lg"><!-- ... --></div>

<!-- Logical inset (replaces deprecated start-*/end-*) -->
<div class="absolute inset-s-0 inset-e-4 inset-bs-2 inset-be-8"><!-- ... --></div>
```

### New Color Palettes (v4.2)

Four neutral-ish palettes were added to the default theme: `mauve`, `olive`, `mist`, and `taupe`:

```html
<div class="bg-mauve-950 text-mauve-100">Mauve</div>
<div class="border border-mist-200 shadow-taupe-950/10">Mist and taupe</div>
```

### Font Features (v4.2)

Use `font-features-*` to control OpenType features via `font-feature-settings`:

```html
<div class='font-features-["tnum"]'>1,234.56 (tabular numbers)</div>
```

### Scrollbar Styling (v4.3)

Use first-party scrollbar utilities instead of plugins or custom CSS:

```html
<!-- Scrollbar width and colors (with opacity modifier support) -->
<div class="scrollbar-thin scrollbar-thumb-sky-700 scrollbar-track-sky-100 overflow-auto">
  <!-- ... -->
</div>

<!-- Reserve gutter space to prevent layout shift -->
<div class="scrollbar-gutter-stable overflow-auto"><!-- ... --></div>
```

### Zoom and Tab Size (v4.3)

```html
<div class="zoom-75">Zoomed out</div>
<pre class="tab-2">Two-space tabs</pre>
```

### Size Container Queries (v4.3)

Use `@container-size` when you need block-direction container units (`cqb`, `cqh`):

```html
<div class="@container-size">
  <div class="h-[50cqb]"><!-- Half the container's block size --></div>
</div>
```

## Component Patterns

### Avoiding Utility Inheritance

Don't add utilities to parents that you override in children:

```html
<!-- ❌ Avoid this pattern -->
<div class="text-center">
  <h1>Centered Heading</h1>
  <div class="text-left">Left-aligned content</div>
</div>

<!-- ✅ Better approach -->
<div>
  <h1 class="text-center">Centered Heading</h1>
  <div>Left-aligned content</div>
</div>
```

### Component Extraction

- Extract repeated patterns into framework components, not CSS classes
- Keep utility classes in templates/JSX
- Use data attributes for complex state-based styling

## CSS Best Practices

### Nesting Guidelines

- Use nesting when styling both parent and children
- Avoid empty parent selectors

```css
/* ✅ Good nesting - parent has styles */
.card {
  padding: --spacing(4);

  > .card-title {
    font-weight: bold;
  }
}

/* ❌ Avoid empty parents */
ul {
  > li {
    /* Parent has no styles */
  }
}
```

## Common Pitfalls to Avoid

1. **Using old opacity utilities** - Always use `/opacity` syntax like `bg-red-500/60`
2. **Redundant breakpoint classes** - Only specify changes
3. **Space utilities in flex/grid** - Always use gap
4. **Leading utilities** - Use line-height modifiers like `text-sm/6`
5. **Arbitrary values** - Always use Tailwind's predefined scale whenever possible (e.g., use `ml-4` over `ml-[16px]`)
6. **@apply directive** - Use `@utility`, components, or CSS variables
7. **min-h-screen on mobile** - Use min-h-dvh
8. **Separate width/height** - Use size utilities when equal
9. **Dynamically constructed class names** - Always write complete class names so the scanner can detect them
10. **`start-*`/`end-*` utilities** - Deprecated in v4.2, use `inset-s-*`/`inset-e-*`
11. **`theme()` function in CSS** - Deprecated, use CSS variables like `var(--color-red-500)`
12. **Important prefix position** - `bg-red-500!` (suffix), not `!bg-red-500`
13. **Custom scrollbar CSS or plugins** - Use first-party `scrollbar-*` utilities (v4.3)