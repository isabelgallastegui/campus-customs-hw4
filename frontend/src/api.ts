import type { Product, ProductDetail, ProductListResponse } from './types'

/** Vite proxies /api and /media through to the FastAPI backend in dev. */
async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`Request to ${path} failed (${response.status})`)
  }
  return (await response.json()) as T
}

export function fetchProducts(): Promise<ProductListResponse> {
  return getJson<ProductListResponse>('/api/products')
}

export function fetchProduct(productId: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)
}

/** Real catalogue products similar to this one, for "You May Also Like". */
export async function fetchSimilarProducts(productId: string): Promise<Product[]> {
  const data = await getJson<{ products: Product[] }>(
    `/api/products/${encodeURIComponent(productId)}/similar`,
  )
  return data.products ?? []
}

/** Prices come out of the database as a REAL, e.g. 68.0. */
export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}
