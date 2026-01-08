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
  update: (data) => api.put('/api/settings/', data),
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
