const API_BASE = 'http://localhost:8000/api';

async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/files/upload`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        alert(`File uploaded: ${result.filename}`);
    } catch (error) {
        alert('Upload failed: ' + error.message);
    }
}

async function makePrediction() {
    const dataInput = document.getElementById('dataInput');
    const resultDiv = document.getElementById('result');
    
    try {
        const data = JSON.parse(dataInput.value);
        const response = await fetch(`${API_BASE}/ai/predict`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({data, model_type: 'default'})
        });
        const result = await response.json();
        resultDiv.innerHTML = `<h3>Prediction: ${JSON.stringify(result.prediction)}</h3>`;
    } catch (error) {
        resultDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
}