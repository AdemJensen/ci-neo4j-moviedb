export const getApiBaseUrl = () => {
  if (typeof window === 'undefined') {
    // Server-side
    console.log('Server-side API URL:', process.env.NEXT_PUBLIC_API_URL);
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000';
  }
  // Client-side
  console.log('Client-side API URL:', process.env.NEXT_PUBLIC_API_URL);
  if (window.location.hostname === 'localhost') {
    return 'http://localhost:10000';
  }
  // Check if deployed on Render.com
  if (window.location.hostname.endsWith('.onrender.com')) {
    return 'https://ci-neo4j-moviedb-backend.onrender.com';
  }
  if (window.location.port === '3000') {
    // replace window.location.origin's port with 10000
    return `${window.location.origin.replace(/:\d+$/, ':10000')}`;
  }
  return process.env.NEXT_PUBLIC_API_URL;
};
  
export const apiService = {
  async fetchData(endpoint) {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}${endpoint}`);
    return response;
  },

  async postData(endpoint, data = {}) {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return response;
  },

  async putData(endpoint, data = {}) {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}${endpoint}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return response;
  }
};