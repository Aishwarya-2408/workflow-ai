import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { BrowserRouter } from "react-router-dom";
import { StagewiseToolbar } from '@stagewise/toolbar-react';

const basename = import.meta.env.BASE_URL;

const stagewiseConfig = {
  plugins: []
};

// Create the main app root
const appRoot = ReactDOM.createRoot(document.getElementById("root")!);

appRoot.render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

// Create a separate root for the Stagewise Toolbar in development
if (process.env.NODE_ENV === 'development') {
  const toolbarRootElement = document.createElement('div');
  document.body.appendChild(toolbarRootElement);
  const toolbarRoot = ReactDOM.createRoot(toolbarRootElement);
  toolbarRoot.render(
    <React.StrictMode>
      <StagewiseToolbar config={stagewiseConfig} />
    </React.StrictMode>
  );
}
