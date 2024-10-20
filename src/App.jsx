import React, { useState, useEffect } from 'react';
import axios from 'axios';


// Set the base URL for the API
const API_BASE_URL = 'http://localhost:5000';

// Create an axios instance with the base URL
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});



function App() {
  const [projectName, setProjectName] = useState('');
  const [projects, setProjects] = useState([]);
  const [output, setOutput] = useState('');
  const [error, setError] = useState('');
  const [config, setConfig] = useState({});

  const startNewProject = async () => {
    try {
      setError('');
      const response = await api.post('/api/start_project', { name: projectName });
      setOutput(response.data.output || 'Project created successfully');
      setProjectName('');
      await listProjects();
    } catch (error) {
      setError(error.response?.data?.error || 'An error occurred while starting the project');
    }
  };

  const listProjects = async () => {
    try {
      setError('');
      const response = await api.get('/api/list_projects');
      setProjects(response.data.projects);
    } catch (error) {
      setError(error.response?.data?.error || 'An error occurred while listing projects');
    }
  };

  const runProject = async (projectId) => {
    try {
      setError('');
      const response = await api.post('/api/run_project', { id: projectId });
      setOutput(response.data.output || 'Project ran successfully');
    } catch (error) {
      setError(error.response?.data?.error || 'An error occurred while running the project');
    }
  };

  const deleteProject = async (projectId) => {
    try {
      setError('');
      await api.delete(`/api/delete_project/${projectId}`);
      setOutput('Project deleted successfully');
      await listProjects();
    } catch (error) {
      setError(error.response?.data?.error || 'An error occurred while deleting the project');
    }
  };

  const showConfig = async () => {
    try {
      setError('');
      const response = await api.get('/api/show_config');
      setConfig(response.data);
    } catch (error) {
      setError(error.response?.data?.error || 'An error occurred while fetching the configuration');
    }
  };

  useEffect(() => {
    listProjects();
    showConfig();
  }, []);

  // ... rest of the component remains the same


  return (
    <div className="App">
      <h1>Pythagora UI</h1>
      <div>
        <input
          type="text"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="Enter project name"
        />
        <button onClick={startNewProject}>Start New Project</button>
      </div>
      <div>
        <button onClick={listProjects}>Refresh Projects</button>
      </div>
      <div>
        {projects.map((project) => (
          <div key={project.id}>
            {project.name} - 
            <button onClick={() => runProject(project.id)}>Run</button>
            <button onClick={() => deleteProject(project.id)}>Delete</button>
          </div>
        ))}
      </div>
      {error && (
        <div style={{ color: 'red', marginTop: '10px' }}>
          Error: {error}
        </div>
      )}
      <div>
        <h3>Output:</h3>
        <textarea readOnly value={output} rows={10} cols={50} />
      </div>
      <div>
        <h3>Configuration:</h3>
        <pre>{JSON.stringify(config, null, 2)}</pre>
      </div>
    </div>
  );
}

export default App;
