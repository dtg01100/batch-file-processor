import React, { useState } from 'react';
import { useNotification } from '../contexts/NotificationContext';
import Button from '../components/Button';
import Card from '../components/Card';
import FormField from '../components/FormField';
import { validators } from '../utils/validation';
import useFormValidation from '../hooks/useFormValidation';
import './LegacyImport.css';

const LegacyImport = () => {
  const [file, setFile] = useState(null);
  const [previewData, setPreviewData] = useState([]);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [isImportLoading, setIsImportLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const notify = useNotification();

  // Validation schema for the form
  const validationSchema = {
    file: [validators.required]
  };

  const { errors, setFieldError } = useFormValidation(
    { file: '' },
    validationSchema
  );

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.db')) {
        setFieldError('file', 'File must be a SQLite database (.db)');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setFieldError('file', '');
    }
  };

  const handlePreview = async () => {
    if (!file) {
      setFieldError('file', 'Please select a file first');
      return;
    }

    setIsPreviewLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/legacy-import/preview-db', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to preview database');
      }

      const data = await response.json();
      setPreviewData(data);
      setShowPreview(true);
      notify.showInfo(`Found ${data.length} legacy configurations to import`);
    } catch (error) {
      console.error('Preview error:', error);
      notify.showError(`Preview failed: ${error.message}`);
      setPreviewData([]);
      setShowPreview(false);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleImport = async () => {
    if (!file) {
      notify.showError('Please select a file first');
      return;
    }

    if (!window.confirm('Are you sure you want to import this legacy database? This will create new pipelines based on the legacy configurations.')) {
      return;
    }

    setIsImportLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/legacy-import/import-db', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to import database');
      }

      const result = await response.json();
      
      if (result.success) {
        notify.showSuccess(result.message);
        setFile(null);
        setPreviewData([]);
        setShowPreview(false);
      } else {
        notify.showWarning(`${result.message}. See details below.`);
        // Show errors in a modal or expandable section
        console.log('Import errors:', result.errors);
      }
    } catch (error) {
      console.error('Import error:', error);
      notify.showError(`Import failed: ${error.message}`);
    } finally {
      setIsImportLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreviewData([]);
    setShowPreview(false);
  };

  return (
    <div className="legacy-import-page">
      <Card title="Legacy Database Import" subtitle="Convert legacy folders.db configurations to new pipeline format">
        <div className="import-form">
          <FormField
            label="Legacy Database File"
            name="file"
            type="file"
            accept=".db"
            onChange={handleFileChange}
            error={errors.file}
            required
          />
          
          <div className="form-actions">
            <Button 
              variant="secondary" 
              onClick={handlePreview} 
              disabled={isPreviewLoading || isImportLoading}
              loading={isPreviewLoading}
            >
              {isPreviewLoading ? 'Analyzing...' : 'Preview Import'}
            </Button>
            
            <Button 
              variant="primary" 
              onClick={handleImport} 
              disabled={!file || isPreviewLoading || isImportLoading}
              loading={isImportLoading}
            >
              {isImportLoading ? 'Importing...' : 'Import Database'}
            </Button>
            
            <Button 
              variant="outline" 
              onClick={handleReset}
              disabled={isPreviewLoading || isImportLoading}
            >
              Reset
            </Button>
          </div>
        </div>
      </Card>

      {showPreview && previewData.length > 0 && (
        <Card title="Import Preview" subtitle={`${previewData.length} configurations will be created`}>
          <div className="preview-list">
            {previewData.map((preview, index) => (
              <div key={preview.id || index} className={`preview-item ${preview.has_errors ? 'error' : 'success'}`}>
                <div className="preview-header">
                  <h4>{preview.name}</h4>
                  <span className={`status-badge ${preview.has_errors ? 'error' : 'success'}`}>
                    {preview.has_errors ? 'Error' : `${preview.node_count} nodes`}
                  </span>
                </div>
                <p className="preview-description">{preview.description}</p>
                {preview.error_message && (
                  <div className="error-message">
                    <strong>Error:</strong> {preview.error_message}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {showPreview && previewData.length === 0 && (
        <Card title="Import Preview" subtitle="No active configurations found in the database">
          <p className="no-configs-message">
            The selected database doesn't contain any active folder configurations to import.
            Only folders with 'folder_is_active' set to True will be converted to pipelines.
          </p>
        </Card>
      )}
    </div>
  );
};

export default LegacyImport;