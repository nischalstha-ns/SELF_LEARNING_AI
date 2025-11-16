const API_BASE = 'http://localhost:8000';
let authToken = localStorage.getItem('authToken');
let currentUser = null;
let selectedModelId = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        showDashboard();
        loadDashboard();
    } else {
        showAuth();
    }
});

// Auth functions
function showLogin() {
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('registerForm').classList.add('hidden');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab')[0].classList.add('active');
}

function showRegister() {
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.remove('hidden');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab')[1].classList.add('active');
}

async function register() {
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    
    try {
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Registration successful! Please login.', false);
            showLogin();
        } else {
            showMessage(result.detail, true);
        }
    } catch (error) {
        showMessage('Registration failed: ' + error.message, true);
    }
}

async function login() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            authToken = result.access_token;
            localStorage.setItem('authToken', authToken);
            showDashboard();
            loadDashboard();
        } else {
            showMessage(result.detail, true);
        }
    } catch (error) {
        showMessage('Login failed: ' + error.message, true);
    }
}

function logout() {
    authToken = null;
    localStorage.removeItem('authToken');
    showAuth();
}

function showAuth() {
    document.getElementById('authSection').classList.remove('hidden');
    document.getElementById('dashboardSection').classList.add('hidden');
}

function showDashboard() {
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('dashboardSection').classList.remove('hidden');
}

function showMessage(message, isError) {
    const messageEl = document.getElementById('authMessage');
    messageEl.textContent = message;
    messageEl.className = `message ${isError ? 'error' : 'success'}`;
}

// Dashboard functions
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/dashboard`, {
            headers: {'Authorization': `Bearer ${authToken}`}
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentUser = data.user;
            updateDashboardUI(data);
            loadModels();
        } else {
            logout();
        }
    } catch (error) {
        console.error('Dashboard load failed:', error);
    }
}

function updateDashboardUI(data) {
    document.getElementById('userInfo').textContent = data.user.email;
    document.getElementById('apiUsage').textContent = `${data.user.api_calls_used} / ${data.user.api_calls_limit}`;
    document.getElementById('subscription').textContent = data.user.subscription_tier;
    document.getElementById('modelCount').textContent = data.models.length;
    
    // Update model select
    const select = document.getElementById('modelSelect');
    select.innerHTML = '<option value="">Select Model</option>';
    data.models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = `${model.name} (${model.total_states} states)`;
        select.appendChild(option);
    });
}

async function loadModels() {
    try {
        const response = await fetch(`${API_BASE}/models`, {
            headers: {'Authorization': `Bearer ${authToken}`}
        });
        
        const models = await response.json();
        
        const container = document.getElementById('modelsList');
        container.innerHTML = '';
        
        models.forEach(model => {
            const div = document.createElement('div');
            div.className = 'model-item';
            div.innerHTML = `
                <div>
                    <strong>${model.name}</strong><br>
                    <small>States: ${model.total_states} | Created: ${new Date(model.created_at).toLocaleDateString()}</small>
                </div>
                <button onclick="selectModel(${model.id})">Select</button>
            `;
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Failed to load models:', error);
    }
}

function selectModel(modelId) {
    selectedModelId = modelId;
    document.getElementById('modelSelect').value = modelId;
    showResult('Model selected successfully', 'predictResult', false);
}

// Model management
function showCreateModel() {
    document.getElementById('createModelSection').classList.remove('hidden');
}

function hideCreateModel() {
    document.getElementById('createModelSection').classList.add('hidden');
}

async function createModel() {
    const name = document.getElementById('modelName').value;
    const learning_rate = parseFloat(document.getElementById('learningRate').value);
    const discount_factor = parseFloat(document.getElementById('discountFactor').value);
    const epsilon = parseFloat(document.getElementById('epsilon').value);
    
    try {
        const response = await fetch(`${API_BASE}/models`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({name, learning_rate, discount_factor, epsilon})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            hideCreateModel();
            loadDashboard();
            showResult('Model created successfully', 'predictResult', false);
        } else {
            showResult(result.detail, 'predictResult', true);
        }
    } catch (error) {
        showResult('Failed to create model: ' + error.message, 'predictResult', true);
    }
}

// AI functions
function parseState(input) {
    try {
        return JSON.parse(input);
    } catch {
        return input.trim();
    }
}

function showResult(message, elementId, isError) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `result ${isError ? 'error' : 'success'}`;
}

async function predictAction() {
    const modelId = parseInt(document.getElementById('modelSelect').value);
    const stateInput = document.getElementById('stateInput').value;
    
    if (!modelId || !stateInput.trim()) {
        showResult('Please select a model and enter a state', 'predictResult', true);
        return;
    }
    
    try {
        const state = parseState(stateInput);
        const response = await fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({state, model_id: modelId})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResult(`Predicted Action: ${result.action} for state: ${JSON.stringify(result.state)}`, 'predictResult', false);
            loadDashboard(); // Refresh API usage
        } else {
            showResult(result.detail, 'predictResult', true);
        }
    } catch (error) {
        showResult('Prediction failed: ' + error.message, 'predictResult', true);
    }
}

async function updateModel() {
    const modelId = parseInt(document.getElementById('modelSelect').value);
    const state = document.getElementById('updateState').value;
    const action = parseInt(document.getElementById('updateAction').value);
    const reward = parseFloat(document.getElementById('updateReward').value);
    const nextState = document.getElementById('updateNextState').value;
    
    if (!modelId || !state || isNaN(action) || isNaN(reward) || !nextState) {
        showResult('Please fill all fields and select a model', 'updateResult', true);
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                state: parseState(state),
                action,
                reward,
                next_state: parseState(nextState),
                model_id: modelId
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResult(result.message, 'updateResult', false);
            loadDashboard(); // Refresh stats
            loadModelStatus(); // Refresh Q-table
        } else {
            showResult(result.detail, 'updateResult', true);
        }
    } catch (error) {
        showResult('Update failed: ' + error.message, 'updateResult', true);
    }
}

async function loadModelStatus() {
    const modelId = parseInt(document.getElementById('modelSelect').value);
    
    if (!modelId) {
        document.getElementById('qtableDisplay').innerHTML = '<p>Please select a model first</p>';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/status/${modelId}`, {
            headers: {'Authorization': `Bearer ${authToken}`}
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayQTable(data);
        } else {
            document.getElementById('qtableDisplay').innerHTML = '<p>Failed to load model status</p>';
        }
    } catch (error) {
        document.getElementById('qtableDisplay').innerHTML = '<p>Connection error</p>';
    }
}

function displayQTable(data) {
    const container = document.getElementById('qtableDisplay');
    
    if (Object.keys(data.q_table).length === 0) {
        container.innerHTML = '<p>No Q-table data yet. Start by making predictions or updates!</p>';
        return;
    }
    
    let html = `
        <div style="margin-bottom: 15px;">
            <strong>Model:</strong> ${data.model_name} | 
            <strong>States:</strong> ${data.total_states} | 
            <strong>Last Updated:</strong> ${new Date(data.last_updated).toLocaleString()}
        </div>
        <table>
            <thead>
                <tr><th>State</th><th>Action 0</th><th>Action 1</th><th>Action 2</th><th>Action 3</th></tr>
            </thead>
            <tbody>
    `;
    
    for (const [state, values] of Object.entries(data.q_table)) {
        html += `<tr><td>${state}</td>`;
        values.forEach(value => {
            html += `<td>${value.toFixed(3)}</td>`;
        });
        html += '</tr>';
    }
    
    html += '</tbody></table>';
    container.innerHTML = html;
}