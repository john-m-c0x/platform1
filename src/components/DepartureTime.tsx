import React, { useState, useEffect } from 'react';
import './DepartureTime.css';
import { fetchTrainDepartures, TrainDeparture } from '../services/trainsApi';

// Fallback static times in case API is unavailable
const fallbackTimes = ["05:10", "05:47", "06:15", "06:31", "06:53", "07:10", "07:25", "07:45", 
                 "08:06", "08:25", "08:45", "09:01", "09:17", "09:32", "09:46", "10:01", 
                 "10:15", "10:31", "10:46", "11:01"];

interface FormattedDeparture {
  time: string;
  destination: string;
  mins: number;
  isLive?: boolean;
  platform: string;
}

const DepartureTime: React.FC = () => {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [departures, setDepartures] = useState<FormattedDeparture[]>([]);
  const [allDepartures, setAllDepartures] = useState<TrainDeparture[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const minutesUntil = (trainTime: string, currentTime: string): number => {
    const [trainHours, trainMins] = trainTime.split(':').map(Number);
    const [currentHours, currentMins] = currentTime.split(':').map(Number);
    const minutes = (trainHours * 60 + trainMins) - (currentHours * 60 + currentMins);
    return minutes < 0 ? minutes + (24 * 60) : minutes;
  };

  // Fetch departures from the API
  useEffect(() => {
    const loadDepartures = async () => {
      try {
        setLoading(true);
        const data = await fetchTrainDepartures();
        setAllDepartures(data.departures);
        setLastUpdated(data.lastUpdated);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch departures:', err);
        setError('Unable to load departures data');
      } finally {
        setLoading(false);
      }
    };

    loadDepartures();

    // Refresh data every 5 minutes
    const refreshInterval = setInterval(loadDepartures, 5 * 60 * 1000);
    return () => clearInterval(refreshInterval);
  }, []);

  // Update current time and format departures
  useEffect(() => {
    const updateTimes = () => {
      const now = new Date();
      const melbourneTime = new Date(now.toLocaleString('en-US', { timeZone: 'Australia/Melbourne' }));
      const timeStr = melbourneTime.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit'
      });
      setCurrentTime(timeStr);

      // Get departure times from API if available, otherwise use fallback
      const formattedDepartures: FormattedDeparture[] = [];
      
      if (allDepartures.length > 0) {
        // Use API data
        for (const dep of allDepartures) {
          const depTime = dep.live_time || dep.scheduled_time;
          if (depTime >= timeStr || minutesUntil(depTime, timeStr) < 12 * 60) { // Skip departures more than 12 hours away
            formattedDepartures.push({
              time: depTime,
              destination: dep.destination || 'Flinders',
              mins: minutesUntil(depTime, timeStr),
              isLive: !!dep.live_time,
              platform: dep.platform || '1'
            });
          }
        }
      } else {
        // Use fallback times
        for (const time of fallbackTimes) {
          if (time >= timeStr || minutesUntil(time, timeStr) < 12 * 60) {
            formattedDepartures.push({
              time,
              destination: 'Flinders',
              mins: minutesUntil(time, timeStr),
              isLive: false,
              platform: '1'
            });
          }
        }
      }
      
      // Sort by departure time
      formattedDepartures.sort((a, b) => a.mins - b.mins);
      
      // Limit to 5 departures max
      setDepartures(formattedDepartures.slice(0, 5));
    };

    updateTimes();
    const interval = setInterval(updateTimes, 60000);
    return () => clearInterval(interval);
  }, [allDepartures]);

  return (
    <div className="departure-time">
      {loading && <div className="loading">Loading departures...</div>}
      
      {error && <div className="error">{error}</div>}
      
      {departures.length > 0 && (
        <div className="departures-list">
          {departures.map((departure, index) => (
            <div 
              key={`${departure.time}-${index}`} 
              className={`departure-item ${index >= 2 ? 'later' : ''}`}
            >
              <div className="departure-time-display">
                <span className={`platform-indicator ${index >= 2 ? 'later' : ''}`}>1</span>
                <div className={`time ${index < 2 ? 'highlighted' : ''}`}>{departure.time}</div>
                <div className="destination">{departure.destination}</div>
              </div>
              <div className={`minutes-badge ${index >= 2 ? 'later' : ''}`}>
                {departure.mins <= 0 ? 'Now' : 
                  `${departure.mins} min${departure.mins !== 1 ? 's' : ''}`}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {lastUpdated && (
        <div className="last-updated">Updated: {lastUpdated}</div>
      )}
    </div>
  );
};

export default DepartureTime; 