import React, { useState, useEffect } from 'react';
import DepartureTime from './components/DepartureTime';
import './App.css';

function App() {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  
  // Use process.env.PUBLIC_URL which worked before
  const images = [
    process.env.PUBLIC_URL + '/images/train-station.jpg',
    process.env.PUBLIC_URL + '/images/train-station-2.jpg', 
    process.env.PUBLIC_URL + '/images/train-station-3.jpg',
    process.env.PUBLIC_URL + '/images/train-station-4.jpg'
  ];

  // Auto scroll images every 10 seconds
  useEffect(() => {
    const intervalId = setInterval(() => {
      setCurrentImageIndex(prevIndex => (prevIndex + 1) % images.length);
    }, 10000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, [images.length]);

  return (
    <div className="App">
      <header>
        <h1>Platform 1 Cafe</h1>
        <div className="address-container">
          <p className="address">
            Monday - Friday | 5am - 2pm<br /> <br />
            Wandin Road,<br />
            Camberwell, Victoria 3124<br />
            City of Boroondara
          </p>
          <div className="social-links">
          <a href="https://www.facebook.com/profile.php?id=100027924356190" target="_blank" rel="noopener noreferrer" className="facebook">
            <i className="fab fa-facebook"></i>
          </a>
          <a href="https://www.instagram.com/platform1_cafe/" target="_blank" rel="noopener noreferrer" className="instagram">
            <i className="fab fa-instagram"></i>
          </a>
        </div>
        </div>
        
        <div className="station-image">
          {images.map((src, index) => (
            <img
              key={index}
              src={src}
              alt={`Train station view ${index + 1}`}
              className={index === currentImageIndex ? 'active' : ''}
            />
          ))}
        </div>
      </header>
      <main>
        <DepartureTime />
      </main>
      <footer>
        <p>made with 💕 by john cox | 2025</p>
      </footer>
    </div>
  );
}

export default App;