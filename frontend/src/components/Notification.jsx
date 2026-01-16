import React, { useEffect } from "react";
import "./Notification.css";

const Notification = ({ message, type = "info", duration = 5000, onClose }) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose && onClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const notificationClasses = `notification notification-\${type}`;

  return (
    <div className={notificationClasses}>
      <div className="notification-content">
        <span className="notification-message">{message}</span>
        <button className="notification-close" onClick={onClose}>
          ×
        </button>
      </div>
    </div>
  );
};

export default Notification;
