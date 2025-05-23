import pytest
from core.state_manager import user_state  # adjust import if needed
from routes.webhook import generate_response  # adjust import path accordingly
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

# Define your test cases
test_dataset = [
    {
        "input": "I have a headache and dizziness",
        "expected_department": "Neurology",
        "expected_response_keywords": ["neurolog", "appointment", "schedule"]
    },
    {
        "input": "I am having chest pain and shortness of breath",
        "expected_department": "Cardiology",
        "expected_response_keywords": ["cardiology", "appointment", "schedule"]
    },
    {
        "input": "My skin has developed a rash",
        "expected_department": "Dermatology",
        "expected_response_keywords": ["dermatology", "appointment", "schedule"]
    },
    {
        "input": "I have a fever and cough",
        "expected_department": "General Medicine",
        "expected_response_keywords": ["general medicine", "appointment", "schedule"]
    },
    {
        "input": "Toothache for two days",
        "expected_department": "Dentistry",
        "expected_response_keywords": ["dentistry", "appointment", "schedule"]
    }
]

@pytest.mark.parametrize("case", test_dataset)
def test_triage_department_and_response(case):
    user_id = "pytest_user"
    # Reset state for new test case
    user_state[user_id] = {"step": 1, "data": {}}

    # Generate triage response (step 1 triggers triage)
    response = generate_response(user_id, case["input"], 
                                 user_state[user_id]["step"], 
                                 user_state[user_id]["data"])

    predicted_department = user_state[user_id]["data"].get("department", "")

    # Check predicted department
    assert predicted_department == case["expected_department"], \
        f"Expected {case['expected_department']}, got {predicted_department}"

    # Check LLM response contains all expected keywords
    response_lower = response.lower()
    for kw in case["expected_response_keywords"]:
        assert kw in response_lower, f"Response missing keyword: '{kw}'"

def test_overall_metrics():
    true_labels = []
    pred_labels = []

    for case in test_dataset:
        user_id = "pytest_user"
        user_state[user_id] = {"step": 1, "data": {}}
        response = generate_response(user_id, case["input"],
                                     user_state[user_id]["step"],
                                     user_state[user_id]["data"])
        predicted_department = user_state[user_id]["data"].get("department", "")
        true_labels.append(case["expected_department"])
        pred_labels.append(predicted_department)

    accuracy = accuracy_score(true_labels, pred_labels)
    precision, recall, f1, _ = precision_recall_fscore_support(true_labels, pred_labels, average='weighted', zero_division=0)
    cm = confusion_matrix(true_labels, pred_labels, labels=list(set(true_labels)))

    print(f"Triage Accuracy: {accuracy:.2f}")
    print(f"Precision: {precision:.2f}, Recall: {recall:.2f}, F1-score: {f1:.2f}")
    print("Confusion Matrix:\n", cm)

    # Simple assertions for minimum performance (adjust thresholds as needed)
    assert accuracy > 0.7, "Accuracy too low"
    assert f1 > 0.7, "F1 score too low"
