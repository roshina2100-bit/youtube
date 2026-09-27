# Cinematic Multi-Language Video Studio - Frontend

Angular 18+ frontend for the Cinematic Multi-Language Video Studio.

## Prerequisites

- Node.js 20+ (LTS)
- npm 10+
- Angular CLI 18+

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
# Start development server
npm start

# Run tests
npm test

# Run tests in CI mode
npm run test:ci

# Lint code
npm run lint

# Build for production
npm run build:prod
```

## Project Structure

```
src/
├── app/
│   ├── core/                 # Core services, interceptors, guards
│   │   ├── interceptors/     # HTTP interceptors
│   │   └── services/         # Core services (Auth, Notification, API)
│   ├── features/             # Feature modules
│   │   ├── dashboard/        # Dashboard component
│   │   ├── models/           # Models management
│   │   ├── projects/         # Project management
│   │   │   ├── project-create/
│   │   │   └── project-detail/
│   │   └── settings/         # Settings
│   ├── layout/               # Layout components
│   ├── shared/               # Shared components, models, pipes
│   │   └── models/           # TypeScript interfaces
│   ├── app.component.ts      # Root component
│   ├── app.routes.ts         # Routing configuration
│   └── main.ts               # Application bootstrap
├── assets/                   # Static assets
├── environments/             # Environment configurations
├── styles.scss               # Global styles
├── index.html                # Main HTML file
└── main.ts                   # Entry point
```

## Key Features

- **Project Management**: Create, edit, delete, and manage cinematic video projects
- **Model Management**: Configure and test AI models (local and external)
- **Settings**: Comprehensive application configuration
- **Dashboard**: Overview of projects and recent activity
- **Responsive Design**: Works on desktop and tablet

## Technology Stack

- Angular 18+
- Angular Material 18+
- RxJS 7+
- TypeScript 5.4+
- SCSS for styling

## Environment Configuration

- `src/environments/environment.ts` - Development
- `src/environments/environment.prod.ts` - Production

## API Integration

The frontend communicates with the FastAPI backend via REST API. Configure the API URL in the environment files.

## Testing

```bash
# Unit tests
npm test

# E2E tests (requires running backend)
npm run e2e
```

## Building

```bash
# Development build
npm run build

# Production build
npm run build:prod
```

Output will be in `dist/cinematic-video-studio/`.

## Code Style

- Prettier for formatting
- TSLint for linting
- Angular style guide compliance

## Contributing

1. Follow Angular style guide
- Use standalone components
- Use signals for state management
- Write tests for new features
- Follow conventional commits