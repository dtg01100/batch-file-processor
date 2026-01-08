import React, { useState, useEffect } from "react";
import { api } from "../services/api";

function Settings() {
  const [settings, setSettings] = useState({
    connection_method: "jdbc", // Default to JDBC
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
    // ODBC settings (legacy)
    odbc_driver: "",
    as400_address: "",
    as400_username: "",
    as400_password: "",
    // JDBC settings (preferred)
    jdbc_url: "",
    jdbc_driver_class: "com.ibm.as400.access.AS400JDBCDriver",
    jdbc_jar_path: "",
    jdbc_username: "",
    jdbc_password: "",
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await api.get("/api/settings/");
      setSettings(data);
      setMessage({ type: "success", text: "Settings loaded successfully" });
    } catch (error) {
      console.error("Failed to load settings:", error);
      setMessage({ type: "error", text: "Failed to load settings" });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put("/api/settings/", settings);
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
          {/* Connection Method */}
          <section className="settings-section">
            <h2>Database Connection</h2>

            <div className="form-group">
              <label htmlFor="connection_method">Connection Method</label>
              <select
                id="connection_method"
                name="connection_method"
                value={settings.connection_method}
                onChange={handleChange}
              >
                <option value="jdbc">JDBC (Preferred)</option>
                <option value="odbc">ODBC (Legacy)</option>
              </select>
              <small>
                JDBC is recommended for better licensing flexibility and wider driver
                support.
              </small>
            </div>

            {/* JDBC Configuration */}
            {settings.connection_method === "jdbc" && (
              <div className="subsection jdbc-section">
                <h3>JDBC Configuration</h3>

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
                    Full Java class name of the JDBC driver. Common examples:
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
                    JDBC Driver JAR Path (Optional)
                  </label>
                  <input
                    type="text"
                    id="jdbc_jar_path"
                    name="jdbc_jar_path"
                    value={settings.jdbc_jar_path}
                    onChange={handleChange}
                    placeholder="/path/to/driver.jar"
                  />
                  <small>
                    Absolute path to JDBC driver JAR file. Optional if driver is in
                    JVM classpath.
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
                    required={settings.connection_method === "jdbc"}
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
                    required={settings.connection_method === "jdbc"}
                  />
                </div>
              </div>
            )}

            {/* ODBC Configuration */}
            {settings.connection_method === "odbc" && (
              <div className="subsection odbc-section">
                <h3>ODBC Configuration (Legacy)</h3>
                <small className="warning">
                  ODBC is being deprecated. Please migrate to JDBC when possible.
                </small>

                <div className="form-group">
                  <label htmlFor="odbc_driver">ODBC Driver</label>
                  <input
                    type="text"
                    id="odbc_driver"
                    name="odbc_driver"
                    value={settings.odbc_driver}
                    onChange={handleChange}
                    placeholder="Select ODBC Driver..."
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="as400_address">
                    AS400 Address
                  </label>
                  <input
                    type="text"
                    id="as400_address"
                    name="as400_address"
                    value={settings.as400_address}
                    onChange={handleChange}
                    placeholder="hostname"
                    required={settings.connection_method === "odbc"}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="as400_username">
                    AS400 Username
                  </label>
                  <input
                    type="text"
                    id="as400_username"
                    name="as400_username"
                    value={settings.as400_username}
                    onChange={handleChange}
                    required={settings.connection_method === "odbc"}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="as400_password">
                    AS400 Password
                  </label>
                  <input
                    type="password"
                    id="as400_password"
                    name="as400_password"
                    value={settings.as400_password}
                    onChange={handleChange}
                    required={settings.connection_method === "odbc"}
                  />
                </div>
              </div>
            )}
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
