import api from "./api.js";

function mapRow(row) {
  return {
    id: row.id,
    name: row.name,
    category: row.category,
    unit: row.unit,
    photo: row.photo,
    imageData: row.image_data,
    indivPrice: Number(row.indiv_price),
    bizPrice: Number(row.biz_price),
    minBulkQty: row.min_bulk_qty,
    farmer: row.farmer,
    farmerAdded: row.farmer_added,
    createdAt: row.created_at,
  };
}

export async function getProducts() {
  const { data } = await api.get("/products?order=created_at.asc");
  return data.map(mapRow);
}

export async function createProduct(product) {
  const payload = {
    name: product.name,
    category: product.category,
    unit: product.unit,
    photo: product.photo || null,
    image_data: product.imageData || null,
    indiv_price: product.indivPrice,
    biz_price: product.bizPrice,
    min_bulk_qty: product.minBulkQty,
    farmer: product.farmer,
    farmer_added: true,
  };
  const { data } = await api.post("/products", payload, {
    headers: { Prefer: "return=representation" },
  });
  return data.length > 0 ? mapRow(data[0]) : null;
}

export async function deleteProduct(id) {
  await api.delete(`/products?id=eq.${encodeURIComponent(id)}`);
  return true;
}
