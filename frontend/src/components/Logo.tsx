/**
 * The Campus Customs mark: a collegiate shield carrying a "CC" monogram above
 * an open book, with the founding year on a banner beneath.
 *
 * Drawn as inline SVG rather than an image file so it stays crisp at any size,
 * inherits colour from CSS, and costs no extra request. `tone="light"` renders
 * it for the dark footer.
 */
export default function Logo({
  size = 40,
  tone = 'dark',
}: {
  size?: number
  tone?: 'dark' | 'light'
}) {
  const shield = tone === 'light' ? '#f2efe8' : 'var(--blue)'
  const detail = tone === 'light' ? 'var(--blue)' : '#ffffff'
  const accent = tone === 'light' ? 'var(--blue)' : 'var(--paper-2)'

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="Campus Customs"
      focusable="false"
    >
      {/* Shield */}
      <path
        d="M32 3 59 11v23c0 12.6-8.6 22.3-27 30C13.6 56.3 5 46.6 5 34V11L32 3Z"
        fill={shield}
      />
      <path
        d="M32 7.3 54.8 14v20c0 10.5-7.2 18.8-22.8 25.4C16.4 52.8 9.2 44.5 9.2 34V14L32 7.3Z"
        fill="none"
        stroke={detail}
        strokeOpacity="0.45"
        strokeWidth="1.4"
      />

      {/* CC monogram */}
      <g fill="none" stroke={detail} strokeWidth="3.6" strokeLinecap="round">
        <path d="M31 19.5a8.2 8.2 0 1 0 0 13.4" />
        <path d="M43 19.5a8.2 8.2 0 1 0 0 13.4" />
      </g>

      {/* Open book */}
      <g fill={detail}>
        <path d="M17 39.2c4.2-1.9 9.2-1.9 13.4 0v8.6c-4.2-1.9-9.2-1.9-13.4 0v-8.6Z" opacity="0.95" />
        <path d="M33.6 39.2c4.2-1.9 9.2-1.9 13.4 0v8.6c-4.2-1.9-9.2-1.9-13.4 0v-8.6Z" opacity="0.95" />
      </g>
      <path d="M32 38.4v9.8" stroke={shield} strokeWidth="1.8" strokeLinecap="round" />

      {/* Founding year */}
      <text
        x="32"
        y="55.4"
        textAnchor="middle"
        fontFamily="Fraunces, Georgia, serif"
        fontSize="7.4"
        fontWeight="700"
        letterSpacing="0.6"
        fill={accent}
      >
        1975
      </text>
    </svg>
  )
}
