import pytest
import random
import json
from unittest.mock import MagicMock, patch
from streamlit.testing.v1 import AppTest

# Import the core logic functions directly from your app
from app import recalculate_totals, calculate_total_expense, generate_csv, parse_receipt_images_ai

# ==========================================
# 1. PURE LOGIC TESTS (Math & Conversions)
# ==========================================

def test_calculate_total_expense():
    """Ensure the grand total calculates correctly across all expenses."""
    expenses = [
        {'cost': 15.50},
        {'cost': 10.25},
        {'cost': 4.25}
    ]
    assert calculate_total_expense(expenses) == 30.0

def test_recalculate_totals_equal_split():
    """Verify standard equal split math."""
    expenses = [{
        'name': 'Pizza',
        'cost': 30.0,
        'split_method': 'Equal',
        'selected_people': ['Harsh', 'Darsh', 'Manav']
    }]
    people = ['Harsh', 'Darsh', 'Manav', 'Amit'] # Amit bought nothing
    
    totals = recalculate_totals(expenses, people)
    
    assert totals['Harsh']['total'] == 10.0
    assert totals['Darsh']['total'] == 10.0
    assert totals['Manav']['total'] == 10.0
    assert totals['Amit']['total'] == 0.0

def test_recalculate_totals_weighted_split():
    """Verify custom weighted split math."""
    expenses = [{
        'name': 'Drinks',
        'cost': 50.0,
        'split_method': 'Weighted',
        'selected_people': ['Harsh', 'Hitanshu'],
        'quantities': {'Harsh': 4.0, 'Hitanshu': 1.0} # 5 drinks total. Harsh pays 4/5, Hitanshu 1/5
    }]
    people = ['Harsh', 'Hitanshu']
    
    totals = recalculate_totals(expenses, people)
    
    assert totals['Harsh']['total'] == 40.0
    assert totals['Hitanshu']['total'] == 10.0

def test_generate_csv():
    """Ensure the dictionary structure correctly converts to a CSV string."""
    totals = {
        'Darsh': {'total': 15.5, 'items': [('Burgers', 15.5)]},
        'Harsh': {'total': 5.0, 'items': [('Fries', 5.0)]}
    }
    csv_string = generate_csv(totals)
    
    # Check if headers and data are in the string
    assert "Person,Total,Items" in csv_string
    assert "Darsh,15.50,Burgers: $15.50" in csv_string
    assert "Harsh,5.00,Fries: $5.00" in csv_string

def test_100_random_math_combinations():
    """Robust test: Verify that totals always sum up to the grand total across 100 random scenarios."""
    people_pool = ["Harsh", "Darsh", "Manav", "Amit", "Hitanshu", "Darsh Chandura"]

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
# 2. AI PARSING TESTS (MOCKED API)
# ==========================================

@patch('app.genai.Client')
def test_parse_receipt_images_ai(mock_client_class):
    """Simulate the Gemini API returning data to ensure our parsing logic handles the JSON correctly."""
    # 1. Setup Mock API Response
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    # Fixed the malformed JSON string so the parser won't crash
    mock_response.text = ''