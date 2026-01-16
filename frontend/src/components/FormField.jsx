import React from "react";
import "./FormField.css";

const FormField = ({
  label,
  name,
  type = "text",
  value,
  onChange,
  error,
  required = false,
  placeholder = "",
  options = [],
  ...props
}) => {
  const hasError = Boolean(error);

  return (
    <div className={`form-field ${hasError ? "form-field-error" : ""}`}>
      <label htmlFor={name} className="form-label">
        {label} {required && <span className="required">*</span>}
      </label>
      
      {type === "select" ? (
        <select
          id={name}
          name={name}
          value={value}
          onChange={onChange}
          className={`form-input form-select ${hasError ? "input-error" : ""}`}
          {...props}
        >
          <option value="">Select an option</option>
          {options.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : type === "textarea" ? (
        <textarea
          id={name}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={`form-input form-textarea ${hasError ? "input-error" : ""}`}
          {...props}
        />
      ) : (
        <input
          id={name}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={`form-input ${hasError ? "input-error" : ""}`}
          {...props}
        />
      )}
      
      {hasError && <div className="error-message">{error}</div>}
    </div>
  );
};

export default FormField;
