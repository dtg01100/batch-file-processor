import React from "react";
import "./LoadingSpinner.css";

const LoadingSpinner = ({ size = "medium", message = "Loading..." }) => {
  const sizeClasses = {
    small: "spinner-small",
    medium: "spinner-medium",
    large: "spinner-large"
  };

  return (
    <div className="loading-spinner-container">
      <div className={`loading-spinner \${sizeClasses[size]}`}>
        <div className="spinner"></div>
        {message && <p className="loading-message">{message}</p>}
      </div>
    </div>
  );
};

export default LoadingSpinner;
