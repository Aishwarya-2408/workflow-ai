# GenAI Workflow Standardization

A modern web application for workflow standardization and transformation, built with React, TypeScript, and Vite.

## Features

- **File Upload**: Support for Excel (.xlsx, .xls) and CSV (.csv) files
- **Validation**: Validate and configure workflow data
- **Tree Visualization**: Visualize and modify workflow hierarchies
- **Export**: Generate and download standardized workflow files
- **Error Handling**: Comprehensive error handling throughout the application
- **Responsive Design**: Works across different screen sizes and devices

## Getting Started

### Prerequisites

- Node.js 14.x or higher
- npm 7.x or higher

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/GenAI-Workflow.git
   cd GenAI-Workflow
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:5173`

## Project Structure

- `/src`: Source code
  - `/components`: React components
  - `/hooks`: Custom React hooks
  - `/lib`: Utilities and helper functions
  - `/types`: TypeScript type definitions
  - `App.tsx`: Main application component
  - `main.tsx`: Application entry point
- `/public`: Static assets
- `/backend`: Flask backend API (see separate README in that directory)

## Error Handling

The application includes comprehensive error handling:

- **404 Page**: Custom "Not Found" page for invalid routes
- **Form Validation**: Client-side validation for all user inputs
- **API Error Handling**: Proper handling and display of backend API errors
- **Fallback UI**: Graceful degradation when components fail

## Backend API

The backend API is built with Flask. See the [backend README](./backend/README.md) for details on setting up and using the API.
