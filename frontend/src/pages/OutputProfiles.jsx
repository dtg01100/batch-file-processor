import React, { useState, useEffect } from "react";
import { outputProfilesApi } from "../services/api";

function OutputProfiles() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [editingProfile, setEditingProfile] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    alias: "",
    description: "",
    output_format: "csv",
    edi_tweaks: "",
    custom_settings: "",
  });

  useEffect(() => {
    loadProfiles();
  }, []);

  const loadProfiles = async () => {
    setLoading(true);
    try {
      const data = await outputProfilesApi.list();
      setProfiles(data);
      setMessage({ type: "", text: "" });
    } catch (error) {
      console.error("Failed to load profiles:", error);
      setMessage({ type: "error", text: "Failed to load profiles" });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingProfile) {
        await outputProfilesApi.update(editingProfile.id, formData);
        setMessage({ type: "success", text: "Profile updated successfully" });
      } else {
        await outputProfilesApi.create(formData);
        setMessage({ type: "success", text: "Profile created successfully" });
      }
      setShowForm(false);
      setEditingProfile(null);
      setFormData({
        name: "",
        alias: "",
        description: "",
        output_format: "csv",
        edi_tweaks: "",
        custom_settings: "",
      });
      loadProfiles();
    } catch (error) {
      console.error("Failed to save profile:", error);
      setMessage({ type: "error", text: "Failed to save profile" });
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (profile) => {
    setEditingProfile(profile);
    setFormData({
      name: profile.name,
      alias: profile.alias,
      description: profile.description,
      output_format: profile.output_format,
      edi_tweaks: profile.edi_tweaks,
      custom_settings: profile.custom_settings,
    });
    setShowForm(true);
    setMessage({ type: "", text: "" });
  };

  const handleDelete = async (profileId) => {
    if (!confirm("Are you sure you want to delete this profile?")) {
      return;
    }

    try {
      await outputProfilesApi.delete(profileId);
      setMessage({ type: "success", text: "Profile deleted successfully" });
      loadProfiles();
    } catch (error) {
      console.error("Failed to delete profile:", error);
      setMessage({ type: "error", text: "Failed to delete profile" });
    }
  };

  const handleSetDefault = async (profileId) => {
    try {
      await outputProfilesApi.setDefault(profileId);
      setMessage({ type: "success", text: "Default profile updated" });
      loadProfiles();
    } catch (error) {
      console.error("Failed to set default profile:", error);
      setMessage({ type: "error", text: "Failed to set default profile" });
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingProfile(null);
    setFormData({
      name: "",
      alias: "",
      description: "",
      output_format: "csv",
      edi_tweaks: "",
      custom_settings: "",
    });
  };

  return (
    <div className="page">
      <h1>Output Profiles</h1>

      {message.text && (
        <div className={`alert alert-${message.type}`}>{message.text}</div>
      )}

      <div className="page-actions">
        <button
          onClick={() => setShowForm(true)}
          disabled={showForm}
          className="btn btn-primary"
        >
          + New Profile
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>{editingProfile ? "Edit" : "Create"} Output Profile</h2>
              <button
                type="button"
                onClick={handleCancel}
                className="btn btn-icon"
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleSave} className="profile-form">
                <div className="form-group">
                  <label htmlFor="name">Profile Name *</label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    required
                    placeholder="e.g., Standard CSV Output"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="alias">Alias *</label>
                  <input
                    type="text"
                    id="alias"
                    name="alias"
                    value={formData.alias}
                    onChange={(e) =>
                      setFormData({ ...formData, alias: e.target.value })
                    }
                    required
                    placeholder="e.g., standard-csv"
                    pattern="[a-z0-9-]+"
                    title="Only lowercase letters, numbers, and hyphens"
                  />
                  <small>
                    Unique identifier (lowercase, numbers, hyphens only)
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="output_format">Output Format *</label>
                  <select
                    id="output_format"
                    name="output_format"
                    value={formData.output_format}
                    onChange={(e) =>
                      setFormData({ ...formData, output_format: e.target.value })
                    }
                    required
                  >
                    <option value="csv">CSV</option>
                    <option value="edi">EDI</option>
                    <option value="estore-einvoice">eStore eInvoice</option>
                    <option value="fintech">Fintech</option>
                    <option value="scannerware">Scannerware</option>
                    <option value="scansheet-type-a">Scansheet Type A</option>
                    <option value="simplified-csv">Simplified CSV</option>
                    <option value="stewart-custom">Stewart Custom</option>
                    <option value="yellowdog-csv">Yellowdog CSV</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="description">Description</label>
                  <textarea
                    id="description"
                    name="description"
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        description: e.target.value,
                      })
                    }
                    rows="3"
                    placeholder="Description of this output profile..."
                  />
                </div>

                {formData.output_format === "edi" && (
                  <div className="form-group">
                    <label htmlFor="edi_tweaks">EDI Tweaks (JSON)</label>
                    <textarea
                      id="edi_tweaks"
                      name="edi_tweaks"
                      value={formData.edi_tweaks}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          edi_tweaks: e.target.value,
                        })
                      }
                      rows="4"
                      placeholder='{"tweak1": "value1", "tweak2": "value2"}'
                    />
                    <small>
                      JSON string of EDI configuration tweaks
                    </small>
                  </div>
                )}

                {formData.output_format !== "csv" && formData.output_format !== "edi" && (
                  <div className="form-group">
                    <label htmlFor="custom_settings">
                      Custom Settings (JSON)
                    </label>
                    <textarea
                      id="custom_settings"
                      name="custom_settings"
                      value={formData.custom_settings}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          custom_settings: e.target.value,
                        })
                      }
                      rows="4"
                      placeholder='{"setting1": "value1", "setting2": "value2"}'
                    />
                    <small>
                      JSON string of custom settings for this output format
                    </small>
                  </div>
                )}

                <div className="form-actions">
                  <button type="submit" disabled={saving} className="btn btn-primary">
                    {saving ? "Saving..." : editingProfile ? "Update" : "Create"} Profile
                  </button>
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="btn btn-secondary"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {loading && <div className="loading">Loading profiles...</div>}

      {!loading && !showForm && (
        <div className="profiles-list">
          {profiles.length === 0 ? (
            <div className="no-profiles">
              <p>No output profiles found.</p>
              <p>Create a profile to get started.</p>
            </div>
          ) : (
            profiles.map((profile) => (
              <div key={profile.id} className="profile-card">
                <div className="profile-header">
                  <div className="profile-info">
                    <h3>{profile.name}</h3>
                    <span className="profile-alias">@{profile.alias}</span>
                    {profile.is_default && (
                      <span className="badge badge-default">Default</span>
                    )}
                  </div>
                  <div className="profile-actions">
                    {!profile.is_default && (
                      <button
                        type="button"
                        onClick={() => handleSetDefault(profile.id)}
                        className="btn btn-sm btn-secondary"
                        title="Set as default profile"
                      >
                        Set Default
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleEdit(profile)}
                      className="btn btn-sm btn-secondary"
                      title="Edit profile"
                    >
                      Edit
                    </button>
                    {!profile.is_default && (
                      <button
                        type="button"
                        onClick={() => handleDelete(profile.id)}
                        className="btn btn-sm btn-danger"
                        title="Delete profile"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
                <div className="profile-body">
                  <div className="profile-details">
                    <div className="detail-item">
                      <label>Format:</label>
                      <span className="detail-value">
                        {profile.output_format.toUpperCase()}
                      </span>
                    </div>
                    {profile.description && (
                      <div className="detail-item">
                        <label>Description:</label>
                        <span className="detail-value">
                          {profile.description}
                        </span>
                      </div>
                    )}
                    <div className="detail-item">
                      <label>Created:</label>
                      <span className="detail-value">
                        {new Date(profile.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="detail-item">
                      <label>Updated:</label>
                      <span className="detail-value">
                        {new Date(profile.updated_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default OutputProfiles;
