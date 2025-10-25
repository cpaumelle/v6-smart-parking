/**
 * Type declarations for simplified API client
 */

export class ApiError extends Error {
  status: number;
  details: any;
}

export class ApiClient {
  baseUrl: string;
  getAuthToken(): string | null;
  setAuthToken(token: string | null): void;
  request(endpoint: string, options?: any): Promise<any>;
  get(endpoint: string, params?: any): Promise<any>;
  post(endpoint: string, data: any): Promise<any>;
  put(endpoint: string, data: any): Promise<any>;
  delete(endpoint: string): Promise<any>;
}

export const api: ApiClient;

export const authApi: {
  login(email: string, password: string): Promise<any>;
  logout(): Promise<void>;
  me(): Promise<any>;
  register(data: any): Promise<any>;
};

export const tenantsApi: {
  list(): Promise<any[]>;
  get(id: string): Promise<any>;
  create(data: any): Promise<any>;
  update(id: string, data: any): Promise<any>;
  delete(id: string): Promise<void>;
};

export const sitesApi: {
  list(tenantId: string, params?: any): Promise<any[]>;
  get(id: string): Promise<any>;
  create(tenantId: string, data: any): Promise<any>;
  update(id: string, data: any): Promise<any>;
  delete(id: string): Promise<void>;
  getOccupancy(id: string): Promise<any>;
};

export const spacesApi: {
  list(siteId: string, params?: any): Promise<any[]>;
  get(id: string): Promise<any>;
  create(siteId: string, data: any): Promise<any>;
  update(id: string, data: any): Promise<any>;
  delete(id: string): Promise<void>;
  getHistory(id: string, params?: any): Promise<any[]>;
};

export const dashboardApi: {
  getData(): Promise<any>;
  getStats(): Promise<any>;
};

export const reservationsApi: {
  list(params?: any): Promise<any[]>;
  get(id: string): Promise<any>;
  create(data: any): Promise<any>;
  update(id: string, data: any): Promise<any>;
  cancel(id: string): Promise<void>;
  checkAvailability(spaceId: string, startTime: string, endTime: string): Promise<any>;
};

export default api;
