# SQL Cookbook for Supabase

## Schema Migrations

Create migrations in `supabase/migrations/` with timestamp naming:
```bash
supabase migration new add_caption_to_photos
# Creates: supabase/migrations/20260114000000_add_caption_to_photos.sql
```

Migration file format:
```sql
-- Add column
ALTER TABLE photos ADD COLUMN IF NOT EXISTS caption TEXT;

-- Add index
CREATE INDEX IF NOT EXISTS idx_photos_caption ON photos(caption);

-- Add constraint
ALTER TABLE photos ADD CONSTRAINT check_filename_not_empty
  CHECK (filename IS NOT NULL AND filename != '');
```

## Performance Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM daily_entries WHERE project_id = 'x';

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes ORDER BY idx_scan DESC;

-- Find slow queries
SELECT query, mean_time, calls FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 10;

-- Check table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::text)) as size
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::text) DESC;
```

## Row Level Security (RLS)

```sql
-- Enable RLS
ALTER TABLE daily_entries ENABLE ROW LEVEL SECURITY;

-- Policy for authenticated users
CREATE POLICY "Users can view own entries" ON daily_entries FOR SELECT
USING (auth.uid() = user_id);

-- Policy for insert
CREATE POLICY "Users can create entries" ON daily_entries FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Policy for service role (bypass RLS)
CREATE POLICY "Service role full access" ON daily_entries
USING (auth.role() = 'service_role');
```

## Storage Buckets

```sql
-- Create storage bucket
INSERT INTO storage.buckets (id, name, public) VALUES ('entry-photos', 'entry-photos', false);

-- Storage policy for uploads
CREATE POLICY "Users can upload photos" ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'entry-photos' AND auth.role() = 'authenticated');

-- Storage policy for downloads
CREATE POLICY "Users can download own photos" ON storage.objects FOR SELECT
USING (bucket_id = 'entry-photos' AND auth.uid()::text = (storage.foldername(name))[1]);
```

## Useful Indexes

```sql
-- Composite index for common queries
CREATE INDEX idx_entries_project_date ON daily_entries(project_id, date DESC);

-- Partial index for pending sync
CREATE INDEX idx_entries_pending ON daily_entries(id) WHERE sync_status = 'pending';

-- GIN index for full-text search
CREATE INDEX idx_entries_activities_search ON daily_entries USING GIN(to_tsvector('english', activities));
```

## Database Functions

```sql
-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_timestamp BEFORE UPDATE ON daily_entries
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Aggregate function for entry counts
CREATE OR REPLACE FUNCTION get_project_stats(p_project_id TEXT)
RETURNS TABLE(total_entries BIGINT, total_locations BIGINT, total_contractors BIGINT) AS $$
BEGIN
  RETURN QUERY SELECT
    (SELECT COUNT(*) FROM daily_entries WHERE project_id = p_project_id),
    (SELECT COUNT(*) FROM locations WHERE project_id = p_project_id),
    (SELECT COUNT(*) FROM contractors WHERE project_id = p_project_id);
END; $$ LANGUAGE plpgsql;
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `PGRST205` | Table not found | Check spelling, run migration |
| `23503` | FK violation | Ensure parent record exists |
| `23505` | Unique violation | Check for duplicate IDs |
| `42501` | RLS policy denied | Check policies or use service role |
| `42P01` | Undefined table | Run pending migrations |
