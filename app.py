from flask import Flask, Response, render_template, request, jsonify
import requests
import json
import os
from typing import Optional, List, Dict, Any

app = Flask(__name__)

class MedicalBot:
    def __init__(self):
        self.endpoint = "https://capps-backend-shzm2b4edovty.calmsea-1c79426f.westus.azurecontainerapps.io/chat/stream"
        
    def get_stream(self, query: str, message_history: Optional[List[Dict[str, str]]] = None):
        try:
            # Ensure message_history is a list
            messages = list(message_history) if message_history else []
            
            # Log received message history
            #print("Received message history:", messages)
            
            headers = {
                'authority': self.endpoint.split('//')[1],
                'accept': '*/*',
                'Content-Type': 'application/json',
                'origin': f"https://{self.endpoint.split('//')[1]}"
            }
            
            payload = {
                'messages': messages,
                'context': {
                    'overrides': {
                        'temperature': 0.3,
                        'retrieval_mode': 'hybrid',
                        'semantic_ranker': True,
                        'suggest_followup_questions': True
                    }
                },
                'session_state': None
            }
            
            # Log the payload being sent
            #print("Sending payload:", json.dumps(payload, indent=2))

            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        yield f"data: {json.dumps(chunk)}\n\n"
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        continue
                        
        except requests.RequestException as e:
            error_message = {
                'error': f"API request failed: {str(e)}",
                'status': 'error'
            }
            yield f"data: {json.dumps(error_message)}\n\n"
        except Exception as e:
            error_message = {
                'error': f"An unexpected error occurred: {str(e)}",
                'status': 'error'
            }
            yield f"data: {json.dumps(error_message)}\n\n"

medical_bot = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint for Azure Health Check feature
    Returns 200 if the application is running
    """
    return jsonify({
        'status': 'healthy',
        'service': 'medical-bot',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/chat', methods=['POST'])
def chat():
    global medical_bot
    if medical_bot is None:
        medical_bot = MedicalBot()
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        query = data.get('message')
        if not query:
            return jsonify({'error': 'No message provided'}), 400
            
        # Get message history from request
        message_history = data.get('messages', [])
        
        # Log the received message history
        #print("Received request with message history length:", len(message_history))
        
        return Response(
            medical_bot.get_stream(query, message_history),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'  # For Nginx
            }
        )
        
    except Exception as e:
        return jsonify({
            'error': f'Server error: {str(e)}',
            'status': 'error'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
