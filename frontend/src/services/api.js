import axios from 'axios'
import { useState, useEffect } from 'react'


// API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// API client
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Folders API
export const foldersApi = {
  list: () => api.get('/api/folders/'),
  get: (id) => api.get(`/api/folders/${id}`),
  create: (data) => api.post('/api/folders/', data),
  update: (id, data) => api.put(`/api/folders/${id}`, data),
  delete: (id) => api.delete(`/api/folders/${id}`),
}

// Settings API
export const settingsApi = {
  get: () => api.get('/api/settings/'),
  getSchema: () => api.get('/api/settings/schema'),
  getUiConfig: () => api.get('/api/settings/ui-config'),
  getCategories: () => api.get('/api/settings/categories'),
  getRegistry: () => api.get('/api/settings/registry'),
  update: (data) => api.put('/api/settings/', data),
  bulkUpdate: (settings) => api.post('/api/settings/bulk-update', { settings }),
  reset: (key) => api.post(`/api/settings/${key}/reset`),
  validate: (key, value) => api.get(`/api/settings/${key}/validate?value=${encodeURIComponent(value)}`),
  uploadJar: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/settings/upload-jar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  listJars: () => api.get('/api/settings/jars'),
  deleteJar: (filename) => api.delete(`/api/settings/jars/${filename}`),
}

// Output Profiles API
export const outputProfilesApi = {
  list: () => api.get('/api/output-profiles/'),
  get: (id) => api.get(`/api/output-profiles/${id}`),
  create: (data) => api.post('/api/output-profiles/', data),
  update: (id, data) => api.put(`/api/output-profiles/${id}`, data),
  delete: (id) => api.delete(`/api/output-profiles/${id}`),
  setDefault: (id) => api.post(`/api/output-profiles/${id}/set-default`),
  getDefault: () => api.get('/api/output-profiles/default'),
  getFormats: () => api.get('/api/output-profiles/formats'),
}

// Jobs API
export const jobsApi = {
  list: () => api.get('/api/jobs/'),
  get: (id) => api.get(`/api/jobs/${id}`),
  create: (data) => api.post('/api/jobs/', data),
  update: (id, data) => api.put(`/api/jobs/${id}`, data),
  delete: (id) => api.delete(`/api/jobs/${id}`),
  run: (id) => api.post(`/api/jobs/${id}/run`),
  toggle: (id) => api.post(`/api/jobs/${id}/toggle`),
}

// Output Profiles API
export const outputProfilesApi = {
  list: () => api.get('/api/output-profiles/'),
  get: (id) => api.get(`/api/output-profiles/${id}`),
  create: (data) => api.post('/api/output-profiles/', data),
  update: (id, data) => api.put(`/api/output-profiles/${id}`, data),
  delete: (id) => api.delete(`/api/output-profiles/${id}`),
  setDefault: (id) => api.post(`/api/output-profiles/${id}/set-default`),
  getDefault: () => api.get('/api/output-profiles/default'),
  getFormats: () => api.get('/api/output-profiles/formats'),
}

// Runs API
export const runsApi = {
  list: (params) => api.get('/api/runs/', { params }),
  get: (id) => api.get(`/api/runs/${id}`),
  getLogs: (id) => api.get(`/api/runs/${id}/logs`),
}

// Test connection API
export const testConnectionApi = {
  test: (data) => api.post('/api/test-connection', data),
}

// Import database API
export const importApi = {
  importDatabase: (source_db_path, target_db_path) => api.post('/api/import', {
    source_db_path,
    target_db_path,
  }),
}
