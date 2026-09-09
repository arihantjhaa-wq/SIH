import api from "./api.js";

export async function getProducts() {
  const { data } = await api.get("/products");
  // Map MongoDB _id to id for frontend compatibility
  return data.data.map(p => ({ ...p, id: p._id }));
}

// Authenticated farmer's OWN products — scoped server-side by JWT identity.
export async function getMyProducts() {
  const { data } = await api.get("/products/mine");
  return data.data.map(p => ({ ...p, id: p._id }));
}

// Developer/Admin: ALL products (with owner info). Rejected server-side for
// non-developers.
export async function getAdminProducts() {
  const { data } = await api.get("/products/admin");
  return data.data.map(p => ({ ...p, id: p._id }));
}

export async function createProduct(product) {
  const { data } = await api.post("/products", {
    name: product.name,
    category: product.category,
    unit: product.unit,
    photo: product.photo || null,
    imageData: product.imageData || null,
    indivPrice: product.indivPrice,
    bizPrice: product.bizPrice,
    minBulkQty: product.minBulkQty,
    farmer: product.farmer,
  });
  // Map MongoDB _id to id for frontend compatibility
  return { ...data.data, id: data.data._id };
}

export async function deleteProduct(id) {
  await api.delete(`/products/${id}`);
  return true;
}

export async function seedProducts() {
  const { data } = await api.post("/products/seed");
  return data.data;
}
