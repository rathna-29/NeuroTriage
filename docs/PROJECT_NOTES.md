# NeuroTriage — Project Notes

## 1. One-Sentence Summary

NeuroTriage is a Flask and SQLite web application prototype that manages patient records and provides an AI-assisted priority indication from EEG features to support clinician review.

## 2. Suggested Report Structure

1. Introduction and problem statement
2. Project objectives and scope
3. System architecture and database design
4. Dataset description and source verification
5. EEG preprocessing and feature extraction
6. Machine-learning methodology
7. Experimental results and evaluation
8. Application security and record management
9. Limitations and ethical considerations
10. Conclusion and future enhancements

## 3. Demonstration Plan

1. Log in using an authorized demo account.
2. Display the dashboard.
3. Register a test patient.
4. Add vital signs and clinical information.
5. Upload a supported EEG CSV file.
6. Show the model output and project-defined priority indication.
7. Demonstrate patient record retrieval and editing.
8. Review the available audit history.
9. Demonstrate simulated monitoring, if available.
10. Export a spreadsheet and open it.
11. Verify access restrictions using the configured user roles.

Only demonstrate features that have been tested successfully.

## 4. Likely Viva Questions

**Q1. What problem does NeuroTriage address?**

It explores how EEG data and organized patient records can support the prioritization workflow for patients who cannot communicate their symptoms.

**Q2. Does NeuroTriage diagnose a patient?**

No. It is an academic decision-support prototype, not a clinically validated diagnostic system.

**Q3. Which machine-learning model is used?**

The current project notes identify Logistic Regression with extracted EEG features. Confirm this against the saved model and training script before the final presentation.

**Q4. What are the model inputs?**

The described model uses EEG-derived features. Vital signs and clinical information are stored for review and should not be described as model inputs unless the implementation changes.

**Q5. Why is dataset verification important?**

The original source, licence, recording parameters, and subject identifiers affect reproducibility and how results can be interpreted.

**Q6. Does high test accuracy establish clinical usefulness?**

No. Results from synthetic or easily separable data do not demonstrate performance on real patients.

**Q7. Is monitoring connected to a real EEG device?**

The described monitoring demonstration is simulated. It must not be presented as live hardware acquisition.

**Q8. Is the priority mapping a clinical standard?**

No. The mapping is provisional and project-defined until it has been reviewed and approved through the appropriate clinical or academic process.

**Q9. Why use SQLite?**

SQLite provides a lightweight local database for storing and retrieving application records during development.

**Q10. What are the main limitations?**

Dataset provenance requires verification, clinical validation has not been established, and predictions may not generalize to real-world patients.

## 5. Facts to Verify Before Submission

- Original EEG dataset page, exact title, author, licence, and whether it is synthetic.
- Actual sampling rate and recording units.
- Meaning of `subject_k` across the dataset files.
- Model training and evaluation procedure, including patient-independent validation.
- Current model metrics from reproducible output.
- Project-defined priority mapping, reviewed with the project supervisor.
- Which features are fully implemented and tested.

## 6. Claims to Avoid

- Claiming that NeuroTriage is clinically validated.
- Describing predictions as confirmed diagnoses.
- Claiming real-time EEG device monitoring when only simulation is available.
- Claiming that vital signs affect the model when they are not model inputs.
- Presenting a project-defined priority mapping as an established medical standard.
- Citing an unverified dataset source or licence.
- Reporting evaluation results without confirming the experiment and test split.

## 7. Future Enhancements

- Verify and document dataset provenance and recording parameters.
- Evaluate the model on suitable independent datasets.
- Investigate additional EEG features after verifying the sampling rate.
- Improve secure access control, auditability, and data protection.
- Explore validated multimodal modelling if appropriately labelled data becomes available.
- Conduct appropriate clinical and usability evaluation before any real-world deployment.

## 8. Disclaimer

NeuroTriage is an academic software prototype. It must not be used as the sole basis for diagnosis, treatment, or emergency triage decisions. Clinical decisions must follow qualified professional judgment and established protocols.
