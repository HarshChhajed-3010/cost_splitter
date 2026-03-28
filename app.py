import streamlit as st
import pandas as pd
import csv
from io import StringIO
import json
import re
from PIL import Image

# --- NEW: Imports for Cloud-Safe Browser Storage ---
from google import genai
import extra_streamlit_components as stx

# --- Cloud-Safe Cookie Manager ---
# Initialize directly (without cache) to comply with latest Streamlit widget rules
cookie_manager = stx.CookieManager()

def load_config():
    """Loads API key and presets from the user's browser cookies."""
    cookie_val = cookie_manager.get(cookie="cost_splitter_config")
    if cookie_val:
        try:
            if isinstance(cookie_val, str):
                return json.loads(cookie_val)
            return cookie_val
        except Exception:
            return {}
    return {}

def save_config(api_key, presets):
    """Saves API key and presets to the user's browser cookies (expires in 1 year)."""
    config = {
        "api_key": api_key,
        "presets": presets
    }
    cookie_manager.set("cost_splitter_config", json.dumps(config), max_age=31536000)

# Initialize configuration from the user's local browser
config_data = load_config()

# Initialize or update session state variables if not present
if 'expenses' not in st.session_state:
    st.session_state.expenses = []
if 'totals' not in st.session_state:
    st.session_state.totals = {}
if 'temp_expense' not in st.session_state:
    st.session_state.temp_expense = {}
if 'form_values' not in st.session_state:
    st.session_state.form_values = {"item_name": "", "total_cost": 0.0, "split_method": "Equal", "selected_people": []}
if 'presets' not in st.session_state:
    # Safely load presets from cookies, default to empty dict if none exist
    st.session_state.presets = config_data.get("presets", {})
if 'form_key' not in st.session_state:
    st.session_state.form_key = 0
if 'pending_receipt_items' not in st.session_state:
    st.session_state.pending_receipt_items = []
if 'current_receipt_index' not in st.session_state:
    st.session_state.current_receipt_index = 0

# --- AI Vision Parsing Function ---
def parse_receipt_images_ai(images, api_key):
    if not api_key:
        st.error("⚠️ Please enter a Google Gemini API Key in the sidebar to use the scanner.")
        return []

    try:
        client = genai.Client(api_key=api_key)
        prompt = """
        Analyze these screenshots of a shopping cart or receipt(s). 
        Extract all the purchased items and their final prices across all images. 
        CRITICAL INSTRUCTIONS:
        1. Ignore UI elements like "Review item", "Add", "Item reviewed".
        2. Ignore weights, quantities per pound (e.g., 50.0¢/lb), and crossed-out original prices.
        3. Ignore subtotals, taxes, and delivery fees.
        4. Return ONLY a valid JSON array of objects. Do not include markdown formatting or backticks.
        5. For each item, provide the 'original_name' (exactly as it appears), a 'short_name' (a concise, meaningful 1-3 word summary like "Tomatoes", "Milk", or "Avocados", avoiding sizes/brands unless necessary), and the 'cost'.
        
        Format exactly like this example:
        [
            {"original_name": "Fresh Roma Tomato, Each", "short_name": "Tomatoes", "cost": 5.58},
            {"original_name": "Great Value Whole Vitamin D Milk, Gallon, 128 fl oz", "short_name": "Milk", "cost": 12.08}
        ]
        """
        contents = [prompt] + images
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=contents
        )
        response_text = response.text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
            
        items = json.loads(response_text)
        
        valid_items = []
        for item in items:
            orig_name = item.get("original_name", item.get("name", ""))
            short_name = item.get("short_name", orig_name)
            cost = item.get("cost")
            
            if orig_name and cost is not None:
                try:
                    valid_items.append({
                        "original_name": str(orig_name).strip(), 
                        "short_name": str(short_name).strip(),
                        "cost": float(cost)
                    })
                except ValueError:
                    pass
        return valid_items
    except Exception as e:
        st.error(f"AI Parsing Error: {e}")
        return []

def recalculate_totals(expenses, people):
    totals = {person: {'total': 0, 'items': []} for person in people}
    for expense in expenses:
        item = expense['name']
        cost = expense['cost']
        if expense['split_method'] == 'Equal':
            num_people = len(expense['selected_people'])
            if num_people > 0:
                split_cost = cost / num_people
                for person in expense['selected_people']:
                    totals[person]['total'] += split_cost
                    totals[person]['items'].append((item, split_cost))
        elif expense['split_method'] == 'Weighted':
            total_quantity = sum(expense['quantities'].values())
            if total_quantity > 0:
                for person, quantity in expense['quantities'].items():
                    person_cost = (quantity / total_quantity) * cost
                    totals[person]['total'] += person_cost
                    totals[person]['items'].append((item, person_cost))
    return totals

def generate_csv(totals):
    csv_file = StringIO()
    fieldnames = ['Person', 'Total', 'Items']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    for person, data in totals.items():
        items_str = "; ".join([f"{item}: ${cost:.2f}" for item, cost in data['items']])
        writer.writerow({'Person': person, 'Total': f"{data['total']:.2f}", 'Items': items_str})
    return csv_file.getvalue()

def reset_form_values():
    st.session_state.form_values = {"item_name": "", "total_cost": 0.0, "split_method": "Equal", "selected_people": []}
    st.session_state.form_key += 1

def calculate_total_expense(expenses):
    return sum(expense['cost'] for expense in expenses)

def cost_splitter_app():
    st.title("Cost Splitter for Shared Purchases")

    # --- Sidebar setup ---
    st.sidebar.header("🔑 API Settings")
    st.sidebar.write("Settings are securely saved to your browser cookies.")
    
    # Load saved key from user's browser cookie
    saved_api_key = config_data.get("api_key", "")
    api_key = st.sidebar.text_input("Gemini API Key", value=saved_api_key, type="password")
    
    # Save API key to their browser if it changed
    if api_key and api_key != saved_api_key:
        save_config(api_key, st.session_state.presets)
        
    st.sidebar.markdown("[Get a free key here](https://aistudio.google.com/app/apikey)")
    st.sidebar.divider()

    st.sidebar.header("💾 Manage Saved Groups")
    new_preset_name = st.sidebar.text_input("Group Name (e.g., Roommates)")
    new_preset_people = st.sidebar.text_input("Names (comma-separated)", key="preset_input")
    
    if st.sidebar.button("Save Group"):
        if new_preset_name and new_preset_people:
            st.session_state.presets[new_preset_name] = [p.strip() for p in new_preset_people.split(',') if p.strip()]
            save_config(api_key, st.session_state.presets)
            st.sidebar.success(f"Saved group: {new_preset_name}")
            st.rerun()
        else:
            st.sidebar.warning("Please provide both a name and people.")

    # --- Dropdown to load saved groups ---
    st.subheader("1. Who is splitting the cost?")
    preset_options = ["Custom"] + list(st.session_state.presets.keys())
    selected_preset = st.selectbox("Load a saved group:", preset_options)

    default_people_text = ""
    if selected_preset != "Custom":
        default_people_text = ", ".join(st.session_state.presets[selected_preset])

    people_input = st.text_input("Enter names (comma-separated)", value=default_people_text)
    
    if people_input:
        st.session_state.people = [name.strip() for name in people_input.split(',') if name.strip()]
    else:
        st.session_state.people = []

    st.divider()

    # --- Expense fields ---
    st.subheader("2. Add an Expense")
    
    uploaded_files = st.file_uploader("🧾 Optional: Upload Receipt Screenshots", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    if uploaded_files and st.button("Scan with AI"):
        if not api_key:
            st.error("Please enter your API Key in the sidebar first!")
        else:
            with st.spinner("AI is analyzing images..."):
                images = [Image.open(file) for file in uploaded_files]
                items = parse_receipt_images_ai(images, api_key)
                if items:
                    st.session_state.pending_receipt_items.extend(items)
                    st.session_state.current_receipt_index = 0
                    st.success(f"Found {len(items)} items!")
                else:
                    st.error("Could not parse. Check image quality or API key.")
                
    if st.session_state.pending_receipt_items:
        if st.session_state.current_receipt_index >= len(st.session_state.pending_receipt_items):
            st.session_state.current_receipt_index = max(0, len(st.session_state.pending_receipt_items) - 1)
            
        idx = st.session_state.current_receipt_index
        current_item = st.session_state.pending_receipt_items[idx]
        
        st.info(f"📋 Reviewing item {idx + 1} of {len(st.session_state.pending_receipt_items)}.")
        
        col_prev, col_remove, col_next = st.columns(3)
        with col_prev:
            if st.button("⬅️ Previous", disabled=(idx == 0)):
                st.session_state.current_receipt_index -= 1
                st.rerun()
        with col_remove:
            if st.button("🗑️ Remove"):
                st.session_state.pending_receipt_items.pop(idx)
                st.rerun()
        with col_next:
            if st.button("Next ➡️", disabled=(idx >= len(st.session_state.pending_receipt_items) - 1)):
                st.session_state.current_receipt_index += 1
                st.rerun()
                
        default_orig_name = current_item.get('original_name', current_item.get('name', ''))
        default_short_name = current_item.get('short_name', default_orig_name)
        default_cost = current_item['cost']

        name_preference = st.radio(
            "Name Format", ["Shortened", "Original"],
            format_func=lambda x: f"{x}: {default_short_name if x == 'Shortened' else default_orig_name}",
            horizontal=True
        )
        selected_default_name = default_short_name if name_preference == "Shortened" else default_orig_name
    else:
        selected_default_name = st.session_state.form_values['item_name']
        default_cost = st.session_state.form_values['total_cost']

    item_name = st.text_input("Final Item Name", value=selected_default_name)
    total_cost = st.number_input("Total Cost", format="%.2f", value=default_cost)
    split_method = st.radio("Splitting Method", ['Equal', 'Weighted'], index=['Equal', 'Weighted'].index(st.session_state.form_values['split_method']))

    selected_people = []
    st.write("**Select People Involved:**")
    select_all = st.checkbox("Select All People", key=f"select_all_{st.session_state.form_key}")

    for person in st.session_state.people:
        is_checked_by_default = select_all or (person in st.session_state.form_values['selected_people'])
        checked = st.checkbox(person, value=is_checked_by_default, key=f"chk_{person}_{select_all}_{st.session_state.form_key}")
        if checked:
            selected_people.append(person)

    if st.button("Add/Configure Expense"):
        if not selected_people:
            st.error("⚠️ Select at least one person.")
        else:
            if st.session_state.pending_receipt_items:
                st.session_state.pending_receipt_items.pop(st.session_state.current_receipt_index)
                
            if split_method == 'Weighted':
                st.session_state.temp_expense = {'name': item_name, 'cost': total_cost, 'split_method': split_method, 'selected_people': selected_people}
                st.session_state.form_values['split_method'] = split_method
            else:
                st.session_state.expenses.append({'name': item_name, 'cost': total_cost, 'split_method': split_method, 'selected_people': selected_people})
                reset_form_values()
                st.rerun()

    if st.session_state.get('temp_expense'):
        st.info(f"Quantities for: {st.session_state.temp_expense['name']}")
        quantities = {person: st.number_input(f"Quantity for {person}:", min_value=0.0, value=1.0, format="%.2f", key=f"qty_{person}") for person in st.session_state.temp_expense['selected_people']}
        if st.button("Confirm Weighted Expense"):
            if sum(quantities.values()) == 0:
                st.error("⚠️ Total must be > 0.")
            else:
                st.session_state.expenses.append({**st.session_state.temp_expense, 'quantities': quantities})
                st.session_state.temp_expense = {}
                reset_form_values()
                st.rerun()

    st.divider()
    st.subheader("3. Breakdown & Totals")
    st.session_state.totals = recalculate_totals(st.session_state.expenses, st.session_state.people)
    total_expense = calculate_total_expense(st.session_state.expenses)
    st.write(f"**Total Receipt Expense:** ${total_expense:.2f}")
    
    if st.session_state.totals:
        for person, data in st.session_state.totals.items():
            if data['total'] > 0:
                with st.expander(f"**{person}**: ${data['total']:.2f}"):
                    for i_name, i_cost in data['items']:
                        st.write(f"- {i_name}: ${i_cost:.2f}")

    st.write("---")
    expense_names = [e['name'] for e in st.session_state.expenses]
    selected_expense_to_delete = st.selectbox("Select an expense to delete:", [""] + expense_names)
    if st.button("Delete Selected Expense"):
        if selected_expense_to_delete:
            st.session_state.expenses = [e for e in st.session_state.expenses if e['name'] != selected_expense_to_delete]
            st.rerun()

    if st.button("Export to CSV"):
        csv_data = generate_csv(st.session_state.totals)
        st.download_button(label="Download CSV", data=csv_data, file_name="cost_splits.csv", mime='text/csv')

    st.divider()
    st.caption("This project was inspired from the work of Hitanshu Shah and Amit Patel")

if __name__ == "__main__":
    cost_splitter_app()