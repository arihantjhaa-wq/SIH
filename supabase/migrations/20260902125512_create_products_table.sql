/*
# Create products table for Kheti Seedha marketplace

1. New Tables
- `products`
  - `id` (uuid, primary key)
  - `name` (text, not null) — product name
  - `category` (text, not null) — e.g. "Grains", "Vegetables"
  - `unit` (text, not null) — e.g. "kg", "litre", "dozen"
  - `photo` (text) — keyword for stock photo lookup
  - `image_data` (text) — base64 data URL for farmer-uploaded photos
  - `indiv_price` (numeric, not null) — household price
  - `biz_price` (numeric, not null) — bulk/business price
  - `min_bulk_qty` (integer, not null) — minimum qty for bulk pricing
  - `farmer` (text, not null) — farmer name and location
  - `farmer_added` (boolean, default false) — true for farmer-published listings
  - `created_at` (timestamptz, default now())

2. Security
- Enable RLS on `products`.
- No-auth app (no sign-in screen), so allow anon + authenticated full CRUD.

3. Notes
- Seeds all 61 original hardcoded products from the frontend.
*/

CREATE TABLE IF NOT EXISTS products (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  category text NOT NULL,
  unit text NOT NULL,
  photo text,
  image_data text,
  indiv_price numeric NOT NULL,
  biz_price numeric NOT NULL,
  min_bulk_qty integer NOT NULL,
  farmer text NOT NULL,
  farmer_added boolean NOT NULL DEFAULT false,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE products ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_products" ON products;
CREATE POLICY "anon_select_products" ON products FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_products" ON products;
CREATE POLICY "anon_insert_products" ON products FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_products" ON products;
CREATE POLICY "anon_update_products" ON products FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_products" ON products;
CREATE POLICY "anon_delete_products" ON products FOR DELETE
  TO anon, authenticated USING (true);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_farmer_added ON products(farmer_added);

INSERT INTO products (name, category, unit, photo, indiv_price, biz_price, min_bulk_qty, farmer, farmer_added) VALUES
('Sona Masoori Rice','Grains','kg','rice grain',62,42,50,'Ravi Kumar, Nalgonda',false),
('Vine-Ripened Tomatoes','Vegetables','kg','tomatoes fresh',38,24,40,'Sunita Devi, Nashik',false),
('Red Onions','Vegetables','kg','red onions',30,19,60,'Prakash Patil, Nashik',false),
('Cold-Pressed Mustard Oil','Oils','litre','mustard oil bottle',210,165,20,'Harpreet Singh, Bathinda',false),
('Turmeric (Whole)','Spices','kg','turmeric root',180,110,25,'Lakshmi Reddy, Erode',false),
('Wheat Atta','Grains','kg','wheat flour',48,34,50,'Bhupinder Sidhu, Ludhiana',false),
('Alphonso Mangoes','Fruits','dozen','mango fruit',650,480,10,'Devendra More, Ratnagiri',false),
('Jaggery Blocks','Sweeteners','kg','jaggery',70,41,30,'Meena Yadav, Muzaffarnagar',false),
('Potatoes','Vegetables','kg','potatoes',26,17,75,'Gurmeet Kaur, Jalandhar',false),
('Kashmiri Saffron','Spices','g','saffron spice',450,300,200,'Abdul Rashid, Pampore',false),
('A2 Desi Cow Ghee','Dairy','kg','ghee butter',950,620,20,'Kishorbhai Patel, Anand',false),
('Raw Forest Honey','Sweeteners','kg','honey jar',520,310,30,'Bimal Mondal, Sundarbans',false),
('Whole Cashews','Nuts','kg','cashew nuts',900,640,25,'Vinayak Sawant, Sindhudurg',false),
('Green Cardamom','Spices','kg','cardamom spice',2200,1450,10,'Thomas Kurian, Idukki',false),
('Malabar Black Pepper','Spices','kg','black pepper spice',650,400,20,'Joseph Mathew, Wayanad',false),
('Finger Millet Flour','Grains','kg','millet flour',55,36,60,'Nagaraju H.S., Mandya',false),
('Kutch Dates','Fruits','kg','dates fruit',480,300,30,'Ismail Jat, Kutch',false),
('Toor Dal','Pulses','kg','lentils dal',140,95,40,'Sharad Deshmukh, Latur',false),
('Chana Dal','Pulses','kg','chickpea lentils',95,62,40,'Anil Chaudhary, Indore',false),
('Moong Dal','Pulses','kg','mung beans',130,85,40,'Rekha Sharma, Rajkot',false),
('Masoor Dal','Pulses','kg','red lentils',110,70,40,'Baldev Singh, Hisar',false),
('Fresh Coriander','Herbs','kg','coriander herb',60,35,20,'Ramesh Yadav, Pune',false),
('Fresh Mint','Herbs','kg','mint herb',70,40,15,'Suresh Vora, Ahmedabad',false),
('Green Chillies','Vegetables','kg','green chillies',45,28,30,'Farida Bee, Guntur',false),
('Capsicum','Vegetables','kg','bell pepper',55,34,30,'Manoj Bhandari, Bengaluru',false),
('Cauliflower','Vegetables','kg','cauliflower vegetable',32,20,40,'Iqbal Sandhu, Ludhiana',false),
('Spinach','Vegetables','kg','spinach leaves',28,17,35,'Kavita Rao, Hyderabad',false),
('Bananas','Fruits','dozen','bananas fruit',55,38,25,'Ganesh Naik, Jalgaon',false),
('Green Grapes','Fruits','kg','green grapes',90,60,30,'Vitthal Pawar, Nashik',false),
('Tender Coconut','Fruits','piece','coconut fruit',35,22,100,'Muthu Raman, Pollachi',false),
('Groundnuts','Nuts','kg','peanuts groundnut',110,72,40,'Digvijay Solanki, Rajkot',false),
('Kashmiri Almonds','Nuts','kg','almonds nuts',850,600,25,'Zorawar Bhatti, Kashmir',false),
('Raisins','Sweeteners','kg','raisins dried fruit',320,210,20,'Devraj Chavan, Nashik',false),
('Basmati Rice','Grains','kg','basmati rice',120,85,40,'Amarjit Gill, Karnal',false),
('Pearl Millet (Bajra)','Grains','kg','millet grain',42,28,60,'Deepak Chaudhary, Jodhpur',false),
('Sorghum (Jowar)','Grains','kg','sorghum grain',44,30,60,'Yogesh Patil, Solapur',false),
('Barley','Grains','kg','barley grain',40,27,60,'Harveen Brar, Amritsar',false),
('Sweet Corn','Grains','kg','corn maize',35,22,50,'Mahesh Jadhav, Nashik',false),
('Groundnut Oil','Oils','litre','peanut oil bottle',195,150,20,'Ketan Vaghela, Junagadh',false),
('Sunflower Oil','Oils','litre','sunflower oil bottle',165,125,20,'Ramanna Gowda, Bellary',false),
('Virgin Coconut Oil','Oils','litre','coconut oil bottle',320,240,15,'Sherin Thomas, Kochi',false),
('Sesame (Til) Oil','Oils','litre','sesame oil bottle',260,195,15,'Chandrakant Naik, Latur',false),
('Cold-Pressed Olive Oil','Oils','litre','olive oil bottle',780,590,10,'Nilgiri Growers Co-op, Coimbatore',false),
('Himachal Apples','Fruits','kg','red apples',180,130,25,'Rohit Thakur, Shimla',false),
('Nagpur Oranges','Fruits','kg','oranges citrus',90,62,30,'Sanjay Deshmukh, Nagpur',false),
('Pomegranate','Fruits','kg','pomegranate fruit',150,105,25,'Vishal Chavan, Solapur',false),
('Watermelon','Fruits','piece','watermelon',60,40,40,'Irfan Shaikh, Karnal',false),
('Papaya','Fruits','kg','papaya fruit',45,28,40,'Lakshman Nair, Salem',false),
('Guava','Fruits','kg','guava fruit',65,42,30,'Om Prakash, Allahabad',false),
('Pineapple','Fruits','piece','pineapple fruit',55,36,30,'Bimol Das, Tripura',false),
('Litchi','Fruits','kg','lychee fruit',220,150,20,'Anand Jha, Muzaffarpur',false),
('Carrots','Vegetables','kg','carrots vegetable',40,25,40,'Balraj Sandhu, Ludhiana',false),
('Cabbage','Vegetables','kg','cabbage vegetable',25,15,45,'Sunil Wagh, Pune',false),
('Brinjal (Eggplant)','Vegetables','kg','eggplant brinjal',35,22,35,'Rajendra Naik, Nagpur',false),
('Beetroot','Vegetables','kg','beetroot vegetable',38,24,30,'Simran Kaur, Jalandhar',false),
('Green Peas','Vegetables','kg','green peas',70,46,25,'Devendra Kushwaha, Agra',false),
('Okra (Bhindi)','Vegetables','kg','okra vegetable',42,27,30,'Fatima Sheikh, Hyderabad',false),
('Cucumber','Vegetables','kg','cucumber vegetable',30,18,35,'Ajay Mali, Nashik',false),
('Pumpkin','Vegetables','kg','pumpkin vegetable',28,17,40,'Geeta Bhoi, Raipur',false),
('Radish','Vegetables','kg','radish vegetable',24,15,35,'Harpal Randhawa, Jalandhar',false),
('Bitter Gourd','Vegetables','kg','bitter gourd vegetable',46,30,25,'Kumari Bai, Bhopal',false)
ON CONFLICT DO NOTHING;
