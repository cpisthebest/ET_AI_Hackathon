# Point-in-time regulatory queries

The model stores `effective_from` and `effective_to` on regulation versions and obligations.

Conceptually, a point-in-time assessment uses:

```sql
SELECT *
FROM regulation_versions
WHERE effective_from <= :as_of
  AND (effective_to IS NULL OR effective_to > :as_of);
```

This prevents a current regulation from being incorrectly applied to a historical control assessment.

For a production implementation, the same temporal predicate should be applied to obligations and mappings, and assessment runs should persist the `as_of` date plus the exact source version IDs used.
