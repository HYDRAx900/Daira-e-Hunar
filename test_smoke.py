import json
import urllib.request

def send_request(query):
    url = "http://localhost:8000/request"
    data = json.dumps({"query": query}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"--- QUERY: {query} ---")
            print(f"Status: {result.get('status')}")
            print(f"Message: {result.get('message')}")
            print(f"Intent Need Clarification?: {result.get('intent', {}).get('needs_clarification')}")
            
            discovery = result.get('discovery')
            if discovery:
                print(f"Discovery found: {discovery.get('total_found')}")
                
            ranking = result.get('ranking')
            if ranking:
                top = ranking.get('top_3', [])
                if top:
                    print(f"Ranking top 1: {top[0].get('provider_id')} (Score: {top[0].get('score')})")
            
            booking = result.get('booking')
            if booking:
                print(f"Booking Status: {booking.get('status')}")
                print(f"Booking ID: {booking.get('booking_id')}")
                print(f"Scheduled: {booking.get('scheduled_datetime')}")
                print(f"Confirmation: {booking.get('confirmation_message')}")
            
            print(f"Run Trace: {result.get('run_trace')}")
            print("\n")
    except Exception as e:
        print(f"Error: {e}")

send_request("Mujhe kal subah G-13 mein AC technician chahiye")
send_request("asdfghjkl potato moon")
send_request("I need a beautician in Quetta")
