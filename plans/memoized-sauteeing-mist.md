# Field Guide App - Product Overview

**Last Updated**: 2026-01-22 | **Version**: Pre-Beta

---

## Product Summary

Field Guide is a cross-platform mobile and desktop application designed specifically for construction inspectors. Built with an **offline-first architecture**, it enables inspectors to document daily activities, track material quantities, capture photos, and generate professional PDF reports—all without requiring constant internet connectivity.

### Target Users
- MDOT Construction Inspectors
- DOT Field Engineers
- Quality Assurance Personnel
- Project Supervisors

### Key Value Proposition
> Replace paper-based inspection logs with a modern, field-tested digital solution that works offline, syncs automatically, and produces professional reports.

---

## Core Features

### 1. Daily Inspection Reports (IDRs)
Create comprehensive daily inspection reports with structured data entry for activities, weather, personnel, and materials.

| Capability | Description |
|------------|-------------|
| Activity Logging | Document work performed with timestamps |
| Personnel Tracking | Record contractor and inspector personnel on-site |
| Weather Integration | Automatic weather data capture |
| Material Quantities | Track bid items and material usage |
| Notes & Observations | Free-form documentation |

### 2. Photo Management
Capture, annotate, and organize site photos directly linked to daily entries.

- Camera integration with automatic geo-tagging
- Photo notes and annotations
- Organized by project and entry date
- Included in PDF exports

### 3. PDF Export
Generate professional, print-ready inspection reports.

- Template-based PDF generation
- Matches official IDR formats
- Includes photos, quantities, and signatures
- Export to share or print

### 4. Project Management
Organize work by project with all related data in one place.

- Project setup and configuration
- Location management
- Contractor assignments
- Bid item tracking

### 5. Material Quantities
Track installed quantities against bid items.

- Bid item import
- Daily quantity entry
- Running totals and summaries
- Integration with calculators (planned)

### 6. Offline-First Architecture
Full functionality without internet connection.

- All data stored locally first
- Background sync when connected
- Conflict resolution built-in
- No data loss during outages

### 7. Cloud Sync
Secure synchronization across devices.

- Supabase backend
- Real-time sync when online
- Multi-device support
- Encrypted data transfer

---

## Platform Support

### Mobile
| Platform | Minimum Version | Notes |
|----------|-----------------|-------|
| Android | 7.0 (API 24) | Optimized for field tablets |
| iOS | 15.0 | iPhone and iPad support |

### Technical Specifications
| Component | Version |
|-----------|---------|
| Flutter | 3.38+ |
| Dart | 3.10+ |
| Android compileSdk | 36 (Android 16) |
| Android targetSdk | 35 (Android 15) |
| Gradle | 8.14 |
| Kotlin | 2.2.20 |

---

## User Experience

### Theme Modes
Three accessibility-focused themes optimized for field conditions:

| Mode | Use Case |
|------|----------|
| **Light** | Indoor use, well-lit conditions |
| **Dark** | Low-light, battery saving |
| **High Contrast** | Outdoor visibility, accessibility |

### Field-Optimized Design
- Large touch targets for glove-friendly use
- High contrast colors for outdoor visibility
- Minimal scrolling on key screens
- Quick-access actions for common tasks

---

## Upcoming Features

### Inspector Toolbox (In Development)
A comprehensive digital toolbox replacing physical calculators and reference sheets.

#### Calculators
| Calculator | Purpose |
|------------|---------|
| HMA Tonnage | Calculate asphalt tonnage from area/thickness |
| Concrete Volume | Slab, wall, column, footing volumes |
| Compaction | Percent, density, lift thickness |
| Aggregate | Tonnage/volume with density presets |
| Grade/Slope | Percent, ratio, degrees conversion |
| Rebar | Weight, quantity, lap length |
| Paint/Coating | Coverage per gallon |
| Unit Converter | Length, area, volume, weight, temp |

#### Reference Guides
- Material Density Tables
- Compaction Requirements
- Lift Thickness Guide
- Weather Restrictions
- MDOT Spec Quick Reference

#### Checklists
- Pre-Paving Checklist
- Density Test Checklist
- SESC Inspection
- End-of-Day Checklist

#### Templates
- Activity Description Templates
- Deficiency Note Templates
- Weather Delay Notes

### AASHTOWare Integration (Planned)
Direct integration with MDOT's AASHTOWare system for data exchange.

---

## Pricing

### Competitive Positioning
Field Guide is priced competitively against industry alternatives:

| Competitor | Starting Price |
|------------|----------------|
| Fieldwire | $0-89/user/month |
| PlanGrid | $39-119/user/month |
| Procore | ~$375/month entry |
| SafetyCulture | $24-29/user/month |
| **Field Guide** | **$19/user/month** |

### Pricing Tiers

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 1 user, 1 project, local storage only |
| **Pro** | $19/user/month | Full features, cloud sync, 5 projects |
| **Team** | $29/user/month | Unlimited projects, priority support |
| **Enterprise** | Custom | SSO, SLA, dedicated support |

*Annual billing: 17% discount*

### Feature Comparison

| Feature | Free | Pro | Team |
|---------|------|-----|------|
| Projects | 1 | 5 | Unlimited |
| Cloud Sync | No | Yes | Yes |
| PDF Export | Basic | Full | Full |
| Photo Storage | Local | Cloud | Cloud |
| Toolbox Calculators | Basic | Full | Full |
| Priority Support | No | No | Yes |
| Admin Dashboard | No | No | Yes |

---

## Development Status

### Current State
| Metric | Value |
|--------|-------|
| Phase | Pre-Beta |
| Features Complete | 12 core features |
| Tests Passing | 363 unit/widget tests |
| E2E Coverage | 5 user journeys |
| Code Review Score | 6/10 |

### Recent Improvements (Jan 2026)
- Removed hardcoded developer values
- Documented deep link handling
- Complete E2E test framework with Patrol
- Updated to 2026 platform standards
- Improved test reliability and batching

### Release Blockers
| Blocker | Status | Priority |
|---------|--------|----------|
| ~~Hardcoded name~~ | Fixed | ~~Critical~~ |
| ~~Deep link docs~~ | Fixed | ~~High~~ |
| Pagination | Pending | **Critical** |
| Screen tests | Pending | Medium |

### Roadmap to Beta

**Week 1-2: Foundation**
- Add pagination to all list queries
- Create Toolbox feature structure
- Implement core calculators

**Week 3-4: Features**
- Complete Toolbox calculators
- Reference guides and checklists
- Integration with quantities

**Week 5-6: Polish**
- E2E testing on devices
- Bug fixes and refinements
- Performance optimization

**Week 7-8: Beta Prep**
- Documentation updates
- Final testing
- Beta release

---

## Technical Architecture

### Data Flow
```
Screen → Provider → Repository → SQLite (local) → Supabase (sync)
```

### Key Patterns
| Pattern | Implementation |
|---------|----------------|
| State Management | Provider (ChangeNotifier) |
| Navigation | GoRouter (declarative) |
| Local Storage | SQLite via sqflite |
| Cloud Backend | Supabase (PostgreSQL) |
| PDF Generation | Syncfusion Flutter PDF |
| Offline-First | Local-first with sync queue |

### Feature Organization
```
lib/features/
├── auth/          # Authentication flows
├── contractors/   # Personnel management
├── dashboard/     # Project overview
├── entries/       # Daily inspection reports
├── locations/     # Project locations
├── pdf/           # PDF generation
├── photos/        # Photo capture/management
├── projects/      # Project configuration
├── quantities/    # Material tracking
├── settings/      # User preferences
├── sync/          # Cloud synchronization
└── weather/       # Weather integration
```

---

## Security

### Authentication
- Supabase Auth with magic link support
- Secure token storage (flutter_secure_storage)
- Session management with refresh

### Data Protection
- Local SQLite with app-level encryption
- TLS for all cloud communications
- Row-Level Security (RLS) in Supabase
- No sensitive data in logs

### Credentials
- Environment variables for all secrets
- No hardcoded API keys or tokens
- Proper credential handling in CI/CD

---

## Quality Metrics

### Code Quality
| Metric | Status |
|--------|--------|
| Flutter Analyzer | 0 errors, 10 info warnings |
| Async Safety | 44 mounted checks |
| Test Coverage | Models/Repos: Good, Screens: Pending |

### Architecture Assessment
| Category | Score | Notes |
|----------|-------|-------|
| Architecture | 7/10 | Feature-first, good patterns |
| Security | 8/10 | Proper credential handling |
| Performance | 5/10 | Pagination needed |
| Testing | 4/10 | Screen tests missing |
| Code Quality | 6/10 | Some refactoring needed |

### Known Technical Debt
| Issue | Impact | Priority |
|-------|--------|----------|
| Mega-screens (2700+ lines) | Maintainability | Medium |
| No pagination | Performance | Critical |
| Legacy barrel exports | Cleanup | Low |

---

## Competitive Advantages

### What Sets Field Guide Apart

1. **True Offline-First**
   - Not just "works offline sometimes"
   - Full feature set without connectivity
   - Smart sync when back online

2. **Construction-Specific**
   - Built for inspectors, not adapted
   - MDOT/DOT workflow alignment
   - Industry-standard formulas and formats

3. **Affordable**
   - 50-80% cheaper than competitors
   - No per-project fees
   - Free tier for evaluation

4. **Modern Tech Stack**
   - Cross-platform (one codebase)
   - Regular updates
   - 2026 platform standards

5. **Inspector Toolbox** (Coming)
   - Calculators inspectors actually use
   - Reference data at fingertips
   - Replaces paper reference sheets

---

## Resources

### Documentation
| Document | Location |
|----------|----------|
| Session State | `.claude/plans/_state.md` |
| Toolbox Plan | `.claude/plans/memoized-sauteeing-mist-agent-a98b468.md` |
| Architecture | `.claude/docs/architectural_patterns.md` |
| Defects Log | `.claude/memory/defects.md` |

### Repositories
| Repo | URL |
|------|-----|
| App Code | https://github.com/RobertoChavez2433/construction-inspector-tracking-app |
| Claude Config | https://github.com/RobertoChavez2433/field-guide-claude-config |

---

## Open Questions

1. **Pricing**: Implement volume discounts (10+ users: 15% off, 25+ users: 25% off)?

2. **Testing Priority**: Which devices for E2E validation (Android phone, tablet, iOS)?

3. **Reference Data**: MDOT-specific tables or generic AASHTO standards for Toolbox?

---

## Contact

**Developer**: Robert Sebastian
**Project**: Field Guide - Construction Inspector App
**Target Market**: Michigan DOT and similar state DOTs

---

*This document reflects the current state of Field Guide as of January 2026. For implementation details, see the linked technical documentation.*
