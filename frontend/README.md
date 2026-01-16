# Frontend Documentation

This document describes the frontend architecture and components of the Batch File Processor application.

## Architecture Overview

The frontend is built with React and follows a component-based architecture with the following key areas:

- **Components**: Reusable UI elements
- **Pages**: Route-level components
- **Services**: API communication layer
- **Utils**: Utility functions
- **Hooks**: Custom React hooks
- **Styles**: Global styles and design system

## Component Library

### Core Components

#### Button
A versatile button component with multiple variants and sizes.

**Props:**
- `variant`: "primary", "secondary", "success", "danger", "warning", "outline"
- `size`: "small", "medium", "large"
- `disabled`: boolean
- `loading`: boolean
- `icon`: React node
- `onClick`: function

#### Card
A container component for grouping related content.

**Props:**
- `title`: string
- `subtitle`: string
- `actions`: React node
- `className`: string

#### Modal
A dialog component for displaying content in a popup overlay.

**Props:**
- `isOpen`: boolean
- `onClose`: function
- `title`: string
- `size`: "small", "medium", "large"
- `footer`: React node

#### FormField
An input wrapper with built-in validation and error display.

**Props:**
- `label`: string
- `name`: string
- `type`: "text", "select", "textarea", etc.
- `value`: string
- `onChange`: function
- `error`: string
- `required`: boolean
- `placeholder`: string

### Utility Components

#### LoadingSpinner
Shows a loading indicator with optional message.

**Props:**
- `size`: "small", "medium", "large"
- `message`: string

#### Notification
Displays user feedback messages.

**Props:**
- `message`: string
- `type`: "info", "success", "warning", "error"
- `duration`: number
- `onClose`: function

## Hooks

### useFormValidation
Manages form state and validation.

**Usage:**
\`\`\`javascript
const { values, errors, handleChange, handleBlur, validate } = useFormValidation(
  initialValues,
  validationSchema
);
\`\`\`

## Validation Utilities

The validation system provides common validation functions:

- `validators.required`: Checks if a field has a value
- `validators.email`: Validates email format
- `validators.minLength(min)`: Checks minimum length
- `validators.maxLength(max)`: Checks maximum length
- `validators.min(min)`: Checks minimum numeric value
- `validators.max(max)`: Checks maximum numeric value
- `validators.pattern(regex, message)`: Checks against a regex pattern
- `validators.url`: Validates URL format
- `validators.number`: Validates numeric format

## Design System

The application uses a consistent design system defined in \`design-system.css\` with:

- CSS variables for colors, spacing, typography, etc.
- Utility classes for common styling patterns
- Responsive design patterns

## API Service Layer

The \`services/api.js\` file contains modules for interacting with different backend endpoints:

- \`foldersApi\`: Folder management
- \`jobsApi\`: Job scheduling and execution
- \`settingsApi\`: Application settings
- \`outputProfilesApi\`: Output profile management
- \`runsApi\`: Job run history
- \`testConnectionApi\`: Connection testing

## Error Handling

The application implements error boundaries at the route level to prevent crashes and provides user-friendly error messages.

## State Management

- Local component state using React hooks
- Global notification state using context
- Form state using custom hooks

## Best Practices

- All asynchronous operations include proper error handling
- Loading states are displayed during API calls
- User feedback is provided through notifications
- Forms have validation and clear error messaging
- Components are reusable and follow consistent patterns
- Accessibility is considered in component design
