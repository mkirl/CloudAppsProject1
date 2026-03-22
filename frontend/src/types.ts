export type Project = {
    name: string,
    description: string,
    id: string
}

export type Hardware = {
    set: string,
    capacity: number,
    available: number,
    checkedOut: number
}

export type User = {
    email: string;
};

export type AuthState = {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
};

export type LoginCredentials = {
    email: string;
    password: string;
    rememberMe?: boolean;
};

export type RegisterCredentials = {
    email: string;
    password: string;
    confirmPassword: string;
};

export type LoginResponse = {
    access_token: string;
    user: User;
};
