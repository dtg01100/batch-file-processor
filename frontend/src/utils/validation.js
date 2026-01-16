// Validation utilities
const validators = {
  required: (value) => {
    if (typeof value === "string") {
      return value.trim() ? undefined : "This field is required";
    }
    return value !== undefined && value !== null ? undefined : "This field is required";
  },

  email: (value) => {
    if (!value) return undefined;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value) ? undefined : "Please enter a valid email address";
  },

  minLength: (min) => (value) => {
    if (!value) return undefined;
    return value.length >= min ? undefined : `Must be at least ${min} characters`;
  },

  maxLength: (max) => (value) => {
    if (!value) return undefined;
    return value.length <= max ? undefined : `Must be no more than ${max} characters`;
  },

  min: (min) => (value) => {
    if (value === undefined || value === null || value === "") return undefined;
    return Number(value) >= min ? undefined : `Must be at least ${min}`;
  },

  max: (max) => (value) => {
    if (value === undefined || value === null || value === "") return undefined;
    return Number(value) <= max ? undefined : `Must be no more than ${max}`;
  },

  pattern: (regex, message) => (value) => {
    if (!value) return undefined;
    return regex.test(value) ? undefined : message || "Invalid format";
  },

  url: (value) => {
    if (!value) return undefined;
    try {
      new URL(value);
      return undefined;
    } catch {
      return "Please enter a valid URL";
    }
  },

  number: (value) => {
    if (!value) return undefined;
    return !isNaN(value) && !isNaN(parseFloat(value)) ? undefined : "Must be a number";
  },
};

// Validate a single field
const validateField = (value, validations) => {
  if (!validations || !Array.isArray(validations)) {
    return undefined;
  }

  for (const validator of validations) {
    if (typeof validator === "function") {
      const error = validator(value);
      if (error) return error;
    }
  }

  return undefined;
};

// Validate an entire form
const validateForm = (values, schema) => {
  const errors = {};

  for (const fieldName in schema) {
    const fieldValidations = schema[fieldName];
    const fieldValue = values[fieldName];
    
    const error = validateField(fieldValue, fieldValidations);
    if (error) {
      errors[fieldName] = error;
    }
  }

  return errors;
};

export { validators, validateField, validateForm };
