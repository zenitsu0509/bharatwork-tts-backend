class BulkPathAudioGenerator {
    constructor() {
        this.csvData = null;
        this.selectedRecords = new Set();
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Step 1: Load CSV
        document.getElementById('loadCsvBtn').addEventListener('click', () => {
            this.loadCsvData();
        });

        // CSV path input
        document.getElementById('csvPath').addEventListener('input', (e) => {
            const path = e.target.value;
            const display = document.getElementById('csvPathDisplay');
            if (path) {
                display.textContent = `File path: ${path}`;
                display.style.display = 'block';
            } else {
                display.style.display = 'none';
            }
        });

        // Step 2: Record Selection
        document.getElementById('selectAllBtn').addEventListener('click', () => {
            this.selectAllRecords();
        });

        document.getElementById('deselectAllBtn').addEventListener('click', () => {
            this.deselectAllRecords();
        });

        // Step 3: Generate Audio
        document.getElementById('generateAudioBtn').addEventListener('click', () => {
            this.generateBulkAudio();
        });
    }

    async loadCsvData() {
        const csvPath = document.getElementById('csvPath').value.trim();
        const btn = document.getElementById('loadCsvBtn');
        const resultDiv = document.getElementById('csvResult');
        
        if (!csvPath) {
            alert('Please enter a CSV file path');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Loading CSV...';
        
        try {
            const response = await fetch('/api/process-csv-path', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    csv_path: csvPath
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.csvData = data;
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `
                    <div class="success-message">
                        ✅ ${data.message}
                    </div>
                    <div class="csv-preview">
                        <h4>Preview (First ${data.preview.length} records):</h4>
                        <table class="preview-table">
                            <thead>
                                <tr>
                                    <th>Index</th>
                                    <th>Name</th>
                                    <th>Company</th>
                                    <th>Salary</th>
                                    <th>Phone</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.preview.map(record => `
                                    <tr>
                                        <td>${record.index}</td>
                                        <td>${record.name}</td>
                                        <td>${record.company_name}</td>
                                        <td>${record.salary}</td>
                                        <td>${record.phone_number}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;

                console.log('CSV loaded successfully, data:', data);
                console.log('Preview data:', data.preview);
                this.renderRecordSelector(data.preview);
                
                // Activate steps 2, 3, 4
                document.getElementById('step2').classList.add('active');
                document.getElementById('step3').classList.add('active');
                document.getElementById('step4').classList.add('active');
                
            } else {
                throw new Error(data.detail || 'Failed to load CSV data');
            }
        } catch (error) {
            console.error('CSV loading error:', error);
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div class="error-message">
                    ❌ Error: ${error.message}
                </div>
            `;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span>📄</span> Load CSV Data';
        }
    }

    renderRecordSelector(records) {
        console.log('renderRecordSelector called with:', records);
        
        const selectorDiv = document.getElementById('recordSelector');
        console.log('selectorDiv found:', selectorDiv);
        
        if (!selectorDiv) {
            console.error('recordSelector element not found!');
            return;
        }
        
        if (!records || records.length === 0) {
            console.warn('No records provided to renderRecordSelector');
            return;
        }
        
        selectorDiv.style.display = 'block';
        
        const checkboxes = records.map(record => `
            <div class="record-item">
                <input type="checkbox" id="record_${record.index}" value="${record.index}" onchange="bulkGenerator.updateSelection()">
                <div class="record-info">
                    <div class="record-name">${record.name}</div>
                    <div class="record-details">${record.company_name} • ${record.salary} • ${record.phone_number}</div>
                </div>
            </div>
        `).join('');
        
        console.log('Generated checkboxes HTML:', checkboxes);
        selectorDiv.innerHTML = checkboxes;
        
        console.log('Record selector rendered successfully');
    }

    selectAllRecords() {
        const checkboxes = document.querySelectorAll('#recordSelector input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
            this.selectedRecords.add(parseInt(checkbox.value));
        });
        this.updateSelectionCount();
    }

    deselectAllRecords() {
        const checkboxes = document.querySelectorAll('#recordSelector input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        this.selectedRecords.clear();
        this.updateSelectionCount();
    }

    updateSelection() {
        const checkboxes = document.querySelectorAll('#recordSelector input[type="checkbox"]');
        this.selectedRecords.clear();
        
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                this.selectedRecords.add(parseInt(checkbox.value));
            }
        });
        
        this.updateSelectionCount();
    }

    updateSelectionCount() {
        const countSpan = document.getElementById('selectionCount');
        countSpan.textContent = `${this.selectedRecords.size} records selected`;
    }

    async generateBulkAudio() {
        const csvPath = document.getElementById('csvPath').value.trim();
        const outputPath = document.getElementById('outputPath').value.trim();
        const btn = document.getElementById('generateAudioBtn');
        const resultDiv = document.getElementById('audioResult');
        const progressContainer = document.getElementById('progressContainer');
        
        if (!csvPath) {
            alert('Please specify a CSV file path');
            return;
        }

        if (this.selectedRecords.size === 0) {
            alert('Please select at least one record');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Generating Audio...';
        progressContainer.style.display = 'block';
        
        this.updateProgress(0, 'Starting audio generation...');
        
        try {
            const selectedIndices = Array.from(this.selectedRecords);
            
            const response = await fetch('/api/generate-bulk-audio-path', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    csv_path: csvPath,
                    selected_indices: selectedIndices,
                    output_folder: outputPath || null
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.updateProgress(100, 'Generation complete!');
                
                resultDiv.style.display = 'block';
                
                if (data.saved_files) {
                    // Files saved to folder
                    resultDiv.innerHTML = `
                        <div class="success-message">
                            ✅ Successfully generated ${data.total_generated} audio files!
                            <br>Files saved to: <strong>${data.output_folder}</strong>
                        </div>
                        <div class="saved-files">
                            <h4>Generated Files:</h4>
                            <ul>
                                ${data.saved_files.map(file => 
                                    `<li><strong>${file.name}</strong> (${file.company_name}) → ${file.file_path}</li>`
                                ).join('')}
                            </ul>
                        </div>
                    `;
                } else {
                    // Files returned as base64 (for download)
                    resultDiv.innerHTML = `
                        <div class="success-message">
                            ✅ Successfully generated ${data.total_generated} audio files!
                        </div>
                        <div class="audio-downloads">
                            <h4>Download Audio Files:</h4>
                            ${data.audio_files.map(file => `
                                <div style="margin: 10px 0;">
                                    <strong>${file.name}</strong> (${file.company_name})
                                    <button class="btn" onclick="bulkGenerator.downloadAudio('${file.audio_base64}', '${file.name}_${file.company_name}.wav')">
                                        <span>⬇️</span> Download
                                    </button>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
                
            } else {
                throw new Error(data.detail || 'Failed to generate audio files');
            }
        } catch (error) {
            console.error('Bulk audio generation error:', error);
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div class="error-message">
                    ❌ Error: ${error.message}
                </div>
            `;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span>🔊</span> Generate Audio Files';
            
            setTimeout(() => {
                progressContainer.style.display = 'none';
            }, 3000);
        }
    }

    updateProgress(percentage, message) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        progressFill.style.width = `${percentage}%`;
        progressText.textContent = message;
    }

    downloadAudio(base64Data, filename) {
        try {
            // Convert base64 to blob
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'audio/wav' });
            
            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename.replace(/\s+/g, '_');
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error('Download error:', error);
            alert('Failed to download audio file');
        }
    }
}

// Initialize the application
const bulkGenerator = new BulkPathAudioGenerator();