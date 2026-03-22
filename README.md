# **Cost Splitter (AI-Powered)**

A smart, Python-based web application built with **Streamlit** for splitting shared expenses.

**Cost Splitter** eliminates the friction of manual data entry by using Google’s **Gemini Vision AI** to read grocery receipts and shopping cart screenshots. Simply upload your screenshots, let the AI extract the items and prices, and assign them to your friends.

---

## ✨ **Key Features**

- **AI Receipt Scanner:**  
  Upload multiple screenshots at once. The app uses `google-genai` (**Gemini 3 Flash**) to automatically parse item names, filter out noise (such as UI buttons and crossed-out prices), and queue them for review.

- **Smart Queue System:**  
  Navigate back and forth through scanned items, toggle between **Original** and **Shortened** item names, or manually tweak them.

- **Customizable Splitting:**  
  Split items **Equally** or assign **Weighted** quantities if someone bought more of a specific item.

- **Persistent Saved Groups:**  
  Save your recurring friend groups (for example, **Roommates** or **Miami Trip**) locally so you never have to retype names.

- **Export & Analytics:**  
  View real-time totals, itemized breakdowns, and export the final calculations to a **CSV**.

- **Offline Test Suite:**  
  Includes a robust **pytest** suite with mocked API calls to safely verify math integrity without consuming API credits.

---

## 🚀 **Setup & Installation**

Follow the steps below for your operating system to get the app running locally.

### **1. Clone the Repository**

```bash
git clone https://github.com/HarshChhajed-3010/cost_splitter.git
cd cost-splitter
```

### **2. Set up a Virtual Environment**

It is highly recommended to use a virtual environment to manage dependencies.

**For Ubuntu & macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**For Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

### **3. Install Dependencies**

Make sure your virtual environment is active, then run:

```bash
pip install -r requirements.txt
```

---

## ⚙️ **Configuration (Required Before Running)**

Before you launch the app, you need to configure your local settings and API key.

1. Open the `config.json` file in the root directory.  
2. Replace `"your_api_key"` with your free **Google Gemini API Key** (you can get one at [Google AI Studio](https://aistudio.google.com/app/apikey)).  
3. Update the `"presets"` dictionary with your actual group names and members.

Your `config.json` should look like this:

```json
{
  "api_key": "AIzaSyYourSecretKeyHere...",
  "presets": {
    "Roommates": ["Harsh", "Darsh", "Manav", "Darshan"],
    "Trip Group": ["Amit", "Hitanshu", "Harsh"]
  }
}
```

---

## 🏃‍♂️ **Running the App**

Once configured, start the Streamlit server.

**For Ubuntu & macOS:**

```bash
streamlit run app.py
```

**For Windows:**

```bash
python -m streamlit run app.py
```

The app will automatically open in your default web browser at:

`http://localhost:8501`

---

## **Credits**

This project was inspired by the work of **Hitanshu Shah** ,**Darsh Chandura** and **Amit Patel**.

