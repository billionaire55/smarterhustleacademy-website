# Money Academy static files

This directory contains the standalone Money Academy learning pages prepared for Smarter Hustle Academy. Upload the entire `money-academy/` directory to the website repository without renaming the files.

## Upload file table

| File | Purpose | Website path |
| --- | --- | --- |
| `index.html` | Money Academy directory page linking to all three levels | `/money-academy/` |
| `money-starter.html` | Money Starter course | `/money-academy/money-starter.html` |
| `money-independent.html` | Money Independent course | `/money-academy/money-independent.html` |
| `money-builder.html` | Money Builder course, including tax and retirement learning tools | `/money-academy/money-builder.html` |

## Add a link to the existing site

Add a navigation or homepage link pointing to `/money-academy/`, for example:

```html
<a href="/money-academy/">Money Academy</a>
```

The pages are self-contained and do not require a build step, npm packages, or external image files. They can be served by a static host such as the current website hosting setup.

## Scope note

These static files provide the standalone lesson experience. The separate full-stack Money Academy project contains OAuth authentication, database-backed learner persistence, educator analytics, and synchronized progress. Those features require deploying the full-stack project and are not activated by copying HTML files alone.
