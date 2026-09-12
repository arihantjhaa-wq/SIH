# Frontend Project

This project uses shadcn/ui components with Tailwind CSS and TypeScript.

## Setup Instructions

### 1. Install Dependencies

```bash
# Navigate to the frontend directory
# Then run:
npm install
"
"  "motion": "^11.0.0",
  "framer-motion": "^11.0.0",
  "lucide-react": "^0.263.1"
""

### 2. Project Structure

The project follows shadcn/ui conventions:

```
src/
├── components/
│   └── ui/              # UI component directory
│       ├── dancing-letters.jsx  # Animated letters component
│       └── sign-in-card-2.jsx    # Login card component
├── lib/                  # Utility functions
│   └── utils.js
├── context/             # React contexts
├── hooks/              # Custom hooks
├── pages/              # Page components
└── components/         # Regular components
```

### 3. Component Paths

The `components/ui` directory is the standard location for UI components in shadcn/ui projects:

- **Default path**: `/src/components/ui/`
- **Why this folder matters**: This is the conventional location for reusable UI components, making them easily discoverable and importable across the application.

### 4. Tailwind CSS Setup

Tailwind CSS is already configured:
- Configured via `@tailwindcss/vite` in `vite.config.js`
- Base styles in `src/index.css`
- Custom components with `className` utilities

### 5. TypeScript Support

The project uses TypeScript. All components include type definitions:

```tsx
interface DancingLettersProps {
  text?: string;
  className?: string;
  letterClassName?: string;
  autoPlay?: boolean;
  autoPlayInterval?: number;
}
```

### 6. Available Components

#### DancingLetters
A component that creates animated, physics-based letter effects with hover interactions. It's perfect for headers, logos, or any text that needs to be engaging.

**Usage**: 
```tsx
import DancingLetters from "@/components/ui/dancing-letters";

<DancingLetters text="ANIMATE" />
```

#### SignInCard2
A modern, glassmorphic login card with 3D hover effects, animated light beams, and a beautiful gradient background. Supports email/password login and Google authentication.

**Usage**:
```tsx
import { Component } from "@/components/ui/sign-in-card-2";

<Component />
```

### 7. Development

```bash
npm run dev    # Start development server
npm run build  # Build for production
npm run preview # Preview production build
```

### 8. Integration Notes

The components are ready to be used in your application. They include:
- responsive design
- hover and interaction states
- smooth animations
- accessibility features
- proper TypeScript typing

Simply import them where needed and start building!