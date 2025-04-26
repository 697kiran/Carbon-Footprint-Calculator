# Carbon Footprint Calculator

This repository hosts a Carbon Footprint Calculator, a web application that enables users to estimate carbon emissions from activities such as electricity usage, car travel, bus travel, natural gas consumption, and train travel. Built with a React frontend, a Flask backend, and a Python-based emission calculation module powered by the Climatiq API, the app compares emissions calculated via the API with an algorithmic approach, factoring in regional and seasonal variations.

## Features

- **User-Friendly Interface:** Add, manage, and remove activities through a modern, responsive React UI with custom CSS styling.
- **Dual Calculation Methods:** Estimates emissions using the Climatiq API and a custom algorithm, displaying comparisons with differences and percentages.
- **Regional Support:** Supports multiple regions (e.g., US, EU, UK) with region-specific emission factors.
- **Responsive Design:** Optimized for both desktop and mobile devices with animations and hover effects.

## Repository Structure

```
Carbon-Footprint-Calculator/
├── src1/
│   ├── App.css
│   ├── App.js
│   ├── index.css
│   ├── index.js
│   └── reportWebVitals.js
├── app.py
├── check_api.py
├── run_calculation.py
├── LICENSE
├── README.md

```

## Prerequisites

- Node.js (v16 or higher) for the React frontend
- Python (3.8 or higher) for the Flask backend and calculation script
- Climatiq API Key (obtain one by signing up at [Climatiq](https://www.climatiq.io/))
- Git for cloning the repository

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/697kiran/Carbon-Footprint-Calculator.git
cd Carbon-Footprint-Calculator
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory and add your Climatiq API key:

```env
CLIMATIQ_API_KEY=your_climatiq_api_key
```

### 3. Backend Setup

Install Python dependencies:

```bash
pip install flask flask-cors python-dotenv requests
```

Ensure `app.py` and `check_api.py` are in the root directory.

### 4. Frontend Setup

Navigate to the `frontend/` directory:

```bash
cd frontend
```

Install Node.js dependencies:

```bash
npm install
```

Verify that `App.jsx` and `App.css` are in `frontend/src/`.

## Running the Application

### Start the Flask Backend

```bash
python app.py
```

The backend will run at [http://localhost:5000](http://localhost:5000).

### Start the React Frontend (in a new terminal)

From the `frontend/` directory:

```bash
npm start
```

The frontend will run at [http://localhost:3000](http://localhost:3000).

Open your browser and go to [http://localhost:3000](http://localhost:3000) to access the calculator.

## Usage

### Add Activities

- Select an activity type (e.g., Electricity Usage, Car Travel).
- Enter the amount (e.g., 100 kWh, 50 km).
- Choose a unit (e.g., kWh, miles) and region (e.g., US, EU).
- Click **Add Activity** to add it to the list.

### Calculate Emissions

- After adding activities, click **Calculate Emissions**.
- View results showing API-based and algorithmic emissions, including total emissions and per-activity details with differences.

### Remove Activities

- Click the ✕ button next to an activity to remove it.

## Example

To calculate emissions for 100 kWh of electricity in the US:

1. Select **Electricity Usage**, enter **100** for amount, select **kWh** and **US**.
2. Click **Add Activity**.
3. Click **Calculate Emissions** to see results, e.g.:

```
API: 38 kg CO2e
Algorithm: 35.64 kg CO2e
Difference:  -2.36 kg (-6.2%)
```


### Backend

- Flask
- Flask-CORS
- python-dotenv
- requests

### Frontend

- React
- Node.js

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- Climatiq API for providing emission factor data.
- React for the frontend framework.
- Flask for the backend API.

