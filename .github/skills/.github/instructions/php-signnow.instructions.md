---
description: PHP coding standards and best practices for SignNow applications with project-specific conventions
applyTo: '**/*.php'
---

# PHP Coding Standards

## File Structure

- UTF-8 encoding without BOM
- Start with `<?php` tag, **never** close with `?>`
- Add `declare(strict_types = 1);` after `<?php` (**no blank line** between them)
- **Exception**: interfaces do NOT need `declare(strict_types = 1);`
- One blank line after namespace declaration
- One blank line after `use` block
- One class/interface per file
- Line length recommendation: **120** characters (no strict limit)
- UNIX-style line endings (`chr(10)`)

```php
<?php
declare(strict_types = 1);

namespace YourCompany\Package\Something\New;
```

**Interface file example** (no strict_types):

```php
<?php

namespace JsonSchema;

interface UriRetrieverInterface
{
    public function retrieve(string $uri, ?string $baseUri = null): string;
}
```

## Naming Conventions

### General Rules
- Use **English** for all names (classes, methods, variables, comments, database fields)
- CamelCase acronyms (not ALL-CAPS): `Html`, `Xml`, `Api` (not `HTML`, `XML`, `API`)
- Allowed characters: `a-z`, `A-Z`, `0-9` only
- **Never** start names with numbers

### Files
- Filenames: `UpperCamelCase.php`
- Match class/interface name exactly
- Integration tests: append `Cest.php` (e.g., `DocumentServiceCest.php`)
- Follow PSR-4 directory structure

### Classes
- `UpperCamelCase`
- Must be **nouns**, never adjectives
- Unqualified name must be meaningful without namespace
- Abstract classes: do **NOT** prefix with `Abstract`
- Interfaces: **must** end with `Interface`

### Methods
- `lowerCamelCase`
- Descriptive but concise
- Constructor: always `__construct()`, never class name

### Variables
- `lowerCamelCase`
- Self-explanatory, not abbreviated
- Exception: `$i`, `$j`, `$k` allowed in `for` loops

### Constants
- `UPPER_SNAKE_CASE`
- Use lowercase for `true`, `false`, `null`

## Class/Namespace Naming Examples

**Incorrect:**

| Class | Unqualified | Problem |
|-------|-------------|---------|
| `\Neos\Flow\Session\Php` | `Php` | Not a representation of PHP |
| `\Neos\Cache\Backend\File` | `File` | Doesn't represent a file |
| `\Neos\Flow\Session\Interface` | `Interface` | Reserved keyword |
| `\Neos\Foo\Controller\Default` | `Default` | Reserved keyword |
| `\Neos\Flow\Objects\Manager` | `Manager` | Too fuzzy |

**Correct:**

| Class | Unqualified | Why |
|-------|-------------|-----|
| `\Neos\Flow\Session\PhpSession` | `PhpSession` | Clear meaning |
| `\Neos\Flow\Cache\Backend\FileBackend` | `FileBackend` | Specific purpose |
| `\Neos\Flow\Session\SessionInterface` | `SessionInterface` | Proper interface |
| `\Neos\Foo\Controller\StandardController` | `StandardController` | Clear role |
| `\Neos\Flow\Objects\ObjectManager` | `ObjectManager` | Specific manager |

## Code Formatting (PSR-12)

### Indentation
- **4 spaces** (never tabs)
- No spaces in blank lines

### Braces
- Classes/methods: opening brace on **next line**
- Control structures: opening brace on **same line**

```php
class DocumentService extends BaseService
{
    public function getDocument(): Document
    {
        if ($condition === false) {
            throw new NotFoundException();
        }

        return $this->document;
    }
}
```

### Control Structures
- One space after keywords (`if`, `for`, `while`)
- No space after `(` or before `)`
- Use `=== false` instead of `!$value`
- Comparison with `true` can omit `=== true`
- Use `elseif` as separate keywords (not `else if`)

```php
if ($this->decisionManager->decide($this->token, ['read'], $entity === false)
    && $this->checkPermissions($entity, $user) === false
) {
    throw new NotReadableException();
}

if (
    $expr1
    && $expr2
) {
    // if body
} elseif (
    $expr3
    && $expr4
) {
    // elseif body
}
```

### Blank Lines
- One blank line **before** `return` statement
- One blank line between class members/methods
- No blank lines after opening brace
- No blank lines before closing brace

## Constructor Property Promotion (PHP 8.1+)

Always use trailing comma after last parameter:

```php
public function __construct(
    private readonly DocumentRepository $documentRepository,
    private readonly Dispatcher $eventDispatcher,
) {
}
```

Single parameter (no trailing comma needed):

```php
public function __construct(private readonly Post $post)
{
}
```

## Namespace Imports

- One `use` statement per line
- Order alphabetically
- Remove unused imports
- Use `as` keyword for conflicts

```php
use Folder\Exception\V2\Exception\ConflictException;
use SignNow\ORM\Model\Document\DocumentGroupInviteStep as BaseDocumentGroupInviteStep;
```

## Arrays

- Short syntax `[]` only
- **Do not align** values (1 space after `=>`)
- Always trailing comma on last element

```php
$array = [
    'first' => [
        'description' => 'Test desc',
        'name' => 'Test',
    ],
    'second' => [
        'description' => 'Test desc',
        'name' => 'Test',
    ],
];
```

## Strings

- Prefer **single quotes** for literals
- Space around concatenation operator `.`
- Variable interpolation with double quotes is acceptable
- Use `sprintf()` for complex strings

```php
$neos = 'A great project from a great team';
$message = 'Hey ' . $name . ', you look ' . $appearance . ' today!';
$message = "Hey {$name}, you look {$appearance} today!";
$message = sprintf('Hey %s, you look %s today!', $name, $appearance);
```

Multi-line concatenation:

```php
$neos = 'A great ' .
    'project from ' .
    'a great ' .
    'team';
```

## Type Declarations

- Always use strict types
- Specify all parameter and return types
- Space after type cast: `(int) $value`

## Documentation

### When to Document
- `@throws` for exceptions only
- Complex business logic explanations
- Non-obvious algorithm descriptions

### When NOT to Document
- Redundant type info (already in signature)
- Self-explanatory methods
- `@package` annotation (not standard)

### Exception Documentation Rules
- Import exception if directly thrown in method
- Use FQCN if not directly used

```php
/**
 * @throws \Folder\Exception\V2\Exception\ConflictException
 */
public function process(Post $post): void
{
    return $this->service->proceed();
}
```

```php
/**
 * @throws ConflictException
 */
public function process(Post $post): void
{
    if ($condition) {
        throw new ConflictException();
    }
}
```

### @param Format
- Type and name separated by **one space**
- **No alignment**, **no colon** after parameter name

```php
/**
 * A description for this method
 *
 * @param Post $post Some description for the $post parameter
 * @param string $someString Some description for the $someString parameter
 */
public function addStringToPost(Post $post, string $someString): void
```

## Class Properties

- No PHPDoc block unless necessary
- No blank line between properties

```php
private string $name;
private mixed $text;
private Model $class;
```

## Exception Naming

- Generic: namespace + `Exception` (e.g., `\SignNow\ObjectManagement\Exception`)
- Specific: sub-namespace + `*Exception` (e.g., `\SignNow\Flow\ObjectManagement\Exception\InvalidClassNameException`)

## Constants Best Practices

Use constants for regex patterns:

```php
private const PATTERN_MATCH_EMAIL_ADDRESS = '/...pattern.../';
private const PATTERN_MATCH_VALID_HTML_TAGS = '/...pattern.../';
```

## Complete Example

```php
<?php
declare(strict_types = 1);

namespace Document\Services\Document\Dimensions;

use Core\Event\Event\DocumentHistoryEvent;
use Document\Exception\NotReadableException as DocumentNotReadableException;
use Document\Services\Document\Dimensions\DocumentService;
use Document\Services\Document\Dimensions\HistoryCollectorInterface;
use Illuminate\Contracts\Events\Dispatcher;
use ORM\Repository\DocumentDimensionsRepository;

class DocumentDimensionsService extends DocumentService implements HistoryCollectorInterface
{
    private const PER_PAGE = 15;
    private const VERIFICATION_SCOPE = [
        'close_redirect_uri',
    ];

    public function __construct(
        private readonly DocumentDimensionsRepository $documentDimensionsRepository,
        private readonly Dispatcher $eventDispatcher,
    ) {
    }

    /**
     * @throws DocumentNotReadableException
     */
    public function createDocumentViewed(User $user, Document $document): Document
    {
        if (in_array(self::VERIFICATION_SCOPE, $document->getScopeLink()) === false
            && $this->checkPermissions($document, $user) === false
        ) {
            throw new DocumentNotReadableException();
        }

        // ...
    }

    public function createHistoryEvent(
        string $eventName,
        User $user,
        Document $document,
        ?int $clientTimestamp
    ): DocumentHistoryEvent {
        $historyEvent = new DocumentHistoryEvent($document, $user, $eventName, $clientTimestamp);

        $this->eventDispatcher->dispatch($historyEvent);
    }
}
```
