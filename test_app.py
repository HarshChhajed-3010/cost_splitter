import pytest
import random
import json
from unittest.mock import MagicMock, patch
from streamlit.testing.v1 import AppTest
from app import recalculate_totals, calculate_total_expense

# ==========================================
# 1. MOCK DATA FOR OFFLINE TESTING
# ==========================================

MOCK_AI_RESPONSE = [
    {"original_name": "Fresh Roma Tomato, Each", "short_name": "Tomatoes", "cost": 5.58},
    {"original_name": "Great Value Whole Vitamin D Milk, Gallon", "short_name": "Milk", "cost": 12.08},
    {"original_name": "Marketside Fresh Spinach, 10 oz Bag", "short_name": "Spinach", "cost": 1.97}
]

# ==========================================
# 2. CORE LOGIC TESTS (MATH INTEGRITY)
# ==========================================

def test_100_random_math_combinations():
    """Verify that totals always sum up to the grand total across 100 random scenarios."""
    people_pool = ["Harsh", "Darsh", "Manav", "Darshan", "Amit", "Hitanshu"]

    for _ in range(100):
        num_people = random.randint(2, len(people_pool))
        current_people = random.sample(people_pool, num_people)
        num_expenses = random.randint(1, 10)
        expenses = []
        expected_grand_total = 0.0

        for j in range(num_expenses):
            cost = round(random.uniform(1.0, 100.0), 2)
            expected_grand_total += cost
            split_method = random.choice(['Equal', 'Weighted'])
            involved_people = random.sample(current_people, random.randint(1, num_people))

            expense = {
                'name': f"Item_{j}",
                'cost': cost,
                'split_method': split_method,
                'selected_people': involved_people
            }

            if split_method == 'Weighted':
                expense['quantities'] = {p: round(random.uniform(0.5, 5.0), 1) for p in involved_people}

            expenses.append(expense)

        totals = recalculate_totals(expenses, current_people)
        calculated_sum = sum(data['total'] for data in totals.values())

        # Check for penny-rounding errors
        assert calculated_sum == pytest.approx(expected_grand_total, abs=0.01)

# ==========================================
# 3. UI & INTEGRATION TESTS (MOCKED API)
# ==========================================

def test_app_initialization():
    """Ensure the app loads and session states are initialized."""
    at = AppTest.from_file("app.py").run()
    assert not at.exception
    assert "Cost Splitter for Shared Purchases" in at.title[0].value

@patch("app.genai.Client")
def test_ai_scanning_flow_no_api_call(mock_client_class):
    """
    Simulates the AI Scanning process without making real network requests.
    Verifies the queue handles the AI response correctly.
    """
    # 1. Setup Mock Client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Mock the response object from Gemini
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_AI_RESPONSE)
    mock_client.models.generate_content.return_value = mock_response

    # 2. Run App
    at = AppTest.from_file("app.py").run()
    
    # Select the first text input in the sidebar (API Key) and the first in the main body (People)
    at.sidebar.text_input[0].set_value("dummy_key")
    at.text_input[0].set_value("Harsh, Amit").run()
    
    # Verify AI Scan button logic
    from app import parse_receipt_images_ai
    items = parse_receipt_images_ai([MagicMock()], "dummy_key")
    
    assert len(items) == 3
    assert items[0]["short_name"] == "Tomatoes"
    assert items[1]["cost"] == 12.08

def test_select_all_behavior():
    """Verify that 'Select All' correctly populates involved people."""
    at = AppTest.from_file("app.py").run()
    
    # Populate the main "Enter names" input box
    at.text_input[0].set_value("Harsh, Darsh, Manav").run()
    
    # Check 'Select All' by passing its exact dynamic key
    at.checkbox(key="select_all_0").check().run()
    
    # Verify checkboxes are checked via their resulting dynamic keys
    assert at.checkbox(key="chk_Harsh_True_0").value is True
    assert at.checkbox(key="chk_Darsh_True_0").value is True

def test_name_shortening_toggle_logic():
    """Test if the UI correctly toggles between Shortened and Original names from the queue."""
    # We simulate an item in the queue directly
    at = AppTest.from_file("app.py")
    at.session_state.pending_receipt_items = [MOCK_AI_RESPONSE[0]]
    at.run()
    
    # Input a person so the rest of the form renders
    at.text_input[0].set_value("Harsh").run()

    # Locate the first radio button ("Name Format") and second text input ("Final Item Name")
    radio = at.radio[0]
    
    # Set to 'Original'
    radio.set_value("Original").run()
    assert at.text_input[1].value == "Fresh Roma Tomato, Each"
    
    # Set back to 'Shortened'
    at.radio[0].set_value("Shortened").run()
    assert at.text_input[1].value == "Tomatoes"

def test_weighted_split_math():
    """Specific check for weighted quantity logic."""
    expenses = [{
        'name': 'Steak',
        'cost': 100.0,
        'split_method': 'Weighted',
        'selected_people': ['Harsh', 'Darsh'],
        'quantities': {'Harsh': 3.0, 'Darsh': 1.0}
    }]
    people = ['Harsh', 'Darsh']
    
    totals = recalculate_totals(expenses, people)
    assert totals['Harsh']['total'] == 75.0
    assert totals['Darsh']['total'] == 25.0