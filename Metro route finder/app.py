from flask import Flask, render_template, request
from datetime import datetime, timedelta
import pytz
import random
from metro_system import load_data_from_mongodb

app = Flask(__name__)
metro = load_data_from_mongodb()
TIMEZONE = pytz.timezone("Asia/Kolkata")

def generate_train_timings(departure_time, num_trains=3):
    """Generate random train timings with 4-10 minute gaps"""
    train_times = []
    current_time = departure_time
    
    for _ in range(num_trains):
        gap = random.randint(4, 10)  # Random gap between 4-10 minutes
        current_time += timedelta(minutes=gap)
        train_times.append(current_time.strftime("%H:%M"))
    
    return train_times

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/route', methods=['POST'])
def route():
    start = request.form.get('start', '').strip()
    end = request.form.get('end', '').strip()
    time_input = request.form.get('time', '')
    optimize = request.form.get('optimize', 'time')

    # Time parsing
    if time_input:
        try:
            depart_time = datetime.strptime(time_input, "%H:%M").time()
            full_depart_time = datetime.combine(datetime.today(), depart_time)
        except ValueError:
            return "Invalid time format. Use HH:MM"
    else:
        full_depart_time = datetime.now(TIMEZONE)

    # Generate train timings
    train_timings = generate_train_timings(full_depart_time)

    # Get route
    result = metro.shortest_path(start, end, optimize, full_depart_time)

    if not result:
        return render_template('index.html',
                            error=f"No route found from {start} to {end}",
                            train_timings=train_timings)

    return render_template('index.html',
                         start=start,
                         end=end,
                         time=time_input,
                         optimize=optimize,
                         train_timings=train_timings,
                         result=result)

if __name__ == '__main__':
    app.run(debug=True)