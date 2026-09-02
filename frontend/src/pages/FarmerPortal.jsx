import React, { useState } from "react";
import { Leaf, ArrowLeft, PackagePlus, Trash2, Camera, X } from "lucide-react";
import { CATEGORY_OPTIONS, UNIT_OPTIONS, money } from "../utils/marketplace.js";
import { useProducts } from "../context/ProductContext.jsx";
import ProductPhoto from "../components/ProductPhoto.jsx";

const EMPTY_FORM = {
  name: "",
  category: "Grains",
  unit: "kg",
  indivPrice: "",
  bizPrice: "",
  minBulkQty: "",
  farmerName: "",
  location: "",
  imageData: null,
  imageName: "",
};

const MAX_IMAGE_BYTES = 20 * 1024 * 1024;

function Field({ label, error, children }) {
  return (
    <label className="block mt-4 text-sm">
      <span className="block text-[#5C5842] mb-1">{label}</span>
      {children}
      {error && (
        <span className="block text-xs text-[#C4544A] mt-1">{error}</span>
      )}
    </label>
  );
}

export default function FarmerPortal({ onSwitch }) {
  const { products, addProduct, removeProduct, loading } = useProducts();
  const farmerListings = products.filter((p) => p.farmerAdded);

  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [toast, setToast] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function flashToast(msg) {
    setToast(msg);
    window.clearTimeout(flashToast._t);
    flashToast._t = window.setTimeout(() => setToast(null), 2200);
  }

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handlePhotoChange(ev) {
    const file = ev.target.files && ev.target.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setErrors((e) => ({ ...e, image: "Please choose an image file" }));
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setErrors((e) => ({
        ...e,
        image: "Image is too large — please use one under 20MB",
      }));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setForm((f) => ({
        ...f,
        imageData: reader.result,
        imageName: file.name,
      }));
      setErrors((e) => ({ ...e, image: undefined }));
    };
    reader.onerror = () => {
      setErrors((e) => ({
        ...e,
        image: "Couldn't read that image — try another file",
      }));
    };
    reader.readAsDataURL(file);
  }

  function clearPhoto() {
    setForm((f) => ({ ...f, imageData: null, imageName: "" }));
  }

  function validate() {
    const e = {};
    if (!form.name.trim()) e.name = "Enter a product name";
    if (!form.indivPrice || Number(form.indivPrice) <= 0)
      e.indivPrice = "Enter a household price";
    if (!form.bizPrice || Number(form.bizPrice) <= 0)
      e.bizPrice = "Enter a bulk/business price";
    if (
      form.bizPrice &&
      form.indivPrice &&
      Number(form.bizPrice) >= Number(form.indivPrice)
    )
      e.bizPrice = "Bulk price should be lower than household price";
    if (!form.minBulkQty || Number(form.minBulkQty) <= 0)
      e.minBulkQty = "Enter a minimum bulk quantity";
    if (!form.farmerName.trim()) e.farmerName = "Enter your name";
    if (!form.location.trim()) e.location = "Enter your village/district";
    return e;
  }

  async function handleSubmit(ev) {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length > 0) return;

    setSubmitting(true);
    try {
      const product = {
        name: form.name.trim(),
        category: form.category,
        unit: form.unit,
        photo: `${form.name} ${form.category}`,
        imageData: form.imageData || null,
        indivPrice: Number(form.indivPrice),
        bizPrice: Number(form.bizPrice),
        minBulkQty: Number(form.minBulkQty),
        farmer: `${form.farmerName.trim()}, ${form.location.trim()}`,
      };
      await addProduct(product);
      flashToast(`${product.name} is now live for consumers`);
      setForm((f) => ({
        ...EMPTY_FORM,
        farmerName: f.farmerName,
        location: f.location,
      }));
    } catch (err) {
      flashToast(err.message || "Could not publish product");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(id, name) {
    try {
      await removeProduct(id);
      flashToast(`${name} removed`);
    } catch (err) {
      flashToast(err.message || "Could not remove listing");
    }
  }

  return (
    <div
      className="min-h-screen w-full bg-[#F3ECDD] text-[#2A2820]"
      style={{
        fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
        .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
        .tabular { font-variant-numeric: tabular-nums; }
      `}</style>

      <div className="bg-[#14140F] text-[#F3ECDD]">
        <header className="border-b border-[#33301F]">
          <div className="max-w-6xl mx-auto px-5 py-5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Leaf className="w-6 h-6 text-[#C9A227]" strokeWidth={1.75} />
              <span className="ff-display text-2xl tracking-tight">
                Kheti Seedha
              </span>
              <span className="ml-2 text-[11px] uppercase tracking-wide border border-[#C9A227] text-[#C9A227] px-2 py-0.5">
                Farmer portal
              </span>
            </div>
            <button
              onClick={onSwitch}
              className="flex items-center gap-1.5 px-3 py-2 text-sm border border-[#4A4630] text-[#C9C3AE] hover:border-[#C9A227] hover:text-[#C9A227] transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Switch role
            </button>
          </div>
        </header>
        <section className="max-w-6xl mx-auto px-5 pt-10 pb-8">
          <h1 className="ff-display text-3xl sm:text-4xl leading-[1.1] max-w-xl">
            List a new product for consumers
          </h1>
          <p className="mt-3 text-[15px] text-[#C9C3AE] max-w-lg">
            Set a fair household price and a discounted bulk rate for
            businesses. It appears in the consumer marketplace the moment you
            publish it.
          </p>
        </section>
      </div>

      <main className="max-w-6xl mx-auto px-5 py-8 grid grid-cols-1 lg:grid-cols-5 gap-8">
        <form
          onSubmit={handleSubmit}
          className="lg:col-span-2 border border-[#E4D6A7] bg-[#FBF7EC] p-5 h-fit"
        >
          <h2 className="ff-display text-xl flex items-center gap-2">
            <PackagePlus className="w-5 h-5 text-[#1B3A2B]" /> Product details
          </h2>

          <Field label="Product name" error={errors.name}>
            <input
              value={form.name}
              onChange={(e) => update("name", e.target.value)}
              placeholder="e.g. Sona Masoori Rice"
              className="fm-input"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Category">
              <select
                value={form.category}
                onChange={(e) => update("category", e.target.value)}
                className="fm-input"
              >
                {CATEGORY_OPTIONS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </Field>
            <Field label="Unit">
              <select
                value={form.unit}
                onChange={(e) => update("unit", e.target.value)}
                className="fm-input"
              >
                {UNIT_OPTIONS.map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Household price (₹)" error={errors.indivPrice}>
              <input
                type="number"
                min="0"
                value={form.indivPrice}
                onChange={(e) => update("indivPrice", e.target.value)}
                placeholder="62"
                className="fm-input"
              />
            </Field>
            <Field label="Bulk/business price (₹)" error={errors.bizPrice}>
              <input
                type="number"
                min="0"
                value={form.bizPrice}
                onChange={(e) => update("bizPrice", e.target.value)}
                placeholder="42"
                className="fm-input"
              />
            </Field>
          </div>

          <Field label="Minimum bulk order quantity" error={errors.minBulkQty}>
            <input
              type="number"
              min="0"
              value={form.minBulkQty}
              onChange={(e) => update("minBulkQty", e.target.value)}
              placeholder="50"
              className="fm-input"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Your name" error={errors.farmerName}>
              <input
                value={form.farmerName}
                onChange={(e) => update("farmerName", e.target.value)}
                placeholder="Ravi Kumar"
                className="fm-input"
              />
            </Field>
            <Field label="Village / district" error={errors.location}>
              <input
                value={form.location}
                onChange={(e) => update("location", e.target.value)}
                placeholder="Nalgonda"
                className="fm-input"
              />
            </Field>
          </div>

          <Field label="Product photo" error={errors.image}>
            {form.imageData ? (
              <div className="flex items-center gap-3">
                <img
                  src={form.imageData}
                  alt="Preview"
                  className="w-20 h-20 object-cover border border-[#D8CBA1]"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-[#5C5842] truncate">
                    {form.imageName}
                  </p>
                  <button
                    type="button"
                    onClick={clearPhoto}
                    className="text-xs text-[#8C2E33] hover:text-[#6B1E2B] mt-1"
                  >
                    Remove photo
                  </button>
                </div>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center gap-1.5 border border-dashed border-[#D8CBA1] bg-white py-5 text-center cursor-pointer hover:border-[#1B3A2B]">
                <Camera className="w-5 h-5 text-[#8A8468]" />
                <span className="text-xs text-[#5C5842]">
                  Tap to upload a photo of your product (under 20MB)
                </span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoChange}
                  className="hidden"
                />
              </label>
            )}
            <p className="text-[11px] text-[#8A8468] mt-1">
              No photo? A placeholder image is used until you add one.
            </p>
          </Field>

          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-4 py-2.5 bg-[#1B3A2B] text-[#F3ECDD] text-sm hover:bg-[#14140F] active:bg-[#0E1F17] transition-colors disabled:opacity-60"
          >
            {submitting ? "Publishing…" : "Publish product"}
          </button>

          <style>{`
            .fm-input {
              width: 100%;
              border: 1px solid #D8CBA1;
              background: #FFFFFF;
              padding: 0.5rem 0.65rem;
              font-size: 0.875rem;
              outline: none;
            }
            .fm-input:focus { border-color: #1B3A2B; }
          `}</style>
        </form>

        <div className="lg:col-span-3">
          <h2 className="ff-display text-xl mb-3">
            Your live listings{" "}
            {farmerListings.length > 0 && (
              <span className="text-sm text-[#5C5842]">
                ({farmerListings.length})
              </span>
            )}
          </h2>
          {loading ? (
            <p className="text-sm text-[#5C5842] border border-dashed border-[#D8CBA1] p-6 text-center">
              Loading your listings…
            </p>
          ) : farmerListings.length === 0 ? (
            <p className="text-sm text-[#5C5842] border border-dashed border-[#D8CBA1] p-6 text-center">
              Nothing published yet — add your first product on the left.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {farmerListings.map((p) => (
                <div
                  key={p.id}
                  className="border border-[#E4D6A7] bg-[#FBF7EC] flex flex-col"
                >
                  <ProductPhoto
                    product={p}
                    className="w-full h-32 object-cover"
                  />
                  <div className="p-3 flex-1 flex flex-col">
                    <h3 className="ff-display text-base leading-snug">
                      {p.name}
                    </h3>
                    <p className="text-[11px] text-[#5C5842]">
                      {p.category} · {p.unit}
                    </p>
                    <p className="text-sm tabular mt-1 text-[#1B3A2B]">
                      {money(p.indivPrice)}{" "}
                      <span className="text-[#5C5842]">household</span>
                    </p>
                    <p className="text-xs tabular text-[#8A6D1E]">
                      {money(p.bizPrice)} bulk · min {p.minBulkQty} {p.unit}
                    </p>
                    <button
                      onClick={() => handleRemove(p.id, p.name)}
                      className="mt-auto pt-2 flex items-center gap-1 text-xs text-[#8C2E33] hover:text-[#6B1E2B]"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Remove listing
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {toast && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 bg-[#14140F] text-[#F3ECDD] text-sm px-4 py-2.5 flex items-center gap-2 shadow-lg border border-[#C9A227]/40 z-50">
          {toast}
          <button onClick={() => setToast(null)}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
