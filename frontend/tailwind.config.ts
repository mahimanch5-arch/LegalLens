import type { Config } from 'tailwindcss';
import typography from '@tailwindcss/typography';

const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: token('bg'),
        surface: token('surface'),
        sidebar: token('sidebar'),
        border: token('border'),
        hover: token('hover'),
        bubble: token('bubble'),
        ink: token('text'),
        muted: token('text-muted'),
        subtle: token('text-subtle'),
        primary: { DEFAULT: token('primary'), hover: token('primary-hover'), soft: token('primary-soft') },
        accent: { DEFAULT: token('accent'), soft: token('accent-soft') },
        highlight: token('highlight'),
        success: { DEFAULT: token('success'), soft: token('success-soft') },
        warning: { DEFAULT: token('warning'), soft: token('warning-soft') },
        danger: { DEFAULT: token('danger'), soft: token('danger-soft') },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: { lg: '10px', xl: '12px', '2xl': '16px' },
      boxShadow: {
        soft: '0 1px 2px rgb(28 27 25 / 0.04), 0 2px 8px rgb(28 27 25 / 0.05)',
        pop: '0 4px 12px rgb(28 27 25 / 0.08), 0 12px 32px rgb(28 27 25 / 0.10)',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'slide-in-right': { from: { transform: 'translateX(16px)', opacity: '0' }, to: { transform: 'none', opacity: '1' } },
        'slide-in-left': { from: { transform: 'translateX(-16px)', opacity: '0' }, to: { transform: 'none', opacity: '1' } },
        'pop-in': { from: { transform: 'scale(0.97)', opacity: '0' }, to: { transform: 'none', opacity: '1' } },
        blink: { '0%,100%': { opacity: '1' }, '50%': { opacity: '0' } },
        shimmer: { from: { backgroundPosition: '200% 0' }, to: { backgroundPosition: '-200% 0' } },
      },
      animation: {
        'fade-in': 'fade-in 150ms ease-out',
        'slide-in-right': 'slide-in-right 200ms ease-out',
        'slide-in-left': 'slide-in-left 200ms ease-out',
        'pop-in': 'pop-in 150ms ease-out',
        blink: 'blink 1s step-end infinite',
        shimmer: 'shimmer 1.6s linear infinite',
      },
    },
  },
  plugins: [typography],
} satisfies Config;
