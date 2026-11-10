CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_products_name_trgm
ON products USING GIN (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_category_trgm
ON products USING GIN (category gin_trgm_ops);
