import React, { createContext, useContext, useReducer } from "react";
import Notification from "../components/Notification";

const NotificationContext = createContext();

const notificationReducer = (state, action) => {
  switch (action.type) {
    case "ADD_NOTIFICATION":
      return {
        ...state,
        notifications: [
          ...state.notifications,
          { id: Date.now(), ...action.payload }
        ]
      };
    case "REMOVE_NOTIFICATION":
      return {
        ...state,
        notifications: state.notifications.filter(
          notification => notification.id !== action.payload.id
        )
      };
    case "CLEAR_ALL_NOTIFICATIONS":
      return {
        ...state,
        notifications: []
      };
    default:
      return state;
  }
};

export const NotificationProvider = ({ children }) => {
  const [state, dispatch] = useReducer(notificationReducer, {
    notifications: []
  });

  const addNotification = (message, type = "info", duration = 5000) => {
    dispatch({
      type: "ADD_NOTIFICATION",
      payload: { message, type, duration }
    });
  };

  const removeNotification = (id) => {
    dispatch({
      type: "REMOVE_NOTIFICATION",
      payload: { id }
    });
  };

  const clearAllNotifications = () => {
    dispatch({
      type: "CLEAR_ALL_NOTIFICATIONS"
    });
  };

  const showSuccess = (message, duration) => addNotification(message, "success", duration);
  const showError = (message, duration) => addNotification(message, "error", duration);
  const showWarning = (message, duration) => addNotification(message, "warning", duration);
  const showInfo = (message, duration) => addNotification(message, "info", duration);

  return (
    <NotificationContext.Provider
      value={{
        notifications: state.notifications,
        addNotification,
        removeNotification,
        clearAllNotifications,
        showSuccess,
        showError,
        showWarning,
        showInfo
      }}
    >
      {children}
      <div className="notifications-container">
        {state.notifications.map(notification => (
          <Notification
            key={notification.id}
            message={notification.message}
            type={notification.type}
            duration={notification.duration}
            onClose={() => removeNotification(notification.id)}
          />
        ))}
      </div>
    </NotificationContext.Provider>
  );
};

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotification must be used within a NotificationProvider");
  }
  return context;
};
