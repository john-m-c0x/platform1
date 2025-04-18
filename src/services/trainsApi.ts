// API service for train departures data

export interface TrainDeparture {
  scheduled_time: string;
  live_time: string | null;
  destination: string;
  platform: string;
  at_platform: boolean;
  vehicle?: string | null;
  direction: string;
  disruptions: Array<{
    title: string;
    description: string;
  }>;
  route_name: string;
}

export interface TrainsApiResponse {
  departures: TrainDeparture[];
  lastUpdated: string | null;
  updating: boolean;
}

// Default API URL is localhost for development, can be overridden in environment variables
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

/**
 * Fetches train departure data from the API
 */
export const fetchTrainDepartures = async (): Promise<TrainsApiResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/departures`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    const data = await response.json();
    return data as TrainsApiResponse;
  } catch (error) {
    console.error('Error fetching train departures:', error);
    // Return empty data structure in case of error
    return {
      departures: [],
      lastUpdated: null,
      updating: false
    };
  }
}

/**
 * Check API health
 */
export const checkApiHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return response.ok;
  } catch (error) {
    console.error('API health check failed:', error);
    return false;
  }
}

export default {
  fetchTrainDepartures,
  checkApiHealth
}; 