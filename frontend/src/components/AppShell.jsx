import { useState } from 'react';
import BackendAuth from './BackendAuth';
import Layout from './Layout';

export default function AppShell() {
  const [backendUserId, setBackendUserId] = useState(
    () => localStorage.getItem('backendUserId') || null
  );

  const handleConnected = (id, name) => {
    setBackendUserId(id);
  };

  if (!backendUserId) {
    return <BackendAuth onConnected={handleConnected} />;
  }

  return <Layout />;
}