-- inventory table
CREATE TABLE IF NOT EXISTS inventory (
  name          TEXT  PRIMARY KEY,
  qty           REAL  NOT NULL CHECK (qty >= 0),
  price_per_kg  REAL  NOT NULL CHECK (price_per_kg >= 0)
);

-- orders table
CREATE TABLE IF NOT EXISTS orders  (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  phone TEXT,
  address TEXT,
  order_details TEXT,
  datetime TEXT
);

-- feedback table
CREATE TABLE IF NOT EXISTS feedback (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id  INTEGER REFERENCES orders(id) ON DELETE CASCADE,
  rating    INTEGER CHECK (rating BETWEEN 1 AND 5),
  comments  TEXT
);

-- seed inventory
INSERT OR IGNORE INTO inventory (name, qty, price_per_kg) VALUES
  ('tomato',  40, 30),
  ('potato',  50, 25),
  ('spinach', 20, 18),
  ('onion',   35, 28),
  ('carrot',  25, 22);
