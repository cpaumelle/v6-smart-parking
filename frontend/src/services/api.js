/**
 * Simplified API Client
 * Replaces complex multi-file API structure with simple, clear client
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

class ApiClient {
  constructor(baseUrl = API_URL) {
    this.baseUrl = baseUrl;
  }

  getAuthToken() {
    return localStorage.getItem('auth_token');
  }

  setAuthToken(token) {
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  async request(endpoint, options = {}) {
    const token = this.getAuthToken();

    const config = {
      ...options,
      credentials: 'include',  // Include cookies for CORS
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
    };

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, config);

      // Handle non-JSON responses
      const contentType = response.headers.get('content-type');
      const isJson = contentType && contentType.includes('application/json');

      if (!response.ok) {
        const error = isJson ? await response.json() : { detail: response.statusText };
        throw new ApiError(
          error.detail || error.message || 'Request failed',
          response.status,
          error
        );
      }

      return isJson ? await response.json() : null;

    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        error.message || 'Network error',
        0,
        error
      );
    }
  }

  get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url, { method: 'GET' });
  }

  post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

// Create singleton instance
const api = new ApiClient();

// Export API client and organized endpoint methods
export { api, ApiError };

// === Authentication ===
export const authApi = {
  login: async (email, password) => {
    // Backend expects form data (OAuth2PasswordRequestForm)
    const formData = new URLSearchParams();
    formData.append('username', email);  // OAuth2 form uses 'username' field for email
    formData.append('password', password);

    const response = await fetch(`${api.baseUrl}/api/auth/login`, {
      method: 'POST',
      credentials: 'include',  // Include cookies for CORS
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
      },
      body: formData.toString(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new ApiError(error.detail || 'Login failed', response.status, error);
    }

    return response.json();
  },
  logout: () => api.post('/api/auth/logout'),
  me: () => api.get('/api/auth/me'),
  register: (data) => api.post('/api/auth/register', data),
};

// === Tenants ===
export const tenantsApi = {
  list: () => api.get('/api/tenants'),
  get: (id) => api.get(`/api/tenants/${id}`),
  create: (data) => api.post('/api/tenants', data),
  update: (id, data) => api.put(`/api/tenants/${id}`, data),
  delete: (id) => api.delete(`/api/tenants/${id}`),
};

// === Sites ===
export const sitesApi = {
  // List sites - handles both old and new signatures
  list: (tenantIdOrParams = {}, params = {}) => {
    // If first arg is object, treat as params (old API style)
    if (typeof tenantIdOrParams === 'object') {
      return api.get('/api/v6/sites', tenantIdOrParams);
    }
    // If first arg is string, treat as tenantId (new API style)
    return api.get(`/api/tenants/${tenantIdOrParams}/sites`, params);
  },

  // Get single site
  get: (id) => api.get(`/api/v6/sites/${id}`),

  // Create site for tenant
  create: (tenantId, data) => api.post(`/api/tenants/${tenantId}/sites`, data),

  // Update site
  update: (id, data) => api.put(`/api/v6/sites/${id}`, data),

  // Delete site
  delete: (id) => api.delete(`/api/v6/sites/${id}`),

  // Get occupancy for site
  getOccupancy: (id) => api.get(`/api/v6/sites/${id}/occupancy`),
};

// === Spaces ===
export const spacesApi = {
  // List spaces - handles both old and new signatures
  list: (siteIdOrParams = {}, params = {}) => {
    // If first arg is object, treat as params (old API style)
    if (typeof siteIdOrParams === 'object') {
      return api.get('/api/v6/spaces', siteIdOrParams);
    }
    // If first arg is string, treat as siteId (new API style)
    return api.get(`/api/v6/sites/${siteIdOrParams}/spaces`, params);
  },

  // Get single space
  get: (id) => api.get(`/api/v6/spaces/${id}`),

  // Create space for site
  create: (siteId, data) => api.post(`/api/v6/sites/${siteId}/spaces`, data),

  // Update space
  update: (id, data) => api.put(`/api/v6/spaces/${id}`, data),

  // Delete space
  delete: (id) => api.delete(`/api/v6/spaces/${id}`),

  // Get space history
  getHistory: (id, params = {}) => api.get(`/api/v6/spaces/${id}/history`, params),
};

// === Dashboard ===
export const dashboardApi = {
  getData: () => api.get('/api/v6/dashboard/data'),
  getStats: () => api.get('/api/v6/dashboard/stats'),
  getDashboardData: () => api.get('/api/v6/dashboard/data'),  // Alias for compatibility
};

// === Reservations ===
export const reservationsApi = {
  list: (params = {}) => api.get('/api/reservations', params),
  get: (id) => api.get(`/api/reservations/${id}`),
  create: (data) => api.post('/api/reservations', data),
  update: (id, data) => api.put(`/api/reservations/${id}`, data),
  cancel: (id) => api.delete(`/api/reservations/${id}`),
  checkAvailability: (spaceId, startTime, endTime) =>
    api.post('/api/reservations/check-availability', { spaceId, startTime, endTime }),
};

// === Devices ===
export const devicesApi = {
  list: (params = {}) => api.get('/api/devices', params),
  get: (id) => api.get(`/api/devices/${id}`),
  create: (data) => api.post('/api/devices', data),
  update: (id, data) => api.put(`/api/devices/${id}`, data),
  delete: (id) => api.delete(`/api/devices/${id}`),
};

export default api;
