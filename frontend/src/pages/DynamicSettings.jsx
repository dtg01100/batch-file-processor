import React, { useState, useEffect } from "react";
import { settingsApi } from "../services/api";

function DynamicSettings() {
  const [uiConfig, setUiConfig] = useState(null);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [activeCategory, setActiveCategory] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState({});

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      // Load UI configuration
      const config = await settingsApi.getUiConfig();
      setUiConfig(config);
      
      // Load current settings
      const currentSettings = await settingsApi.get();
      setSettings(currentSettings);
      
      // Set initial active category
      if (config.categories && config.categories.length > 0) {
        setActiveCategory(config.categories[0].id);
      }
      
      setMessage({ type: "", text: "" });
    } catch (error) {
      console.error("Failed to load settings:", error);
      setMessage({ type: "error", text: "Failed to load settings configuration" });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (key, value) => {
    setSettings({
      ...settings,
      [key]: {
        ...settings[key],
        value: value
      }
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Collect all values
      const updateData = {};
      for (const [key, settingData] of Object.entries(settings)) {
        if (settingData.value !== undefined) {
          updateData[key] = settingData.value;
        }
      }
      
      await settingsApi.bulkUpdate(updateData);
      setMessage({ type: "success", text: "Settings saved successfully" });
      loadConfig(); // Reload to get fresh data
    } catch (error) {
      console.error("Failed to save settings:", error);
      setMessage({ type: "error", text: "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async (key) => {
    try {
      await settingsApi.reset(key);
      setMessage({ type: "success", text: `Reset ${key} to default` });
      loadConfig();
    } catch (error) {
      console.error("Failed to reset setting:", error);
      setMessage({ type: "error", text: "Failed to reset setting" });
    }
  };

  const toggleGroup = (groupName) => {
    setExpandedGroups({
      ...expandedGroups,
      [groupName]: !expandedGroups[groupName]
    });
  };

  const renderField = (field) => {
    const settingData = settings[field.key] || {};
    const value = settingData.value !== undefined ? settingData.value : field.value;
    const error = settingData.error;

    switch (field.render_as || field.type) {
      case "checkbox":
        return (
          <div className="form-group checkbox">
            <label>
              <input
                type="checkbox"
                checked={!!value}
                onChange={(e) => handleChange(field.key, e.target.checked)}
                disabled={field.read_only}
              />
              <span>{field.label}</span>
            </label>
            {field.help_text && <small>{field.help_text}</small>}
            {error && <span className="error">{error}</span>}
          </div>
        );

      case "select":
        return (
          <div className="form-group">
            <label htmlFor={field.key}>{field.label}</label>
            <select
              id={field.key}
              value={value || ""}
              onChange={(e) => handleChange(field.key, e.target.value)}
              disabled={field.read_only}
            >
              <option value="">Select...</option>
              {field.options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {field.help_text && <small>{field.help_text}</small>}
            {error && <span className="error">{error}</span>}
          </div>
        );

      case "textarea":
        return (
          <div className="form-group">
            <label htmlFor={field.key}>{field.label}</label>
            <textarea
              id={field.key}
              value={value || ""}
              onChange={(e) => handleChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              disabled={field.read_only}
              rows={4}
            />
            {field.help_text && <small>{field.help_text}</small>}
            {error && <span className="error">{error}</span>}
          </div>
        );

      case "number":
        return (
          <div className="form-group">
            <label htmlFor={field.key}>{field.label}</label>
            <input
              type="number"
              id={field.key}
              value={value !== undefined && value !== null ? value : ""}
              onChange={(e) => handleChange(field.key, parseFloat(e.target.value) || 0)}
              disabled={field.read_only}
              placeholder={field.placeholder}
            />
            {field.help_text && <small>{field.help_text}</small>}
            {error && <span className="error">{error}</span>}
          </div>
        );

      case "email":
        return (
          <div className="form-group">
            <label htmlFor={field.key}>{field.label}</label>
            <input
              type="email"
              id={field.key}
              value={value || ""}
              onChange={(e) => handleChange(field.key, e.target.value)}
              disabled={field.read_only}
              placeholder={field.placeholder}
            />
            {field.help_text && <small>{field.help_text}</small>}
            {error && <span className="error">{error}</span>}
          </div>
        );

      case "password":
        return (
          <div className="form-group">
            <label htmlFor={field.key}>{field.label}</label>
            <input
              type="password"
              id={field.key}
              value={value || ""}
              onChange={(e) => handleChange(field.key, e.target.value)}
              disabled={field.read_only}
              placeholder={field.placeholder}
              autoComplete="new-password"
            />
            {field.help_text && <small>{field.help_text}</small>}
            {error && <span className="error">{error}</span>}
          </div>
        );

      case "file":
        return (
          <div className="form-group">
            <label htmlFor={field.key}>{field.label}</label>
            <input
              type="file"
              id={field.key}
              onChange={(e) => handleChange(field.key, e.target.files[0])}
              disabled={field.read_only}
            />
            {field.help_text && <small>{field.help_text}</small>}
            {value && <small>Current file: {value.name || value}</small>}
            {error && <span className="error">{error}</span>}
          </div>
        );

      default:
        // Default to text input
        return (
          <div className="form-group">
            <label htmlFor={field.key}>{field.label}</label>
            <input
              type="text"
              id={field.key}
              value={value || ""}
              onChange={(e) => handleChange(field.key, e.target.value)}
              disabled={field.read_only}
              placeholder={field.placeholder}
              autoComplete="off"
            />
            {field.help_text && <small>{field.help_text}</small>}
            {error && <span className="error">{error}</span>}
          </div>
        );
    }
  };

  const groupFields = (fields) => {
    const groups = {};
    const ungrouped = [];
    
    for (const field of fields) {
      if (field.group && field.group.trim()) {
        if (!groups[field.group]) {
          groups[field.group] = [];
        }
        groups[field.group].push(field);
      } else {
        ungrouped.push(field);
      }
    }
    
    return { groups, ungrouped };
  };

  if (loading) {
    return (
      <div className="page">
        <h1>Settings</h1>
        <div className="loading">Loading settings configuration...</div>
      </div>
    );
  }

  if (!uiConfig || !uiConfig.categories) {
    return (
      <div className="page">
        <h1>Settings</h1>
        <div className="alert alert-error">
          Failed to load settings configuration
        </div>
        <button onClick={loadConfig} className="btn btn-primary">
          Retry
        </button>
      </div>
    );
  }

  const activeCategoryConfig = uiConfig.categories.find(c => c.id === activeCategory);
  const activeFields = activeCategoryConfig?.fields || [];
  const { groups, ungrouped } = groupFields(activeFields);

  return (
    <div className="page settings-page">
      <div className="page-header">
        <h1>Settings</h1>
        {message.text && (
          <div className={`alert alert-${message.type}`}>{message.text}</div>
        )}
      </div>

      <div className="settings-layout">
        {/* Category Navigation */}
        <aside className="settings-sidebar">
          <nav className="settings-nav">
            {uiConfig.categories.map((category) => (
              <button
                key={category.id}
                className={`nav-item ${activeCategory === category.id ? "active" : ""}`}
                onClick={() => setActiveCategory(category.id)}
              >
                <span className="nav-icon">{category.icon}</span>
                <span className="nav-label">{category.label}</span>
                <span className="nav-count">
                  {category.fields.filter(f => !f.hidden).length}
                </span>
              </button>
            ))}
          </nav>
        </aside>

        {/* Settings Form */}
        <main className="settings-main">
          {activeCategoryConfig && (
            <div className="settings-category">
              <div className="category-header">
                <h2>
                  <span className="icon">{activeCategoryConfig.icon}</span>
                  {activeCategoryConfig.label}
                </h2>
              </div>

              {/* Ungrouped Fields */}
              {ungrouped.length > 0 && !Object.keys(groups).length && (
                <div className="settings-form">
                  {ungrouped.map((field) => (
                    <div key={field.key} className="form-field">
                      {renderField(field)}
                      {!field.read_only && (
                        <button
                          type="button"
                          onClick={() => handleReset(field.key)}
                          className="btn btn-sm btn-link"
                        >
                          Reset to default
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Grouped Fields */}
              {Object.keys(groups).map((groupName) => {
                const groupFields = groups[groupName];
                const isExpanded = expandedGroups[groupName] !== false; // Default expanded

                return (
                  <div key={groupName} className="settings-group">
                    <button
                      type="button"
                      className="group-header"
                      onClick={() => toggleGroup(groupName)}
                    >
                      <span className="group-toggle">
                        {isExpanded ? "▼" : "▶"}
                      </span>
                      <span className="group-name">{groupName}</span>
                      <span className="group-count">({groupFields.length} settings)</span>
                    </button>
                    
                    {isExpanded && (
                      <div className="settings-form">
                        {groupFields.map((field) => (
                          <div key={field.key} className="form-field">
                            {renderField(field)}
                            {!field.read_only && (
                              <button
                                type="button"
                                onClick={() => handleReset(field.key)}
                                className="btn btn-sm btn-link"
                              >
                                Reset
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Ungrouped fields with groups also present */}
              {ungrouped.length > 0 && Object.keys(groups).length > 0 && (
                <div className="settings-form">
                  {ungrouped.map((field) => (
                    <div key={field.key} className="form-field">
                      {renderField(field)}
                      {!field.read_only && (
                        <button
                          type="button"
                          onClick={() => handleReset(field.key)}
                          className="btn btn-sm btn-link"
                        >
                          Reset to default
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Save Actions */}
          <div className="settings-actions">
            <button
              type="button"
              onClick={loadConfig}
              className="btn btn-secondary"
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="btn btn-primary"
              disabled={saving}
            >
              {saving ? "Saving..." : "Save Settings"}
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}

export default DynamicSettings;
