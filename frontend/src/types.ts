/** Shapes returned by the FastAPI backend. These mirror the database columns. */

/**
 * The fields a product card needs to render. Both the catalogue endpoint and
 * the agent's chat results satisfy this, so one ProductCard component renders
 * both — and dynamically generated cards behave exactly like catalogue ones.
 */
export interface ProductCardData {
  product_id: string
  name: string
  garment_type: string
  description: string
  image_url: string
  price: number
  total_stock: number
  /** Colour names from the catalogue, rendered as swatch dots on the card. */
  colors?: string[]
}

export interface Product extends ProductCardData {
  colors: string[]
  search_tags: string[]
  image_file_path: string
}

export interface InventoryRow {
  size: string
  quantity: number
}

export interface ProductDetail extends Product {
  inventory: InventoryRow[]
}

export interface ProductListResponse {
  count: number
  products: Product[]
}
