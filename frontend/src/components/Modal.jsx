import React from "react";
import "./Modal.css";

const Modal = ({ isOpen, onClose, title, children, footer, size = "medium" }) => {
  if (!isOpen) return null;

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const modalSizeClass = `modal-${size}`;

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className={`modal ${modalSizeClass}`} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          {title && <h2 className="modal-title">{title}</h2>}
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
};

export default Modal;
