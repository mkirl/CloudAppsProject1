import axios from "axios"
import type { Hardware, Project } from "./types"
import { authService } from "./services/authService"

// Create axios instance with interceptors
const apiClient = axios.create();

// Request interceptor - add auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = authService.getAccessToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor - handle 401 by redirecting to login
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            authService.clearTokens();
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export { apiClient };

export const getUserProjects = async (): Promise<Project[]> => {
    const response = await apiClient.get('/api/projects');
    return response.data;
}

export const createProject = async (project: Project): Promise<Project> => {
    const response = await apiClient.post('/api/projects', project);
    return response.data;
}

export const joinProject = async (projectId: string): Promise<Project> => {
    const response = await apiClient.post('/api/projects/join', { projectId });
    return response.data;
}

export const getHardwareResources = async (): Promise<Hardware[]> => {
    const response = await apiClient.get('/api/hardware');
    return response.data;
}

export const getProjectHardwareResources = async (projectId: string): Promise<Hardware[]> => {
    const response = await apiClient.get(`/api/hardware/project/${projectId}`);
    return response.data;
}

export const requestHardware = async (projectId: string, requests: { set: string, quantity: number }[]): Promise<void> => {
    await apiClient.post('/api/hardware/request', { projectId, requests });
}

export const returnHardware = async (projectId: string, returns: { set: string, quantity: number }[]): Promise<void> => {
    await apiClient.post('/api/hardware/return', { projectId, returns });
}
