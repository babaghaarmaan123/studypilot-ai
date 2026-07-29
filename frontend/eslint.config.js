import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

/**
 * Flat config (ESLint 9). The rules that matter here are the react-hooks ones:
 * a stale closure or a missing dependency is the class of bug that shows up as
 * "the UI didn't update", which is exactly what this app has already been bitten
 * by once.
 */
export default [
  { ignores: ['dist/**', 'node_modules/**', 'public/**'] },

  js.configs.recommended,

  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.es2021 },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    settings: { react: { version: 'detect' } },
    plugins: {
      react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...react.configs.flat.recommended.rules,
      ...reactHooks.configs.recommended.rules,

      // The JSX transform makes the React import unnecessary, and prop-types
      // are not used anywhere in this codebase.
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      // Apostrophes in copy ("Time's up") are intentional.
      'react/no-unescaped-entities': 'off',

      // Advisory, not blocking. This rule (new in eslint-plugin-react-hooks 7)
      // flags the "derive state inside an effect" pattern in nine places that
      // all work correctly today — including ThemeContext, where the effect's
      // real job is syncing the DOM and localStorage. Each one wants an
      // individual redesign rather than a mechanical edit, so they are tracked
      // as warnings instead of being switched off or rushed.
      'react-hooks/set-state-in-effect': 'warn',

      // Fast-refresh ergonomics only. The context and ui/ files deliberately
      // export a hook or a variants object next to their component.
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      'no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },

  {
    // Config files run in Node, not the browser.
    files: ['*.config.js', 'vite.config.js', 'postcss.config.js', 'tailwind.config.js'],
    languageOptions: { globals: { ...globals.node } },
  },
]
