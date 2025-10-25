/**
 * Type declarations for AuthContext
 */

export interface User {
  id: string;
  email: string;
  username: string;
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: string;
  is_platform_admin: boolean;
  created_at: string;
}

export interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  isPlatformAdmin: boolean;
  tenantId: string | null;
}

export function useAuth(): AuthContextType;
export function AuthProvider({ children }: { children: React.ReactNode }): JSX.Element;
