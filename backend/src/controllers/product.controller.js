import { Product } from "../models/product.model.js";
import { ApiResponse } from "../utils/api-responce.js";
import { ApiError } from "../utils/api-error.js";
import { asyncHandler } from "../utils/async-handler.js";

const SEED_PRODUCTS = [
  { name: "Sona Masoori Rice", category: "Grains", unit: "kg", photo: "rice grain", indivPrice: 62, bizPrice: 42, minBulkQty: 50, farmer: "Ravi Kumar, Nalgonda", farmerAdded: false },
  { name: "Vine-Ripened Tomatoes", category: "Vegetables", unit: "kg", photo: "tomatoes fresh", indivPrice: 38, bizPrice: 24, minBulkQty: 40, farmer: "Sunita Devi, Nashik", farmerAdded: false },
  { name: "Red Onions", category: "Vegetables", unit: "kg", photo: "red onions", indivPrice: 30, bizPrice: 19, minBulkQty: 60, farmer: "Prakash Patil, Nashik", farmerAdded: false },
  { name: "Cold-Pressed Mustard Oil", category: "Oils", unit: "litre", photo: "mustard oil bottle", indivPrice: 210, bizPrice: 165, minBulkQty: 20, farmer: "Harpreet Singh, Bathinda", farmerAdded: false },
  { name: "Turmeric (Whole)", category: "Spices", unit: "kg", photo: "turmeric root", indivPrice: 180, bizPrice: 110, minBulkQty: 25, farmer: "Lakshmi Reddy, Erode", farmerAdded: false },
  { name: "Wheat Atta", category: "Grains", unit: "kg", photo: "wheat flour", indivPrice: 48, bizPrice: 34, minBulkQty: 50, farmer: "Bhupinder Sidhu, Ludhiana", farmerAdded: false },
  { name: "Alphonso Mangoes", category: "Fruits", unit: "dozen", photo: "mango fruit", indivPrice: 650, bizPrice: 480, minBulkQty: 10, farmer: "Devendra More, Ratnagiri", farmerAdded: false },
  { name: "Jaggery Blocks", category: "Sweeteners", unit: "kg", photo: "jaggery", indivPrice: 70, bizPrice: 41, minBulkQty: 30, farmer: "Meena Yadav, Muzaffarnagar", farmerAdded: false },
  { name: "Potatoes", category: "Vegetables", unit: "kg", photo: "potatoes", indivPrice: 26, bizPrice: 17, minBulkQty: 75, farmer: "Gurmeet Kaur, Jalandhar", farmerAdded: false },
  { name: "Kashmiri Saffron", category: "Spices", unit: "g", photo: "saffron spice", indivPrice: 450, bizPrice: 300, minBulkQty: 200, farmer: "Abdul Rashid, Pampore", farmerAdded: false },
  { name: "A2 Desi Cow Ghee", category: "Dairy", unit: "kg", photo: "ghee butter", indivPrice: 950, bizPrice: 620, minBulkQty: 20, farmer: "Kishorbhai Patel, Anand", farmerAdded: false },
  { name: "Raw Forest Honey", category: "Sweeteners", unit: "kg", photo: "honey jar", indivPrice: 520, bizPrice: 310, minBulkQty: 30, farmer: "Bimal Mondal, Sundarbans", farmerAdded: false },
  { name: "Whole Cashews", category: "Nuts", unit: "kg", photo: "cashew nuts", indivPrice: 900, bizPrice: 640, minBulkQty: 25, farmer: "Vinayak Sawant, Sindhudurg", farmerAdded: false },
  { name: "Green Cardamom", category: "Spices", unit: "kg", photo: "cardamom spice", indivPrice: 2200, bizPrice: 1450, minBulkQty: 10, farmer: "Thomas Kurian, Idukki", farmerAdded: false },
  { name: "Malabar Black Pepper", category: "Spices", unit: "kg", photo: "black pepper spice", indivPrice: 650, bizPrice: 400, minBulkQty: 20, farmer: "Joseph Mathew, Wayanad", farmerAdded: false },
  { name: "Finger Millet Flour", category: "Grains", unit: "kg", photo: "millet flour", indivPrice: 55, bizPrice: 36, minBulkQty: 60, farmer: "Nagaraju H.S., Mandya", farmerAdded: false },
  { name: "Kutch Dates", category: "Fruits", unit: "kg", photo: "dates fruit", indivPrice: 480, bizPrice: 300, minBulkQty: 30, farmer: "Ismail Jat, Kutch", farmerAdded: false },
  { name: "Toor Dal", category: "Pulses", unit: "kg", photo: "lentils dal", indivPrice: 140, bizPrice: 95, minBulkQty: 40, farmer: "Sharad Deshmukh, Latur", farmerAdded: false },
  { name: "Chana Dal", category: "Pulses", unit: "kg", photo: "chickpea lentils", indivPrice: 95, bizPrice: 62, minBulkQty: 40, farmer: "Anil Chaudhary, Indore", farmerAdded: false },
  { name: "Moong Dal", category: "Pulses", unit: "kg", photo: "mung beans", indivPrice: 130, bizPrice: 85, minBulkQty: 40, farmer: "Rekha Sharma, Rajkot", farmerAdded: false },
  { name: "Masoor Dal", category: "Pulses", unit: "kg", photo: "red lentils", indivPrice: 110, bizPrice: 70, minBulkQty: 40, farmer: "Baldev Singh, Hisar", farmerAdded: false },
  { name: "Fresh Coriander", category: "Herbs", unit: "kg", photo: "coriander herb", indivPrice: 60, bizPrice: 35, minBulkQty: 20, farmer: "Ramesh Yadav, Pune", farmerAdded: false },
  { name: "Fresh Mint", category: "Herbs", unit: "kg", photo: "mint herb", indivPrice: 70, bizPrice: 40, minBulkQty: 15, farmer: "Suresh Vora, Ahmedabad", farmerAdded: false },
  { name: "Green Chillies", category: "Vegetables", unit: "kg", photo: "green chillies", indivPrice: 45, bizPrice: 28, minBulkQty: 30, farmer: "Farida Bee, Guntur", farmerAdded: false },
  { name: "Capsicum", category: "Vegetables", unit: "kg", photo: "bell pepper", indivPrice: 55, bizPrice: 34, minBulkQty: 30, farmer: "Manoj Bhandari, Bengaluru", farmerAdded: false },
  { name: "Cauliflower", category: "Vegetables", unit: "kg", photo: "cauliflower vegetable", indivPrice: 32, bizPrice: 20, minBulkQty: 40, farmer: "Iqbal Sandhu, Ludhiana", farmerAdded: false },
  { name: "Spinach", category: "Vegetables", unit: "kg", photo: "spinach leaves", indivPrice: 28, bizPrice: 17, minBulkQty: 35, farmer: "Kavita Rao, Hyderabad", farmerAdded: false },
  { name: "Bananas", category: "Fruits", unit: "dozen", photo: "bananas fruit", indivPrice: 55, bizPrice: 38, minBulkQty: 25, farmer: "Ganesh Naik, Jalgaon", farmerAdded: false },
  { name: "Green Grapes", category: "Fruits", unit: "kg", photo: "green grapes", indivPrice: 90, bizPrice: 60, minBulkQty: 30, farmer: "Vitthal Pawar, Nashik", farmerAdded: false },
  { name: "Tender Coconut", category: "Fruits", unit: "piece", photo: "coconut fruit", indivPrice: 35, bizPrice: 22, minBulkQty: 100, farmer: "Muthu Raman, Pollachi", farmerAdded: false },
  { name: "Groundnuts", category: "Nuts", unit: "kg", photo: "peanuts groundnut", indivPrice: 110, bizPrice: 72, minBulkQty: 40, farmer: "Digvijay Solanki, Rajkot", farmerAdded: false },
  { name: "Kashmiri Almonds", category: "Nuts", unit: "kg", photo: "almonds nuts", indivPrice: 850, bizPrice: 600, minBulkQty: 25, farmer: "Zorawar Bhatti, Kashmir", farmerAdded: false },
  { name: "Raisins", category: "Sweeteners", unit: "kg", photo: "raisins dried fruit", indivPrice: 320, bizPrice: 210, minBulkQty: 20, farmer: "Devraj Chavan, Nashik", farmerAdded: false },
  { name: "Basmati Rice", category: "Grains", unit: "kg", photo: "basmati rice", indivPrice: 120, bizPrice: 85, minBulkQty: 40, farmer: "Amarjit Gill, Karnal", farmerAdded: false },
  { name: "Pearl Millet (Bajra)", category: "Grains", unit: "kg", photo: "millet grain", indivPrice: 42, bizPrice: 28, minBulkQty: 60, farmer: "Deepak Chaudhary, Jodhpur", farmerAdded: false },
  { name: "Sorghum (Jowar)", category: "Grains", unit: "kg", photo: "sorghum grain", indivPrice: 44, bizPrice: 30, minBulkQty: 60, farmer: "Yogesh Patil, Solapur", farmerAdded: false },
  { name: "Barley", category: "Grains", unit: "kg", photo: "barley grain", indivPrice: 40, bizPrice: 27, minBulkQty: 60, farmer: "Harveen Brar, Amritsar", farmerAdded: false },
  { name: "Sweet Corn", category: "Grains", unit: "kg", photo: "corn maize", indivPrice: 35, bizPrice: 22, minBulkQty: 50, farmer: "Mahesh Jadhav, Nashik", farmerAdded: false },
  { name: "Groundnut Oil", category: "Oils", unit: "litre", photo: "peanut oil bottle", indivPrice: 195, bizPrice: 150, minBulkQty: 20, farmer: "Ketan Vaghela, Junagadh", farmerAdded: false },
  { name: "Sunflower Oil", category: "Oils", unit: "litre", photo: "sunflower oil bottle", indivPrice: 165, bizPrice: 125, minBulkQty: 20, farmer: "Ramanna Gowda, Bellary", farmerAdded: false },
  { name: "Virgin Coconut Oil", category: "Oils", unit: "litre", photo: "coconut oil bottle", indivPrice: 320, bizPrice: 240, minBulkQty: 15, farmer: "Sherin Thomas, Kochi", farmerAdded: false },
  { name: "Sesame (Til) Oil", category: "Oils", unit: "litre", photo: "sesame oil bottle", indivPrice: 260, bizPrice: 195, minBulkQty: 15, farmer: "Chandrakant Naik, Latur", farmerAdded: false },
  { name: "Cold-Pressed Olive Oil", category: "Oils", unit: "litre", photo: "olive oil bottle", indivPrice: 780, bizPrice: 590, minBulkQty: 10, farmer: "Nilgiri Growers Co-op, Coimbatore", farmerAdded: false },
  { name: "Himachal Apples", category: "Fruits", unit: "kg", photo: "red apples", indivPrice: 180, bizPrice: 130, minBulkQty: 25, farmer: "Rohit Thakur, Shimla", farmerAdded: false },
  { name: "Nagpur Oranges", category: "Fruits", unit: "kg", photo: "oranges citrus", indivPrice: 90, bizPrice: 62, minBulkQty: 30, farmer: "Sanjay Deshmukh, Nagpur", farmerAdded: false },
  { name: "Pomegranate", category: "Fruits", unit: "kg", photo: "pomegranate fruit", indivPrice: 150, bizPrice: 105, minBulkQty: 25, farmer: "Vishal Chavan, Solapur", farmerAdded: false },
  { name: "Watermelon", category: "Fruits", unit: "piece", photo: "watermelon", indivPrice: 60, bizPrice: 40, minBulkQty: 40, farmer: "Irfan Shaikh, Karnal", farmerAdded: false },
  { name: "Papaya", category: "Fruits", unit: "kg", photo: "papaya fruit", indivPrice: 45, bizPrice: 28, minBulkQty: 40, farmer: "Lakshman Nair, Salem", farmerAdded: false },
  { name: "Guava", category: "Fruits", unit: "kg", photo: "guava fruit", indivPrice: 65, bizPrice: 42, minBulkQty: 30, farmer: "Om Prakash, Allahabad", farmerAdded: false },
  { name: "Pineapple", category: "Fruits", unit: "piece", photo: "pineapple fruit", indivPrice: 55, bizPrice: 36, minBulkQty: 30, farmer: "Bimol Das, Tripura", farmerAdded: false },
  { name: "Litchi", category: "Fruits", unit: "kg", photo: "lychee fruit", indivPrice: 220, bizPrice: 150, minBulkQty: 20, farmer: "Anand Jha, Muzaffarpur", farmerAdded: false },
  { name: "Carrots", category: "Vegetables", unit: "kg", photo: "carrots vegetable", indivPrice: 40, bizPrice: 25, minBulkQty: 40, farmer: "Balraj Sandhu, Ludhiana", farmerAdded: false },
  { name: "Cabbage", category: "Vegetables", unit: "kg", photo: "cabbage vegetable", indivPrice: 25, bizPrice: 15, minBulkQty: 45, farmer: "Sunil Wagh, Pune", farmerAdded: false },
  { name: "Brinjal (Eggplant)", category: "Vegetables", unit: "kg", photo: "eggplant brinjal", indivPrice: 35, bizPrice: 22, minBulkQty: 35, farmer: "Rajendra Naik, Nagpur", farmerAdded: false },
  { name: "Beetroot", category: "Vegetables", unit: "kg", photo: "beetroot vegetable", indivPrice: 38, bizPrice: 24, minBulkQty: 30, farmer: "Simran Kaur, Jalandhar", farmerAdded: false },
  { name: "Green Peas", category: "Vegetables", unit: "kg", photo: "green peas", indivPrice: 70, bizPrice: 46, minBulkQty: 25, farmer: "Devendra Kushwaha, Agra", farmerAdded: false },
  { name: "Okra (Bhindi)", category: "Vegetables", unit: "kg", photo: "okra vegetable", indivPrice: 42, bizPrice: 27, minBulkQty: 30, farmer: "Fatima Sheikh, Hyderabad", farmerAdded: false },
  { name: "Cucumber", category: "Vegetables", unit: "kg", photo: "cucumber vegetable", indivPrice: 30, bizPrice: 18, minBulkQty: 35, farmer: "Ajay Mali, Nashik", farmerAdded: false },
  { name: "Pumpkin", category: "Vegetables", unit: "kg", photo: "pumpkin vegetable", indivPrice: 28, bizPrice: 17, minBulkQty: 40, farmer: "Geeta Bhoi, Raipur", farmerAdded: false },
  { name: "Radish", category: "Vegetables", unit: "kg", photo: "radish vegetable", indivPrice: 24, bizPrice: 15, minBulkQty: 35, farmer: "Harpal Randhawa, Jalandhar", farmerAdded: false },
  { name: "Bitter Gourd", category: "Vegetables", unit: "kg", photo: "bitter gourd vegetable", indivPrice: 46, bizPrice: 30, minBulkQty: 25, farmer: "Kumari Bai, Bhopal", farmerAdded: false },
];

const getProducts = asyncHandler(async (req, res) => {
  const products = await Product.find().sort({ createdAt: 1 });

  return res
    .status(200)
    .json(new ApiResponse(200, products, "Products fetched successfully"));
});

const getProductById = asyncHandler(async (req, res) => {
  const { id } = req.params;

  const product = await Product.findById(id);

  if (!product) {
    throw new ApiError(404, "Product not found");
  }

  return res
    .status(200)
    .json(new ApiResponse(200, product, "Product fetched successfully"));
});

const createProduct = asyncHandler(async (req, res) => {
  const { name, category, unit, photo, imageData, indivPrice, bizPrice, minBulkQty, farmer } = req.body;

  if (!name || !category || !unit || !indivPrice || !bizPrice || !minBulkQty || !farmer) {
    throw new ApiError(400, "Missing required fields");
  }

  const product = await Product.create({
    name,
    category,
    unit,
    photo: photo || null,
    imageData: imageData || null,
    indivPrice,
    bizPrice,
    minBulkQty,
    farmer,
    farmerAdded: true,
  });

  return res
    .status(201)
    .json(new ApiResponse(201, product, "Product created successfully"));
});

const deleteProduct = asyncHandler(async (req, res) => {
  const { id } = req.params;

  const product = await Product.findByIdAndDelete(id);

  if (!product) {
    throw new ApiError(404, "Product not found");
  }

  return res
    .status(200)
    .json(new ApiResponse(200, {}, "Product deleted successfully"));
});

const seedProducts = asyncHandler(async (req, res) => {
  const count = await Product.countDocuments();

  if (count > 0) {
    return res
      .status(200)
      .json(new ApiResponse(200, { seeded: count }, "Products already seeded"));
  }

  const products = await Product.insertMany(SEED_PRODUCTS);

  return res
    .status(201)
    .json(new ApiResponse(201, { seeded: products.length }, "Products seeded successfully"));
});

export { getProducts, getProductById, createProduct, deleteProduct, seedProducts };
