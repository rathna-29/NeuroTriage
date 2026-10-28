# NeuroTriage
### Multimodal AI for Non-Verbal Patient Prioritization

## 1. Project Overview

NeuroTriage is a software-based, AI-assisted triage workflow prototype designed to support the prioritization of non-verbal or unconscious patients in emergency care settings.

The project explores the use of EEG signals, vital signs, and clinical information to assist healthcare professionals in reviewing patient information and identifying cases that may require urgent attention.

NeuroTriage is a clinician-facing decision-support prototype. It is not intended to replace professional medical judgment or established emergency triage protocols.

## 2. Problem Statement

Non-verbal and unconscious patients may be unable to communicate their symptoms, medical history, or the onset of a medical emergency. This can make initial assessment more difficult.

NeuroTriage aims to organize relevant patient information and explore AI-assisted analysis to support the clinical review process.

## 3. Project Objectives

- Accept and analyze EEG signal data using a machine-learning model.
- Record and manage patient information.
- Store and review vital signs and clinical records.
- Provide an AI-assisted assessment based on the implemented model.
- Support authenticated access for authorized users.
- Maintain patient records that can be retrieved using patient identifiers.
- Support record export for further review and documentation.

## 4. Main Features

- User authentication and role-based access.
- Patient registration and record management.
- Vital-sign recording.
- Clinical information management.
- EEG dataset processing and model-based classification.
- Patient monitoring and assessment history.
- Spreadsheet export of patient records.
- Input validation, CSRF protection, login rate limiting, security headers, and error handling.

Features should be considered implemented only where they are present and working in the current application.

## 5. Technology Stack

- **Programming language:** Python
- **Backend framework:** Flask
- **Database:** SQLite
- **Data processing:** NumPy and pandas
- **Machine learning:** scikit-learn
- **Frontend:** HTML, CSS, and JavaScript
- **Development environment:** Visual Studio Code

## 6. EEG Dataset

The project uses EEG data organized into four categories:

- Normal
- Ischemic
- Hemorrhagic
- Transient Ischemic Attack (TIA)

The dataset files currently used in development are `normal.csv`, `ischemic.csv`, `hemorrhagic.csv`, and `tia.csv`.

The original dataset publisher, author, licence, sampling frequency, and the meaning of the subject identifiers must be verified against the original source before being cited in a report or publication.

## 7. Machine-Learning Approach

The project uses a machine-learning pipeline to process EEG signals and generate predictions for the configured categories.

The implemented pipeline includes signal-feature extraction, feature scaling, and Logistic Regression classification.

Reported experimental results must be accompanied by the evaluation method and dataset limitations. Results from synthetic or otherwise unverified data do not establish clinical accuracy or real-world diagnostic performance.

## 8. System Workflow

1. An authorized user signs in.
2. The user selects or registers a patient record.
3. Patient information, vital signs, and clinical details are recorded.
4. EEG data is supplied for processing.
5. The configured model processes the signal and generates a prediction.
6. The application presents the available assessment information for clinician review.
7. Records can be retrieved and exported where supported.

## 9. Installation and Execution

1. Install a compatible version of Python.
2. Open the project folder in Visual Studio Code.
3. Create and activate a virtual environment.
4. Install the dependencies listed in `requirements.txt`.
5. Configure the environment variables required by the application.
6. Start the Flask application using the project's configured entry point.
7. Open the local address displayed in the terminal.

Use the project's actual configuration and dependency files as the source of truth for setup instructions.

## 10. Security and Data Handling

The application includes security measures such as CSRF protection, login rate limiting, input validation, and security-related response headers.

Before deployment, verify session-cookie settings, secret management, authorization rules, error handling, and database access controls. Development settings should not automatically be used in production.

Patient information and EEG recordings may contain sensitive data. Use appropriately protected data and restrict access to authorized users.

## 11. Limitations

- The project is a prototype and has not been established as a clinically validated medical system.
- Dataset provenance and recording parameters require verification.
- Experimental model performance may not generalize to real-world patients.
- Model predictions may be incorrect and require appropriate clinical review.
- The priority mapping must be confirmed with the project supervisor and must not be represented as an established clinical standard without supporting evidence.

## 12. Future Scope

- Validate the model using appropriately sourced and clinically reviewed EEG datasets.
- Evaluate performance using patient-independent testing and suitable clinical metrics.
- Improve monitoring, auditability, and secure record management.
- Conduct usability evaluation with appropriate clinical supervision.
- Investigate integration with established clinical workflows, subject to necessary approvals.

## 13. Disclaimer

NeuroTriage is an academic software prototype intended for research and demonstration. It must not be used as the sole basis for diagnosis, treatment, or emergency triage decisions. Clinical decisions must follow qualified professional judgment and established medical protocols.
