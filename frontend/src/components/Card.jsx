import React from "react";
import "./Card.css";

const Card = ({ children, title, subtitle, actions, className = "", ...props }) => {
  const cardClasses = ["card", className].filter(Boolean).join(" ");

  return (
    <div className={cardClasses} {...props}>
      {(title || subtitle || actions) && (
        <div className="card-header">
          <div className="card-title-section">
            {title && <h3 className="card-title">{title}</h3>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
    </div>
  );
};

export default Card;
