const API_BASE = 'http://localhost:8000';

// Parse state input (handles arrays and strings)
function parseState(input) {
    try {
        return JSON.parse(input);
    } catch {
        return input.trim();
    }
}

// Show result with styling
function showResult(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `result ${isError ? 'error' : 'success'}`;
}

// Predict action for given state
async function predictAction() {
    const stateInput = document.getElementById('stateInput').value;
    
    if (!stateInput.trim()) {
        showResult('predictResult', 'Please enter a state', true);
        return;
    }
    
    try {
        const state = parseState(stateInput);
        const response = await fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({state})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResult('predictResult', `Predicted Action: ${result.action} for state: ${JSON.stringify(result.state)}`);
        } else {
            showResult('predictResult', result.detail, true);
        }
    } catch (error) {
        showResult('predictResult', `Error: ${error.message}`, true);
    }
}

// Update model with experience
async function updateModel() {
    const state = document.getElementById('updateState').value;
    const action = parseInt(document.getElementById('updateAction').value);
    const reward = parseFloat(document.getElementById('updateReward').value);
    const nextState = document.getElementById('updateNextState').value;
    
    if (!state || isNaN(action) || isNaN(reward) || !nextState) {
        showResult('updateResult', 'Please fill all fields', true);
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/update`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                state: parseState(state),
                action,
                reward,
                next_state: parseState(nextState)
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResult('updateResult', result.message);
            loadStatus(); // Refresh Q-table display
        } else {
            showResult('updateResult', result.detail, true);
        }
    } catch (error) {
        showResult('updateResult', `Error: ${error.message}`, true);
    }
}

// Load and display Q-table status
async function loadStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        
        if (response.ok) {
            displayStatus(data);
            displayQTable(data.q_table);
        } else {
            document.getElementById('status').innerHTML = `<span style="color: red;">Error loading status</span>`;
        }
    } catch (error) {
        document.getElementById('status').innerHTML = `<span style="color: red;">Connection error</span>`;
    }
}

// Display model status
function displayStatus(data) {
    document.getElementById('status').innerHTML = `
        <strong>Model Status:</strong> 
        States: ${data.total_states} | 
        Learning Rate: ${data.learning_rate} | 
        Discount: ${data.discount_factor} | 
        Epsilon: ${data.epsilon}
    `;
}

// Display Q-table as formatted table
function displayQTable(qtable) {
    const container = document.getElementById('qtableDisplay');
    
    if (Object.keys(qtable).length === 0) {
        container.innerHTML = '<p>No Q-table data yet. Start by making predictions or updates!</p>';
        return;
    }
    
    let html = '<table><thead><tr><th>State</th><th>Action 0</th><th>Action 1</th><th>Action 2</th><th>Action 3</th></tr></thead><tbody>';
    
    for (const [state, values] of Object.entries(qtable)) {
        html += `<tr><td>${state}</td>`;
        values.forEach(value => {
            html += `<td>${value.toFixed(3)}</td>`;
        });
        html += '</tr>';
    }
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Load status on page load
document.addEventListener('DOMContentLoaded', loadStatus);

// Auto-refresh status every 10 seconds
setInterval(loadStatus, 10000);