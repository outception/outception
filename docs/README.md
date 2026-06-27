# Outception docs

Using Mintlify.

**Core concepts**
- `docs.json` contains [navigation](https://mintlify.com/docs/navigation/overview), [redirects](https://mintlify.com/docs/settings/broken-links) and core settings

## Development

**Installation**
```bash Terminal
pnpm install
```

**Development Server**
```bash Terminal
pnpm dev
```

### Update schema and webhooks

We have a script that takes care of:

* Downloading the latest OpenAPI schema
* Generate missing webhooks schema pages
    * By default, new pages are added at the bottom of the `Webhooks Events` navigation section, but you can move them to a specific group if needed.
    * Existing pages are not updated, so you can safely edit them without losing your changes.

The schema is served by the API itself (`outception.app.openapi()`):

```bash Terminal
./update-schema.sh https://api.outception.com/openapi.json
```

The script is run automatically by the CI pipeline every day and opens a PR if there are changes.
