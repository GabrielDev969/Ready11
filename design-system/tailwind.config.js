/** ===========================================================================
 *  GSS MONITORING — Tailwind CSS 3 config
 *  ---------------------------------------------------------------------------
 *  Cole este bloco em theme.extend do seu tailwind.config.js (Django).
 *  Os valores espelham design-system/tokens.css 1:1.
 *
 *  USO NAS TEMPLATES DJANGO:
 *    <span class="font-mono text-excellent-fg bg-excellent-bg ...">
 *    <h1 class="text-h1 font-medium tracking-tightish">
 *    <div class="rounded-md shadow-card bg-elev border border-line">
 *
 *  Veja design-system/DJANGO.md para o passo a passo de instalação.
 * ===========================================================================*/

/** @type {import('tailwindcss').Config} */
module.exports = {
  // Ajuste os caminhos para onde ficam suas templates Django:
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
    './**/forms.py',          // se usar classes em widgets
    './static/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // Superfícies
        bg:          '#FAFAF7',
        elev:        '#FFFFFF',
        sunken:      '#F3F2EE',
        inverse:     '#0B0B0D',

        // Texto (use como text-fg, text-fg2, etc.)
        fg:          '#0B0B0D',
        fg2:         '#3D3D42',
        fg3:         '#6E6E76',
        fg4:         '#9C9CA3',
        'on-dark':   '#FAFAF7',
        'on-dark-2': '#B8B8BE',

        // Linhas
        line:         '#E8E6DF',
        'line-2':     '#DAD7CE',
        'line-strong':'#C5C2B7',

        // ---- Semântico: Wellness ----
        'excellent-bg': 'oklch(0.96 0.04 145)',
        'excellent-fg': 'oklch(0.42 0.10 145)',
        'good-bg':      'oklch(0.96 0.03 235)',
        'good-fg':      'oklch(0.40 0.11 235)',
        'warning-bg':   'oklch(0.96 0.05 85)',
        'warning-fg':   'oklch(0.45 0.12 75)',
        'critical-bg':  'oklch(0.95 0.04 25)',
        'critical-fg':  'oklch(0.45 0.16 25)',

        // ---- Semântico: Hydration ----
        'hydrated-bg':   'oklch(0.95 0.03 225)',
        'hydrated-fg':   'oklch(0.38 0.10 225)',
        'attention-bg':  'oklch(0.95 0.05 55)',
        'attention-fg':  'oklch(0.50 0.14 55)',
        'dehydrated-bg': 'oklch(0.94 0.06 25)',
        'dehydrated-fg': 'oklch(0.45 0.18 25)',

        // ---- Semântico: Recovery (semáforo) ----
        'rec-green':  'oklch(0.62 0.16 150)',
        'rec-yellow': 'oklch(0.78 0.16 85)',
        'rec-red':    'oklch(0.58 0.20 25)',
      },

      fontFamily: {
        sans: ['IBM Plex Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },

      fontSize: {
        // [size, { lineHeight, letterSpacing }]
        eyebrow:  ['10px', { lineHeight: '1.2',  letterSpacing: '0.12em' }],
        xs:       ['12px', { lineHeight: '1.4' }],
        sm:       ['13px', { lineHeight: '1.45' }],
        body:     ['14px', { lineHeight: '1.5' }],
        h3:       ['15px', { lineHeight: '1.3',  letterSpacing: '-0.005em' }],
        h2:       ['20px', { lineHeight: '1.2',  letterSpacing: '-0.015em' }],
        h1:       ['28px', { lineHeight: '1.15', letterSpacing: '-0.02em' }],
        display:  ['42px', { lineHeight: '1.05', letterSpacing: '-0.025em' }],
        // Métricas numéricas
        'metric-md': ['20px', { lineHeight: '1' }],
        'metric-lg': ['30px', { lineHeight: '1', letterSpacing: '-0.02em' }],
        'metric-xl': ['44px', { lineHeight: '1', letterSpacing: '-0.03em' }],
      },

      letterSpacing: {
        tightish: '-0.015em',
        tighter2: '-0.025em',
      },

      borderRadius: {
        sm: '6px',
        md: '10px',
        lg: '14px',
        xl: '20px',
      },

      boxShadow: {
        card:   '0 1px 0 rgba(11,11,13,0.04), 0 1px 2px rgba(11,11,13,0.04)',
        'card-md': '0 1px 0 rgba(11,11,13,0.04), 0 6px 18px -8px rgba(11,11,13,0.10)',
        'card-lg': '0 1px 0 rgba(11,11,13,0.04), 0 24px 48px -24px rgba(11,11,13,0.20)',
        focus:  '0 0 0 3px rgba(11,11,13,0.06)',
      },

      transitionTimingFunction: {
        gss: 'cubic-bezier(0.2, 0.7, 0.2, 1)',
      },

      keyframes: {
        'fade-in-up': {
          '0%':   { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-ring': {
          '0%':   { boxShadow: '0 0 0 0 rgba(220,50,47,0.4)' },
          '100%': { boxShadow: '0 0 0 8px rgba(220,50,47,0)' },
        },
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.32s cubic-bezier(0.2,0.7,0.2,1) both',
        'pulse-ring': 'pulse-ring 1.6s infinite',
      },
    },
  },
  plugins: [
    // Recomendado para os formulários do check-in:
    // require('@tailwindcss/forms'),
  ],
};
