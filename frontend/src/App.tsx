import { useState } from 'react';

// 1. Define the shape of our expected data
interface Briefing {
  title: string;
  time: string;
  attendees: string[];
  ai_briefing: string;
}

interface ApiResponse {
  message: string;
  briefings: Briefing[];
}

export default function App() {
  // 2. Setup State
  const [briefings, setBriefings] = useState<Briefing[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // 3. The Fetch Logic
  const generateBriefings = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Reaching out to the FastAPI server
      const response = await fetch('http://127.0.0.1:8000/api/briefings');
      
      if (!response.ok) {
        throw new Error(`Server responded with a ${response.status} error.`);
      }

      const data: ApiResponse = await response.json();
      setBriefings(data.briefings);
      
    } catch (err: any) {
      console.error("Fetch error:", err);
      setError(err.message || "Failed to connect to the backend.");
    } finally {
      setIsLoading(false);
    }
  };

  // 4. The UI
  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif', maxWidth: '800px', margin: '0 auto' }}>
      <h1>🤖 AI Executive Assistant</h1>
      
      <button 
        onClick={generateBriefings} 
        disabled={isLoading}
        style={{ padding: '10px 20px', fontSize: '16px', cursor: 'pointer', marginBottom: '20px' }}
      >
        {isLoading ? 'Generating Briefings...' : 'Sync Calendar & Generate'}
      </button>

      {error && (
        <div style={{ color: 'red', padding: '10px', border: '1px solid red', marginBottom: '20px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <div>
        {briefings.length === 0 && !isLoading && !error && (
          <p>No briefings generated yet. Click the button above to start.</p>
        )}

        {briefings.map((briefing, index) => (
          <div key={index} style={{ border: '1px solid #ddd', padding: '15px', marginBottom: '15px', borderRadius: '8px' }}>
            <h2>{briefing.title}</h2>
            <p><strong>Time:</strong> {briefing.time}</p>
            <p><strong>Attendees:</strong> {briefing.attendees.length > 0 ? briefing.attendees.join(', ') : 'None'}</p>
            
            <hr style={{ margin: '15px 0', borderTop: '1px solid #eee' }} />
            
            <h3>🧠 Executive Briefing</h3>
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
              {briefing.ai_briefing}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}