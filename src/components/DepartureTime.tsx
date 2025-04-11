import React, { useState, useEffect } from 'react';
import './DepartureTime.css';

const deptimes = ["05:10", "05:47", "06:15", "06:31", "06:53", "07:10", "07:25", "07:45", 
                 "08:06", "08:25", "08:45", "09:01", "09:17", "09:32", "09:46", "10:01", 
                 "10:15", "10:31", "10:46", "11:01"];

const DepartureTime: React.FC = () => {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [nextTrain, setNextTrain] = useState<{time: string, mins: number} | null>(null);

  const minutesUntil = (trainTime: string, currentTime: string): number => {
    const [trainHours, trainMins] = trainTime.split(':').map(Number);
    const [currentHours, currentMins] = currentTime.split(':').map(Number);
    const minutes = (trainHours * 60 + trainMins) - (currentHours * 60 + currentMins);
    return minutes < 0 ? minutes + (24 * 60) : minutes;
  };

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

      for (const time of deptimes) {
        if (time > timeStr) {
          setNextTrain({ time, mins: minutesUntil(time, timeStr) });
          return;
        }
      }
      
      const nextTrainTime = deptimes[0];
      setNextTrain({ 
        time: nextTrainTime, 
        mins: minutesUntil(nextTrainTime, timeStr)
      });
    };

    updateTimes();
    const interval = setInterval(updateTimes, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="departure-time">
      {nextTrain && (
        <div className="next-train">
          <div className="train-time">Next train: {nextTrain.time}</div>
          <div className="minutes-until">
            Departing in: {
              nextTrain.mins >= 60
                ? `${Math.floor(nextTrain.mins / 60)} hour${Math.floor(nextTrain.mins / 60) > 1 ? 's' : ''} ${nextTrain.mins % 60} minute${nextTrain.mins % 60 !== 1 ? 's' : ''}`
                : `${nextTrain.mins} minute${nextTrain.mins !== 1 ? 's' : ''}`
           }
          </div>
        </div>
      )}
    </div>
  );
};

export default DepartureTime; 