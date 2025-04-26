import React, { useState } from 'react';
import './App.css';

const App = () => {
  const [activities, setActivities] = useState([]);
  const [selectedActivity, setSelectedActivity] = useState('');
  const [amount, setAmount] = useState('');
  const [unit, setUnit] = useState('kWh');
  const [region, setRegion] = useState('US');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const activityOptions = [
    { id: 'electricity', label: 'Electricity Usage', units: ['kWh', 'MWh', 'GWh'] },
    { id: 'car', label: 'Car Travel', units: ['km', 'miles'] },
    { id: 'bus', label: 'Bus Travel', units: ['km', 'miles'] },
    { id: 'natural_gas', label: 'Natural Gas', units: ['kWh', 'MWh'] },
    { id: 'rail', label: 'Train Travel', units: ['km', 'miles'] },
  ];

  const regions = ['US', 'EU', 'UK', 'CA', 'CN', 'AU', 'IN', 'GLOBAL'];

  const handleAddActivity = () => {
    if (!selectedActivity || !amount) return;
    
    const selectedOption = activityOptions.find(a => a.id === selectedActivity);
    const isEnergy = selectedOption.units[0] === 'kWh' || 
                     selectedOption.units[0] === 'MWh' ||
                     selectedOption.units[0] === 'GWh';
    const paramType = isEnergy ? 'energy' : 'distance';

    const newActivity = {
      name: selectedOption.label,
      activity_type: selectedActivity,
      parameters: {
        [paramType]: parseFloat(amount),
        [`${paramType}_unit`]: unit
      },
      region: region
    };

    setActivities([...activities, newActivity]);
    setSelectedActivity('');
    setAmount('');
    setUnit(activityOptions[0].units[0]);
  };

  const removeActivity = (index) => {
    const updatedActivities = [...activities];
    updatedActivities.splice(index, 1);
    setActivities(updatedActivities);
  };

  const calculateEmissions = async () => {
    setLoading(true);
    setError(null);

    try {
      console.log("Sending activities to backend:", JSON.stringify(activities));

      const response = await fetch('http://localhost:5000/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ activities })
      });

      const responseText = await response.text();
      console.log("Raw response:", responseText);

      if (!response.ok) {
        let errorMessage = "Calculation failed";
        try {
          const errorData = JSON.parse(responseText);
          errorMessage = errorData.error || errorMessage;
        } catch (e) {
          errorMessage += `: ${response.status} - ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = JSON.parse(responseText);
      console.log("Parsed results:", data);
      setResults(data);
    } catch (error) {
      console.error('Error:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1 className="title">Carbon Footprint Calculator</h1>

      <div className="input-section">
        <div className="form-group">
          <label>Activity Type:</label>
          <select
            value={selectedActivity}
            onChange={(e) => {
              const newActivity = e.target.value;
              setSelectedActivity(newActivity);
              if (newActivity) {
                const defaultUnit = activityOptions.find(a => a.id === newActivity).units[0];
                setUnit(defaultUnit);
              }
            }}
            className="input"
          >
            <option value="">Select Activity</option>
            {activityOptions.map(opt => (
              <option key={opt.id} value={opt.id}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Amount:</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="input"
            placeholder="Enter amount"
          />
        </div>

        <div className="form-group">
          <label>Unit:</label>
          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="input"
            disabled={!selectedActivity}
          >
            {selectedActivity && activityOptions
              .find(a => a.id === selectedActivity)
              .units.map(u => (
                <option key={u} value={u}>{u}</option>
              ))}
          </select>
        </div>

        <div className="form-group">
          <label>Region:</label>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="input"
          >
            {regions.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        <button
          onClick={handleAddActivity}
          className="button primary"
        >
          Add Activity
        </button>
      </div>

      {activities.length > 0 && (
        <div className="activities-section">
          <h2>Selected Activities</h2>
          <div className="activities-list">
            {activities.map((activity, index) => {
              const activityType = activityOptions.find(a => a.id === activity.activity_type);
              const paramKey = Object.keys(activity.parameters)[0];
              const valueKey = Object.keys(activity.parameters)[1];
              
              return (
                <div key={index} className="activity-item">
                  <span>{activityType?.label || activity.activity_type}</span>
                  <span>{activity.parameters[paramKey]} {activity.parameters[valueKey]}</span>
                  <span>{activity.region}</span>
                  <button className="remove-btn" onClick={() => removeActivity(index)}>✕</button>
                </div>
              );
            })}
          </div>

          <button
            onClick={calculateEmissions}
            className="button calculate"
            disabled={loading}
          >
            {loading ? 'Calculating...' : 'Calculate Emissions'}
          </button>
        </div>
      )}

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {results && (
        <div className="results-section">
          <h2>Results</h2>
          <div className="total-comparison">
            <div className="comparison-bar api">
              <span>API: {results.api_emissions} {results.unit}</span>
            </div>
            <div className="comparison-bar algorithm">
              <span>Algorithm: {results.algorithm_emissions} {results.unit}</span>
            </div>
          </div>

          <div className="detailed-results">
            {results.activities && results.activities.map((activity, index) => (
              <div key={index} className="activity-result">
                <h3>{activity.name}</h3>
                <div className="activity-comparison">
                  <div className="result-item">
                    <label>API Calculation:</label>
                    <div className="value">{activity.api_emissions} {activity.unit}</div>
                  </div>
                  <div className="result-item">
                    <label>Algorithm Calculation:</label>
                    <div className="value">{activity.algorithm_emissions} {activity.unit}</div>
                  </div>
                  <div className="difference">
                    Difference: {activity.comparison.difference} {activity.unit} (
                      {activity.comparison.percent_difference}%)
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default App;