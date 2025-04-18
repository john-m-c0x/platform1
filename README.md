# Platform 1 Cafe

A web application that displays train departure times for Platform 1 Cafe, located at Riversdale Station in Camberwell, Victoria.

## Setup Instructions

### Prerequisites
- Node.js (for the React frontend)
- Python 3.7+ (for the API service)
- PTV API credentials (Developer ID and API Key)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/platform1-cafe.git
   cd platform1-cafe
   ```

2. Install frontend dependencies:
   ```
   npm install
   ```

3. Install Python dependencies:
   ```
   pip install flask flask-cors requests pytz python-dotenv
   ```

4. Environment Configuration:
   - Copy the example environment file:
     ```
     cp .env.example .env
     ```
   - Edit the `.env` file and add your PTV API credentials:
     ```
     PTV_DEV_ID=your_dev_id_here
     PTV_API_KEY=your_api_key_here
     ```

### Development

1. Start the API service:
   ```
   python ptv_api_service.py
   ```

2. In a separate terminal, start the React frontend:
   ```
   npm start
   ```

3. Open your browser and navigate to `http://localhost:3000`

### Production Deployment

1. Build the React frontend:
   ```
   npm run build
   ```

2. Deploy the build directory and API service to your server.

## Security Notes

- Never commit your `.env` file to the repository
- Always use environment variables for sensitive information
- The `.env.example` file should not contain actual credentials

## License

[Your License Here] 