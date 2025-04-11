import React, { useState, useEffect } from 'react';
import DepartureTime from './components/DepartureTime';
import './App.css';

const images = [
  '/images/train-station.jpg',
  '/images/train-station-2.jpg',
  '/images/train-station-3.jpg',
  '/images/train-station-4.jpg',
];

function App() {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [imageLoaded, setImageLoaded] = useState(false);

  const handleMouseEnter = () => {
    setCurrentImageIndex((prevIndex) => (prevIndex + 1) % images.length);
  };

  useEffect(() => {
    // Preload images
    images.forEach(src => {
      const img = new Image();
      img.src = src;
      img.onload = () => setImageLoaded(true);
    });
  }, []);

  return (
    <div className="App">
      <header>
        <h1>Platform 1 Cafe</h1>
        <p className="address">
          Wandin Road,<br />
          Camberwell, Victoria 3124<br />
          City of Boroondara
        </p>
        <div className="station-image" onMouseEnter={handleMouseEnter}>
          {images.map((image, index) => (
            <img
              key={image}
              src={image}
              alt={`Train station ${index + 1}`}
              className={index === currentImageIndex ? 'active' : ''}
            />
          ))}
        </div>
      </header>
      <main>
        <DepartureTime />
      </main>
      <footer>
        <div className="social-links">
          <a href="https://www.facebook.com/profile.php?id=100027924356190" target="_blank" rel="noopener noreferrer" className="facebook">
            <i className="fab fa-facebook"></i>
          </a>
          <a href="https://www.instagram.com/platform1_cafe/" target="_blank" rel="noopener noreferrer" className="instagram">
            <i className="fab fa-instagram"></i>
          </a>
        </div>
        <p>made with 💕 by john cox | 2025</p>
      </footer>
    </div>
  );
}

export default App;