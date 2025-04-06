"""
HTML template for the verification page that displays parishioner details
"""

verification_page_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Parishioner Details Verification</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f7f7f7;
        }
        .container {
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .header img {
            max-width: 200px;
            margin-bottom: 15px;
        }
        h1 {
            color: #2c3e50;
            margin-top: 0;
        }
        .content {
            margin-bottom: 30px;
        }
        .login-form {
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .details-section {
            display: none;
        }
        .section {
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        .section h2 {
            color: #3498db;
            margin-top: 0;
            font-size: 1.3em;
        }
        .detail-group {
            margin-bottom: 15px;
        }
        .detail-label {
            font-weight: bold;
            margin-bottom: 5px;
            color: #555;
        }
        .detail-value {
            background-color: #f8f9fa;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }
        .message {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .info {
            background-color: #e3f2fd;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        button, input[type="password"] {
            padding: 10px 15px;
            border-radius: 4px;
            border: 1px solid #ddd;
            width: 100%;
            margin-bottom: 15px;
            box-sizing: border-box;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background-color: #2980b9;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #777;
            font-size: 0.9em;
        }
        .update-notice {
            margin-top: 30px;
            padding: 15px;
            background-color: #fffacd;
            border-left: 4px solid #ffd700;
            color: #856404;
        }
        .confirmation-section {
            margin-top: 30px;
            text-align: center;
        }
        .confirm-button {
            background-color: #28a745;
            color: white;
            padding: 15px 30px;
            font-size: 1.1em;
            border-radius: 5px;
            cursor: pointer;
            border: none;
            transition: background-color 0.3s;
            max-width: 400px;
            margin: 0 auto;
        }
        .confirm-button:hover {
            background-color: #218838;
        }
        .confirm-button:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        .confirmation-message {
            margin-top: 20px;
            padding: 15px;
            background-color: #d4edda;
            color: #155724;
            border-radius: 5px;
            font-weight: bold;
            font-size: 1.1em;
        }
        @media (max-width: 600px) {
            .container {
                padding: 15px;
                margin: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="https://res.cloudinary.com/jondexter/image/upload/v1735725861/sfoacc-logo_ncynib.png" alt="SFOACC Logo">
            <h1>Parishioner Details Verification</h1>
        </div>
        
        <div class="content">
            <div class="login-form" id="accessForm">
                <p>Please enter your date of birth in the format <strong>DDMMYYYY</strong> to view your information:</p>
                <div id="errorMessage" class="message error" style="display: none;"></div>
                <input type="password" id="accessCode" placeholder="Enter your date of birth (e.g., 15012000)">
                <button id="submitAccessCode">Access My Information</button>
            </div>
            
            <div class="details-section" id="detailsSection">
                <!-- Personal Information Section -->
                <div class="section">
                    <h2>Personal Information</h2>
                    {{PERSONAL_INFO}}
                </div>
                
                <!-- Contact Information Section -->
                <div class="section">
                    <h2>Contact Information</h2>
                    {{CONTACT_INFO}}
                </div>
                
                <!-- Family Information Section -->
                <div class="section">
                    <h2>Family Information</h2>
                    {{FAMILY_INFO}}
                </div>
                
                <!-- Occupation Information Section -->
                <div class="section">
                    <h2>Occupation</h2>
                    {{OCCUPATION_INFO}}
                </div>
                
                <!-- Church Related Information Section -->
                <div class="section">
                    <h2>Church Information</h2>
                    {{CHURCH_INFO}}
                </div>
                
                <!-- Societies Section -->
                <div class="section">
                    <h2>Societies</h2>
                    {{SOCIETIES_INFO}}
                </div>
                
                <!-- Sacraments Section -->
                <div class="section">
                    <h2>Sacraments</h2>
                    {{SACRAMENTS_INFO}}
                </div>
                
                <!-- Additional Information Section -->
                <div class="section">
                    <h2>Additional Information</h2>
                    {{ADDITIONAL_INFO}}
                </div>
                
                <!-- Confirmation Button -->
                {{CONFIRMATION_BUTTON}}
                
                <div class="update-notice">
                    <p><strong>Need to update your information?</strong> If any of the details above are incorrect or have changed, 
                    please visit the church information desk to update your records.</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>&copy; {{CURRENT_YEAR}} SFOACC Church. All rights reserved.</p>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const correctAccessCode = "{{ACCESS_CODE}}";
            const accessForm = document.getElementById('accessForm');
            const detailsSection = document.getElementById('detailsSection');
            const errorMessage = document.getElementById('errorMessage');
            const accessCodeInput = document.getElementById('accessCode');
            const submitButton = document.getElementById('submitAccessCode');
            
            // Validate access code
            submitButton.addEventListener('click', function() {
                const enteredCode = accessCodeInput.value.trim();
                
                if (enteredCode === correctAccessCode) {
                    // Hide form, show details
                    accessForm.style.display = 'none';
                    detailsSection.style.display = 'block';
                    // Scroll to top
                    window.scrollTo(0, 0);
                } else {
                    // Show error
                    errorMessage.textContent = 'Invalid date of birth. Please enter in DDMMYYYY format.';
                    errorMessage.style.display = 'block';
                    accessCodeInput.value = '';
                    
                    // Auto hide error after 3 seconds
                    setTimeout(function() {
                        errorMessage.style.display = 'none';
                    }, 3000);
                }
            });
            
            // Also trigger validation on Enter key
            accessCodeInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    submitButton.click();
                }
            });
        });
    </script>
</body>
</html>
"""