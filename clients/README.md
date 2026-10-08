# Outception clients

## What's inside?

This [Turborepo](https://turbo.build/) includes the following packages/apps:

### Apps and Packages

- `apps/web`: the web app, built with [Next.js](https://nextjs.org/)
- `apps/app`: iOS and Android app built with [Expo](https://expo.dev/) and React Native
- `packages/ui`: Shared resources
- `packages/client`: Internal API client generated from OpenAPI spec
- `packages/orbit`: the Orbit design system, components and design tokens
- `packages/news-core`: the client domain layer shared by the web and the app
- `packages/i18n`: the UI strings

Each package/app is 100% [TypeScript](https://www.typescriptlang.org/).

### Install

```bash
pnpm install
```

### Build

To build all apps and packages, run the following command:

```bash
pnpm build
```

### Develop

```bash
pnpm dev
```

### Generate API client from OpenAPI spec

```bash
pnpm generate
```
