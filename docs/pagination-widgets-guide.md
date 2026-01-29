# Pagination Widgets Guide

## Overview

Phase 13.3 introduces a comprehensive set of pagination UI widgets located in `lib/shared/widgets/`:
- `paginated_list_view.dart` - Infinite scroll list views
- `pagination_controls.dart` - Page navigation controls

These widgets work seamlessly with the pagination foundation established in Phase 13.1 and 13.2.

## Quick Start

### Basic Infinite Scroll List

```dart
import 'package:construction_inspector/shared/shared.dart';

class ProjectsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ProjectProvider>();

    return PaginatedListView<Project>(
      items: provider.projects,
      itemBuilder: (context, project) => ProjectCard(project: project),
      onLoadMore: () => provider.loadMore(),
      hasMore: provider.hasMore,
      isLoading: provider.isLoadingMore,
    );
  }
}
```

### With Manual "Load More" Button

```dart
PaginatedListView<Entry>(
  items: entries,
  itemBuilder: (context, entry) => EntryCard(entry: entry),
  onLoadMore: () => entryProvider.loadMore(),
  hasMore: entryProvider.hasMore,
  isLoading: entryProvider.isLoadingMore,
  autoLoad: false,  // Show button instead of auto-loading
)
```

### Custom Empty State

```dart
PaginatedListView<Contractor>(
  items: contractors,
  itemBuilder: (context, contractor) => ContractorTile(contractor: contractor),
  onLoadMore: () => contractorProvider.loadMore(),
  hasMore: contractorProvider.hasMore,
  isLoading: contractorProvider.isLoadingMore,
  emptyMessage: 'No contractors found',
  emptyWidget: CustomEmptyWidget(),
)
```

## Pagination Controls

### Simple Page Info Display

```dart
// Shows "Page 1 of 5"
PaginationInfo(
  currentPage: provider.currentPage,
  totalPages: provider.totalPages,
  format: PaginationInfoFormat.page,
)

// Shows "Showing 1-20 of 100"
PaginationInfo(
  currentPage: provider.currentPage,
  totalPages: provider.totalPages,
  totalItems: provider.totalItems,
  itemsPerPage: provider.itemsPerPage,
  format: PaginationInfoFormat.items,
)

// Shows "1 / 5" (compact)
PaginationInfo(
  currentPage: provider.currentPage,
  totalPages: provider.totalPages,
  format: PaginationInfoFormat.compact,
)
```

### Navigation Buttons

```dart
PaginationButtons(
  currentPage: provider.currentPage,
  totalPages: provider.totalPages,
  onPrevious: () => provider.previousPage(),
  onNext: () => provider.nextPage(),
)
```

### Full Pagination Bar

```dart
// At bottom of screen
PaginationBar(
  currentPage: provider.currentPage,
  totalPages: provider.totalPages,
  totalItems: provider.totalItems,
  itemsPerPage: provider.itemsPerPage,
  onPrevious: () => provider.previousPage(),
  onNext: () => provider.nextPage(),
  format: PaginationInfoFormat.items,
  backgroundColor: AppTheme.surfaceElevated,
)
```

### Dot Indicators (Mobile Carousels)

```dart
PaginationDots(
  currentPage: currentPage,
  totalPages: images.length,
  onPageTapped: (page) => setState(() => currentPage = page),
)
```

### Page Number Selector (Desktop/Tablet)

```dart
PageNumberSelector(
  currentPage: provider.currentPage,
  totalPages: provider.totalPages,
  onPageSelected: (page) => provider.goToPage(page),
  maxVisiblePages: 5,
)
```

## Advanced Usage

### With Sliver Lists

For use in `CustomScrollView`:

```dart
CustomScrollView(
  slivers: [
    SliverAppBar(...),

    PaginatedSliverList<Entry>(
      items: entries,
      itemBuilder: (context, entry) => EntryCard(entry: entry),
      onLoadMore: () => provider.loadMore(),
      hasMore: provider.hasMore,
      isLoading: provider.isLoadingMore,
    ),
  ],
)
```

### Custom Scroll Controller

```dart
final scrollController = ScrollController();

PaginatedListView<Project>(
  items: projects,
  itemBuilder: (context, project) => ProjectCard(project: project),
  onLoadMore: () => provider.loadMore(),
  hasMore: provider.hasMore,
  isLoading: provider.isLoadingMore,
  scrollController: scrollController,
  loadThreshold: 0.7,  // Load when 70% scrolled
)
```

### With Separators

```dart
PaginatedListView<Location>(
  items: locations,
  itemBuilder: (context, location) => LocationTile(location: location),
  onLoadMore: () => provider.loadMore(),
  hasMore: provider.hasMore,
  isLoading: provider.isLoadingMore,
  separator: Divider(color: AppTheme.surfaceHighlight),
)
```

## Complete Example

Here's a complete screen implementation:

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/projects/presentation/presentation.dart';

class ProjectListScreen extends StatefulWidget {
  const ProjectListScreen({super.key});

  @override
  State<ProjectListScreen> createState() => _ProjectListScreenState();
}

class _ProjectListScreenState extends State<ProjectListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ProjectProvider>().loadProjects();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Projects'),
      ),
      body: Consumer<ProjectProvider>(
        builder: (context, provider, _) {
          if (provider.isLoading && provider.projects.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }

          return Column(
            children: [
              // Main list
              Expanded(
                child: PaginatedListView<Project>(
                  items: provider.projects,
                  itemBuilder: (context, project) {
                    return ProjectCard(
                      project: project,
                      onTap: () => _openProject(context, project),
                    );
                  },
                  onLoadMore: () => provider.loadMore(),
                  hasMore: provider.hasMore,
                  isLoading: provider.isLoadingMore,
                  emptyMessage: 'No projects found',
                  separator: const SizedBox(height: 8),
                ),
              ),

              // Pagination info bar
              if (provider.projects.isNotEmpty)
                PaginationBar(
                  currentPage: provider.currentPage,
                  totalPages: provider.totalPages,
                  totalItems: provider.totalItems,
                  itemsPerPage: provider.itemsPerPage,
                  onPrevious: () => provider.previousPage(),
                  onNext: () => provider.nextPage(),
                  backgroundColor: AppTheme.surfaceElevated,
                ),
            ],
          );
        },
      ),
    );
  }

  void _openProject(BuildContext context, Project project) {
    // Navigation logic
  }
}
```

## Provider Requirements

Your provider should implement the `PaginatedProvider` mixin from Phase 13.1:

```dart
class ProjectProvider extends ChangeNotifier with PaginatedProvider {
  List<Project> _projects = [];

  List<Project> get projects => _projects;

  Future<void> loadProjects() async {
    await loadInitialPage(() async {
      final results = await _repository.getProjects(
        offset: 0,
        limit: itemsPerPage,
      );
      _projects = results.items;
      return results;
    });
  }

  Future<void> loadMore() async {
    await loadNextPage(() async {
      final results = await _repository.getProjects(
        offset: _projects.length,
        limit: itemsPerPage,
      );
      _projects.addAll(results.items);
      return results;
    });
  }

  Future<void> nextPage() async {
    await goToNextPage(() async {
      final results = await _repository.getProjects(
        offset: (currentPage) * itemsPerPage,
        limit: itemsPerPage,
      );
      _projects = results.items;
      return results;
    });
  }

  Future<void> previousPage() async {
    await goToPreviousPage(() async {
      final results = await _repository.getProjects(
        offset: (currentPage - 2) * itemsPerPage,
        limit: itemsPerPage,
      );
      _projects = results.items;
      return results;
    });
  }
}
```

## Widget Features Summary

### PaginatedListView
- Generic type support (`PaginatedListView<T>`)
- Auto-loading on scroll (configurable threshold)
- Manual "Load More" button mode
- Custom empty state
- Separator support
- Custom scroll controller
- Loading indicators

### PaginatedSliverList
- Sliver version for `CustomScrollView`
- Auto-loading on scroll
- Same generic type support

### PaginationInfo
- Multiple formats: page, items, compact
- Customizable text style

### PaginationButtons
- Previous/Next navigation
- Auto-disable on first/last page
- Customizable size and icons

### PaginationBar
- Combined info + buttons
- Horizontal or vertical layout
- Optional background color
- Customizable padding

### PaginationDots
- Mobile-friendly page indicators
- Animated transitions
- Tap to navigate
- Customizable colors and size

### PageNumberSelector
- Desktop/tablet page selection
- Smart ellipsis for large page counts
- Highlighted current page
- Clickable page numbers

## Best Practices

1. **Use infinite scroll for mobile**: Better UX than page buttons on small screens
2. **Use page controls for desktop**: Better for precise navigation
3. **Show pagination info**: Users appreciate knowing where they are
4. **Handle empty states**: Always provide feedback when no items exist
5. **Loading indicators**: Show progress during data fetch
6. **Responsive design**: Consider screen size when choosing widgets
7. **Accessibility**: Pagination widgets follow Material 3 guidelines

## File Locations

- `lib/shared/widgets/paginated_list_view.dart` - List views
- `lib/shared/widgets/pagination_controls.dart` - Controls
- `lib/shared/widgets/widgets.dart` - Barrel export

## Related Documentation

- Phase 13.1: Pagination Foundation
- Phase 13.2: Repository Pattern Updates
- `lib/shared/providers/paginated_provider.dart` - Provider mixin
