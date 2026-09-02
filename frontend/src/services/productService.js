import api from "./api.js";

export async function getProducts() {
  const { data } = await api.get("/products");
  return data.data;
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
  return data.data;
}

export async function deleteProduct(id) {
  await api.delete(`/products/${id}`);
  return true;
}

export async function seedProducts() {
  const { data } = await api.post("/products/seed");
  return data.data;
}
