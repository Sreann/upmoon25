# Relevant Skills For Lunar Mission Control

This is a curated shortlist of skills that may help with the TanStack/React mission-control dashboard, UI quality, testing, and robotics-adjacent workflows.

These are not installed yet. Review before installing external skill code.

## Recommended First

### 1. find-skills

Use this to keep searching the skill ecosystem as the project evolves.

- Source: `vercel-labs/skills`
- Skill: `find-skills`
- Installs: ~1.5M
- Repository reputation: high
- Use for: discovering and vetting additional skills
- Link: https://skills.sh/vercel-labs/skills/find-skills

Install:

```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

### 2. vercel-react-best-practices

Useful even if we choose TanStack/Vite instead of Next.js, because most rules apply to React performance, rendering, bundle size, and client-side data patterns.

- Source: `vercel-labs/agent-skills`
- Skill: `vercel-react-best-practices`
- Installs: ~390K
- Repository reputation: high
- Use for: React performance, component structure, avoiding heavy renders in a live dashboard
- Link: https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices

Install:

```bash
npx skills add https://github.com/vercel-labs/agent-skills --skill vercel-react-best-practices
```

### 3. web-design-guidelines

Useful for reviewing the mission-control UI for accessibility, layout quality, and interaction polish.

- Source: `vercel-labs/agent-skills`
- Skill: `web-design-guidelines`
- Installs: ~300K
- Repository reputation: high
- Use for: UI review, accessibility review, frontend quality checks
- Link: https://skills.sh/vercel-labs/agent-skills/web-design-guidelines

Install:

```bash
npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines
```

### 4. shadcn

Useful if the dashboard uses shadcn/ui components for tables, cards, controls, dialogs, forms, and charts. Prefer the official shadcn skill over unofficial copies.

- Source: `shadcn/ui`
- Skill: `shadcn`
- Use for: component selection, shadcn CLI workflows, forms, tables, dialogs, dashboards
- Link: https://skills.sh/shadcn/ui/shadcn

Install:

```bash
npx skills add https://github.com/shadcn/ui --skill shadcn
```

### 5. playwright

Useful for testing the new dashboard in a real browser: camera placeholder behavior, reconnect states, command buttons, safety controls, and responsive layout.

- Source: `openai/skills`
- Skill: `playwright`
- Use for: browser automation, screenshots, UI workflow testing
- Link: https://skills.sh/openai/skills/playwright

Install:

```bash
npx skills add https://github.com/openai/skills --skill playwright
```

## TanStack-Specific Candidates

There are TanStack Start skills, but they are less proven than the React/UI/testing skills above.

### tanstack-start

- Source: `jezweb/claude-skills`
- Skill: `tanstack-start`
- Use for: TanStack Start setup, server functions, Cloudflare Workers deployment, migration notes
- Concern: third-party source, much lower ecosystem trust than Vercel/Anthropic/OpenAI/shadcn skills
- Link: https://skills.sh/jezweb/claude-skills/tanstack-start

Install:

```bash
npx skills add https://github.com/jezweb/claude-skills --skill tanstack-start
```

### tanstack-start-best-practices

- Source: `deckardger/tanstack-agent-skills`
- Skill: `tanstack-start-best-practices`
- Use for: server functions, middleware, SSR, auth, deployment patterns
- Concern: third-party source, likely useful but should be reviewed before adoption
- Link: https://skills.sh/deckardger/tanstack-agent-skills/tanstack-start-best-practices

Install:

```bash
npx skills add https://github.com/deckardger/tanstack-agent-skills --skill tanstack-start-best-practices
```

### TanStack Start Skill [DRAFT - NOT READY]

Avoid this one for now.

- Source: `ovachiever/droid-tings`
- Skill: `tanstack-start`
- Status: page explicitly says draft / not ready
- Link: https://skills.sh/ovachiever/droid-tings/tanstack-start

## Lower Priority / Maybe Later

### frontend-design

This is a strong design skill, but its emphasis is bold distinctive interfaces. Our mission-control UI should be dense, restrained, and operational. It may still help with visual polish later, but it is not a first install.

- Source: `anthropics/skills`
- Skill: `frontend-design`
- Installs: ~380K
- Link: https://skills.sh/anthropics/skills/frontend-design

Install:

```bash
npx skills add https://github.com/anthropics/skills --skill frontend-design
```

## Skills I Did Not Find

I did not find high-confidence skills specifically for:

- ROS 2 dashboard development
- rosbridge / roslibjs
- robotics HRI
- point cloud visualization
- TanStack Router without TanStack Start

For these, we should rely on direct project planning and official docs rather than low-confidence skills.

## Suggested Install Order

If we decide to install skills, use this order:

1. `find-skills`
2. `vercel-react-best-practices`
3. `shadcn`
4. `playwright`
5. `web-design-guidelines`
6. `tanstack-start` only if we choose TanStack Start instead of Vite + TanStack Router

## Recommendation For This Project

Use skills to improve implementation quality, not to decide the robot architecture.

Best fit:

- React performance skill for the live dashboard
- shadcn skill if using shadcn/ui
- Playwright skill for browser testing
- TanStack Start skill only after reviewing whether we truly need TanStack Start instead of Vite + TanStack Router

Do not depend on a low-confidence robotics skill. The robotics architecture should stay grounded in our repo, ROS topics, field tests, and the plans in `lunar/.plans`.
