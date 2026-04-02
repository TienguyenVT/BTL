import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);

  useEffect(() => {
    const backendUserId = localStorage.getItem('backendUserId');
    const backendUserName = localStorage.getItem('backendUserName');

    if (backendUserId) {
      setUser({ id: backendUserId, name: backendUserName });
      setIsAuthenticated(true);
    } else {
      setIsAuthenticated(false);
    }
    setIsLoadingAuth(false);
  }, []);

  const logout = () => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('backendUserId');
    localStorage.removeItem('backendUserName');
  };

  const login = (userId, userName) => {
    setUser({ id: userId, name: userName });
    setIsAuthenticated(true);
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      isLoadingAuth,
      logout,
      login,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
