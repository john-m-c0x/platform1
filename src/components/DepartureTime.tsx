import React, { useState, useEffect } from 'react';
import './DepartureTime.css';

interface Departure {
  scheduled_time: string;
  live_time: string | null;
  destination: string;
}

interface ApiResponse {
  departures: Departure[];
  lastUpdated: string;
  updating: boolean;
}

export const DepartureTime: React.FC = () => {
  const [departures, setDepartures] = useState<Departure[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDepartures = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/departures');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: ApiResponse = await response.json();
      
      // Log the full API response
      console.log('API Response:', {
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
        data: data
      });
      
      setDepartures(data.departures);
      setLastUpdated(data.lastUpdated);
      setError(null);
    } catch (e) {
      const errorMessage = `Failed to fetch departures: ${e instanceof Error ? e.message : String(e)}`;
      console.error('Error details:', e);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    console.log('Initiating API call...');
    fetchDepartures();
    const interval = setInterval(() => {
      console.log('Refreshing data...');
      fetchDepartures();
    }, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <div className="departure-time">
        <div className="loading">Loading departure times...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="departure-time">
        <div className="error">{error}</div>
        <button onClick={fetchDepartures} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  if (!departures.length) {
    return (
      <div className="departure-time">
        <div className="no-departures">No departures found</div>
      </div>
    );
  }

  return (
    <div className="departure-time">
      <div className="station-image">
        <img src="/images/train-station.jpg" alt="Train Station" />
      </div>
      
      <div className="departures-container">
        <h2>Next Trains</h2>
        {departures.slice(0, 5).map((departure, index) => (
          <div key={index} className="departure-item">
            <div className="time">
              {departure.scheduled_time}
              {departure.live_time && (
                <span className="live-time"> (Live: {departure.live_time})</span>
              )}
            </div>
            <div className="destination">{departure.destination}</div>
          </div>
        ))}
      </div>

      {lastUpdated && (
        <div className="last-updated">
          Last updated: {lastUpdated}
        </div>
      )}
    </div>
  );
}; 