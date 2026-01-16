import { useState, useCallback } from "react";
import { validateForm } from "../utils/validation";

const useFormValidation = (initialValues, validationSchema) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  // Validate a single field
  const validateField = useCallback((fieldName, value) => {
    const fieldSchema = validationSchema[fieldName];
    if (!fieldSchema) return undefined;

    return validateForm({ [fieldName]: value }, { [fieldName]: fieldSchema })[fieldName];
  }, [validationSchema]);

  // Handle input change
  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === "checkbox" ? checked : value;

    setValues(prev => ({
      ...prev,
      [name]: newValue
    }));

    // Re-validate field if it was touched
    if (touched[name]) {
      const error = validateField(name, newValue);
      setErrors(prev => ({
        ...prev,
        [name]: error
      }));
    }
  }, [touched, validateField]);

  // Handle blur (when field loses focus)
  const handleBlur = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    const fieldValue = type === "checkbox" ? checked : value;

    setTouched(prev => ({
      ...prev,
      [name]: true
    }));

    const error = validateField(name, fieldValue);
    setErrors(prev => ({
      ...prev,
      [name]: error
    }));
  }, [validateField]);

  // Validate entire form
  const validate = useCallback(() => {
    const formErrors = validateForm(values, validationSchema);
    setErrors(formErrors);
    return Object.keys(formErrors).length === 0;
  }, [values, validationSchema]);

  // Reset form
  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  // Set field value programmatically
  const setFieldValue = useCallback((name, value) => {
    setValues(prev => ({
      ...prev,
      [name]: value
    }));

    if (touched[name]) {
      const error = validateField(name, value);
      setErrors(prev => ({
        ...prev,
        [name]: error
      }));
    }
  }, [touched, validateField]);

  // Set field error programmatically
  const setFieldError = useCallback((name, error) => {
    setErrors(prev => ({
      ...prev,
      [name]: error
    }));
  }, []);

  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validate,
    reset,
    setFieldValue,
    setFieldError,
    isValid: Object.keys(errors).length === 0
  };
};

export default useFormValidation;
