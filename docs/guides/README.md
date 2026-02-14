# Implementation Guides

How-to guides and reference documentation for implementing features and running tests.

## Testing Guides

Quick reference and setup instructions for manual and automated testing.

| Guide | Purpose | Used By |
|-------|---------|---------|
| [Manual Testing Checklist](testing/manual-testing-checklist.md) | 168-point QA coverage across all features | qa-testing-agent |
| [E2E Test Setup](testing/e2e-test-setup.md) | Patrol E2E test environment configuration and troubleshooting | qa-testing-agent, planning-agent |

## Implementation Guides

Technical how-to guides for common features and patterns.

| Guide | Purpose | Used By |
|-------|---------|---------|
| [Pagination Widgets Guide](implementation/pagination-widgets-guide.md) | Using pagination UI components and infinite scroll lists | frontend-flutter-specialist-agent |
| [Chunked Sync Usage](implementation/chunked-sync-usage.md) | Configuring and using chunked data sync with progress tracking | backend-supabase-agent |

## How Agents Reference These

Agents load relevant implementation guides based on their specialization:

### Frontend Agent
- Uses `guides/implementation/pagination-widgets-guide.md` for list UI patterns

### Backend Supabase Agent
- Uses `guides/implementation/chunked-sync-usage.md` for large dataset sync

### QA Testing Agent
- Uses both `guides/testing/*` for test setup and verification

## When to Use Each Guide

**Implementing a new feature list?** → Pagination Widgets Guide

**Handling large data syncs?** → Chunked Sync Usage

**Setting up or debugging tests?** → E2E Test Setup

**Running manual QA coverage?** → Manual Testing Checklist

## Related Resources

- [Feature Documentation](../features/) - Feature overviews and architecture
- [Product Requirements](../../prds/) - PRDs for all 13 features
- [Architecture Decisions](../../architecture-decisions/) - Constraints and patterns per feature
