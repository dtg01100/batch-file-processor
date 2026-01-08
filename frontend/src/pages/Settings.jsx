import React, { useState, useEffect } from "react";
import { settingsApi } from "../services/api";

function Settings() {
  const [settings, setSettings] = useState({
    // Email settings
    enable_email: false,
    email_address: "",
    email_username: "",
    email_password: "",
    email_smtp_server: "smtp.gmail.com",
    smtp_port: 587,
    // Backup settings
    enable_interval_backups: true,
    backup_counter_maximum: 200,
    // JDBC settings (optional)
    jdbc_url: "",
    jdbc_driver_class: "com.ibm.as400.access.AS400JDBCDriver",
    jdbc_jar_path: "",
    jdbc_username: "",
    jdbc_password: "",
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  const [jarFiles, setJarFiles] = useState([]);
  const [uploadingJar, setUploadingJar] = useState(false);
  const [selectedJarFile, setSelectedJarFile] = useState(null);

  useEffect(() => {
    loadSettings();
    loadJarFiles();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await settingsApi.get();
      setSettings(data);
      setMessage({ type: "success", text: "Settings loaded successfully" });
    } catch (error) {
      console.error("Failed to load settings:", error);
      setMessage({ type: "error", text: "Failed to load settings" });
    } finally {
      setLoading(false);
    }
  };

  const loadJarFiles = async () => {
    try {
      const response = await settingsApi.listJars();
      setJarFiles(response.jars || []);
    } catch (error) {
      console.error("Failed to load JAR files:", error);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await settingsApi.update(settings);
      setMessage({ type: "success", text: "Settings saved successfully" });
    } catch (error) {
      console.error("Failed to save settings:", error);
      setMessage({ type: "error", text: "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings({
      ...settings,
      [name]: type === "checkbox" ? checked : value,
    });
  };

  const handleJarFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file extension
      if (!file.name.toLowerCase().endsWith(".jar")) {
        setMessage({ type: "error", text: "Only JAR files are allowed" });
        return;
      }
      setSelectedJarFile(file);
      setMessage({ type: "", text: "" });
    }
  };

  const handleJarUpload = async (e) => {
    e.preventDefault();
    if (!selectedJarFile) {
      setMessage({ type: "error", text: "Please select a JAR file to upload" });
      return;
    }

    setUploadingJar(true);
    try {
      const response = await settingsApi.uploadJar(selectedJarFile);
      setMessage({
        type: "success",
        text: `JAR file "${response.filename}" uploaded successfully`,
      });
      setSelectedJarFile(null);
      loadJarFiles(); // Refresh list
      // Reset file input
      e.target.reset();
    } catch (error) {
      console.error("Failed to upload JAR file:", error);
      setMessage({ type: "error", text: "Failed to upload JAR file" });
    } finally {
      setUploadingJar(false);
    }
  };

  const handleJarDelete = async (filename) => {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) {
      return;
    }

    try {
      await settingsApi.deleteJar(filename);
      setMessage({
        type: "success",
        text: `JAR file "${filename}" deleted successfully`,
      });
      loadJarFiles(); // Refresh list

      // If deleted file was selected, clear selection
      if (settings.jdbc_jar_path && settings.jdbc_jar_path.includes(filename)) {
        setSettings({ ...settings, jdbc_jar_path: "" });
      }
    } catch (error) {
      console.error("Failed to delete JAR file:", error);
      setMessage({ type: "error", text: "Failed to delete JAR file" });
    }
  };

  const handleJarSelect = (jarPath) => {
    setSettings({ ...settings, jdbc_jar_path: jarPath });
    setMessage({ type: "success", text: "JAR file selected" });
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  };

  return (
    <div className="page">
      <h1>Settings</h1>

      {message.text && (
        <div className={`alert alert-${message.type}`}>{message.text}</div>
      )}

      {loading ? (
        <div className="loading">Loading settings...</div>
      ) : (
        <form onSubmit={handleSave} className="settings-form">
          {/* JDBC Configuration */}
          <section className="settings-section">
            <h2>Database Connection (Optional JDBC)</h2>
            <small>
              JDBC support is optional. Configure database access only if needed.
              Install JDBC dependencies with: pip install -r requirements-optional.txt
            </small>

                {/* JAR File Upload */}
                <div className="jar-upload-section">
                  <h4>JDBC Driver JAR Files</h4>

                  {/* Upload Form */}
                  <form onSubmit={handleJarUpload} className="jar-upload-form">
                    <div className="form-group">
                      <label htmlFor="jar_file">Upload JAR File</label>
                      <input
                        type="file"
                        id="jar_file"
                        name="jar_file"
                        accept=".jar"
                        onChange={handleJarFileChange}
                        required
                      />
                      <small>
                        Select the JDBC driver JAR file for your database (e.g.,
                        jt400.jar for AS400)
                      </small>
                    </div>

                    <button
                      type="submit"
                      disabled={uploadingJar || !selectedJarFile}
                      className="btn btn-primary"
                    >
                      {uploadingJar ? "Uploading..." : "Upload JAR"}
                    </button>
                  </form>

                  {/* JAR Files List */}
                  {jarFiles.length > 0 && (
                    <div className="jar-files-list">
                      <h5>Available JAR Files:</h5>
                      <ul>
                        {jarFiles.map((jar) => (
                          <li key={jar.name}>
                            <div className="jar-file-info">
                              <span className="jar-name">{jar.name}</span>
                              <span className="jar-size">
                                ({formatFileSize(jar.size)})
                              </span>
                              <span className="jar-actions">
                                <button
                                  type="button"
                                  onClick={() => handleJarSelect(jar.path)}
                                  disabled={
                                    settings.jdbc_jar_path === jar.path
                                  }
                                  className="btn btn-sm btn-secondary"
                                >
                                  {settings.jdbc_jar_path === jar.path
                                    ? "Selected"
                                    : "Select"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleJarDelete(jar.name)}
                                  className="btn btn-sm btn-danger"
                                >
                                  Delete
                                </button>
                              </span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {jarFiles.length === 0 && (
                    <div className="no-jar-files">
                      <p>No JAR files uploaded yet.</p>
                      <p>
                        Upload a JDBC driver JAR file above to get started.
                      </p>
                    </div>
                  )}

                  {/* Selected JAR Display */}
                  {settings.jdbc_jar_path && (
                    <div className="selected-jar">
                      <strong>Selected JAR:</strong>{" "}
                      {settings.jdbc_jar_path.split("/").pop()}
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="jdbc_url">JDBC Connection URL</label>
                  <input
                    type="text"
                    id="jdbc_url"
                    name="jdbc_url"
                    value={settings.jdbc_url}
                    onChange={handleChange}
                    placeholder="jdbc:as400://hostname;database=dbname;..."
                    required
                  />
                  <small>
                    Example: jdbc:as400://myserver.example.com;database=MYDB;
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="jdbc_driver_class">
                    JDBC Driver Class
                  </label>
                  <input
                    type="text"
                    id="jdbc_driver_class"
                    name="jdbc_driver_class"
                    value={settings.jdbc_driver_class}
                    onChange={handleChange}
                    placeholder="com.ibm.as400.access.AS400JDBCDriver"
                    required
                  />
                  <small>
                    Full Java class name of JDBC driver. Common examples:
                    <br />
                    <strong>AS400/DB2:</strong> com.ibm.as400.access.AS400JDBCDriver
                    <br />
                    <strong>PostgreSQL:</strong> org.postgresql.Driver
                    <br />
                    <strong>MySQL:</strong> com.mysql.cj.jdbc.Driver
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="jdbc_jar_path">
                    JDBC Driver JAR Path
                  </label>
                  <input
                    type="text"
                    id="jdbc_jar_path"
                    name="jdbc_jar_path"
                    value={settings.jdbc_jar_path}
                    onChange={handleChange}
                    placeholder="/app/drivers/driver.jar"
                    readOnly
                  />
                  <small>
                    Path automatically set when you select a JAR file from the list
                    above.
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="jdbc_username">Database Username</label>
                  <input
                    type="text"
                    id="jdbc_username"
                    name="jdbc_username"
                    value={settings.jdbc_username}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="jdbc_password">
                    Database Password
                  </label>
                  <input
                    type="password"
                    id="jdbc_password"
                    name="jdbc_password"
                    value={settings.jdbc_password}
                    onChange={handleChange}
                  />
                </div>
              </div>
          </section>

          {/* Email Settings */}
          <section className="settings-section">
            <h2>Email Notifications</h2>

            <div className="form-group checkbox">
              <input
                type="checkbox"
                id="enable_email"
                name="enable_email"
                checked={settings.enable_email}
                onChange={handleChange}
              />
              <label htmlFor="enable_email">Enable Email Notifications</label>
            </div>

            {settings.enable_email && (
              <>
                <div className="form-group">
                  <label htmlFor="email_address">Email Address</label>
                  <input
                    type="email"
                    id="email_address"
                    name="email_address"
                    value={settings.email_address}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="email_username">
                    Email Username
                  </label>
                  <input
                    type="text"
                    id="email_username"
                    name="email_username"
                    value={settings.email_username}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="email_password">
                    Email Password
                  </label>
                  <input
                    type="password"
                    id="email_password"
                    name="email_password"
                    value={settings.email_password}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="email_smtp_server">
                    SMTP Server
                  </label>
                  <input
                    type="text"
                    id="email_smtp_server"
                    name="email_smtp_server"
                    value={settings.email_smtp_server}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="smtp_port">SMTP Port</label>
                  <input
                    type="number"
                    id="smtp_port"
                    name="smtp_port"
                    value={settings.smtp_port}
                    onChange={handleChange}
                  />
                </div>
              </>
            )}
          </section>

          {/* Backup Settings */}
          <section className="settings-section">
            <h2>Backup Settings</h2>

            <div className="form-group checkbox">
              <input
                type="checkbox"
                id="enable_interval_backups"
                name="enable_interval_backups"
                checked={settings.enable_interval_backups}
                onChange={handleChange}
              />
              <label htmlFor="enable_interval_backups">
                Enable Automatic Backups
              </label>
            </div>

            <div className="form-group">
              <label htmlFor="backup_counter_maximum">
                Maximum Backup Count
              </label>
              <input
                type="number"
                id="backup_counter_maximum"
                name="backup_counter_maximum"
                value={settings.backup_counter_maximum}
                onChange={handleChange}
                min="1"
              />
              <small>
                Maximum number of database backups to retain. Older backups will be
                deleted.
              </small>
            </div>
          </section>

          {/* Actions */}
          <div className="form-actions">
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? "Saving..." : "Save Settings"}
            </button>
            <button
              type="button"
              onClick={loadSettings}
              disabled={loading}
              className="btn btn-secondary"
            >
              {loading ? "Reloading..." : "Reload"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default Settings;
