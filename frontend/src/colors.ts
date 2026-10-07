/**
 * Maps the colour names stored in `catalogue.colors` to swatch values.
 *
 * The database writes colours in plain English ("heather gray", "navy blue").
 * Matching is longest-name-first so "navy blue" wins over "blue", and anything
 * unrecognised falls back to a neutral rather than guessing.
 */
const SWATCHES: Record<string, string> = {
  'heather gray': '#b9bbbd',
  'heather grey': '#b9bbbd',
  'charcoal gray': '#4a4d52',
  'charcoal grey': '#4a4d52',
  'dark heather gray': '#6e7277',
  'light gray': '#d6d7d9',
  'light grey': '#d6d7d9',
  'navy blue': '#14213f',
  'royal blue': '#2b50a1',
  'light blue': '#a9c5e3',
  'forest green': '#2f5041',
  'kelly green': '#3b8f54',
  'burnt orange': '#b4531d',
  'off white': '#f3f1ec',
  maroon: '#6d2230',
  crimson: '#9e2235',
  navy: '#14213f',
  white: '#ffffff',
  black: '#17181a',
  gray: '#9b9ea1',
  grey: '#9b9ea1',
  red: '#a62833',
  blue: '#2b50a1',
  green: '#3b7a53',
  yellow: '#d9a921',
  gold: '#c08f3c',
  cream: '#efe8d8',
  tan: '#cbb292',
  brown: '#6b4a32',
  purple: '#574a86',
  pink: '#d6a2ad',
  silver: '#c9ccce',
}

const KEYS = Object.keys(SWATCHES).sort((a, b) => b.length - a.length)

export function swatchFor(colorName: string): string {
  const name = colorName.trim().toLowerCase()
  if (SWATCHES[name]) return SWATCHES[name]
  const match = KEYS.find((key) => name.includes(key))
  return match ? SWATCHES[match] : '#b7b2a8'
}
