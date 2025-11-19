# 🎨 ZeCo Frontend

The frontend for the ZeCo Restaurant Management System, built with **React 18** and **Vite**. This application is designed to be fast, responsive, and highly customizable through a unique automated theming engine.

## 🧠 Project Concept & Architecture

The frontend is built as a **Single Page Application (SPA)** using React. It interacts with the backend via a RESTful API.

### Key Architectural Decisions:
1.  **Automated Theming:** Instead of hardcoding colors, we use a `theme.json` file. A build script (`generate-theme.js`) reads this configuration and generates standard CSS variables. This allows the entire look of the app to be changed without touching a single line of React code.
2.  **Component-Based Design:** The UI is broken down into small, reusable components (e.g., `MenuCard`, `NavBar`) to ensure maintainability.
3.  **Context API for State:** We use React Context for global state management:
    *   `AuthContext`: Manages user login state and tokens.
    *   `CartContext`: Manages the shopping cart across pages.
4.  **Role-Based Routing:** Certain routes (like `/admin`) are protected and only accessible to users with specific roles.

## � Detailed Folder Structure

Here is a breakdown of the project structure and what each part does:

```
frontend/
├── 📂 public/                  # Static assets served directly (e.g., index.html)
│
├── 📂 scripts/                 # Build and utility scripts
│   └── generate-theme.js       # 🎨 The core engine that converts theme.json -> CSS variables
│
├── 📂 src/                     # Main source code
│   ├── 📂 assets/              # Static images and icons (logos, favicons)
│   │
│   ├── 📂 components/          # Reusable UI building blocks
│   │   ├── NavBar.jsx          # Responsive navigation bar with user & cart info
│   │   ├── MenuCard.jsx        # Displays individual menu items with "Add to Cart"
│   │   └── ...
│   │
│   ├── 📂 context/             # Global State Management
│   │   ├── AuthContext.jsx     # Handles Login, Logout, and Token storage
│   │   └── CartContext.jsx     # Handles adding/removing items from the cart
│   │
│   ├── 📂 css/                 # Styling
│   │   ├── theme.css           # 🤖 AUTO-GENERATED file containing all CSS variables
│   │   ├── index.css           # Global resets and base styles
│   │   └── [Component].css     # Component-specific styles
│   │
│   ├── 📂 pages/               # Full page views
│   │   ├── Home.jsx            # Landing page
│   │   ├── Menu.jsx            # Menu grid display
│   │   ├── Login.jsx           # User authentication page
│   │   ├── Admin.jsx           # Dashboard for restaurant management
│   │   └── Checkout.jsx        # Order summary and submission
│   │
│   ├── 📂 routes/              # Navigation Logic
│   │   └── AppRoutes.jsx       # Defines URL paths and protects private routes
│   │
│   ├── App.jsx                 # Main layout wrapper
│   └── main.jsx                # Application entry point (mounts React to DOM)
│
├── theme.json                  # 🖌️ The "Brain" of the design. Edit this to change the look!
├── Dockerfile                  # Docker configuration for containerization
└── vite.config.js              # Vite build configuration
```

## �️ The Automated Theming System

The most unique feature of this frontend is the automated theming.

1.  **Configuration:** You define your brand in `theme.json` (colors, fonts, spacing).
2.  **Generation:** When the container starts (or when you run `npm run generate-theme`), the script parses this JSON.
3.  **Output:** It creates `src/css/theme.css` with CSS variables like:
    ```css
    :root {
      --color-primary: #00ACC1;
      --color-bg-default: #F0F9FF;
      /* ...and dozens more */
    }
    ```
4.  **Usage:** React components just use `var(--color-primary)`, so they automatically adapt to whatever you defined.

## 🛠️ Development Commands

```bash
# Install dependencies
npm install

# 🎨 Generate the theme (Run this after editing theme.json)
npm run generate-theme

# 🚀 Start the development server
npm run dev
```

