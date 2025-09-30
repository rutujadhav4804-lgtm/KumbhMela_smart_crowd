from ultralytics import YOLO
import cv2, csv, os, threading, time
from datetime import datetime
import numpy as np
from playsound import playsound
import smtplib
from email.mime.text import MIMEText
from deep_sort_realtime.deepsort_tracker import DeepSort

# -------------------------------
# YOLO Model
# -------------------------------
model = YOLO("yolov8n.pt")  # person detection

# -------------------------------
# DeepSORT Tracker
# -------------------------------
tracker = DeepSort(max_age=30)

# -------------------------------
# CCTV / Webcam / Video
# -------------------------------
cap = cv2.VideoCapture("crowd.mp4")   # For video file

# -------------------------------
# Zones
# -------------------------------
zones = {
    "Zone A": [(50,50),(400,50),(400,400),(50,400)],
    "Zone B": [(450,50),(800,50),(800,400),(450,400)]
}

# -------------------------------
# Helper Functions
# -------------------------------
def point_in_zone(point, polygon):
    return cv2.pointPolygonTest(np.array(polygon, np.int32), point, False) >= 0

def get_status(count):
    if count < 8:
        return "✅ Safe"
    elif count < 11:
        return "🟡 Moderate"
    else:
        return "🚨 Overcrowded"

def send_email_alert(zone, count):
    sender = "smartalert74@gmail.com"
    app_password = "pkjl kgpl pbpq looe"   # 16-char app password
    receiver = "rutujadhav4804@gmail.com"

    subject = f"⚠️ {zone} Overcrowding Alert!"
    body = f"{zone} has {count} people detected.\nPlease take immediate action."

    msg = MIMEText(body)
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, app_password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print(f"📧 Email sent: {zone} alert")
    except Exception as e:
        print("Email failed:", e)

def play_alert_sound(duration=5):
    """Play alert sound for limited time"""
    def _play():
        start = time.time()
        while time.time() - start < duration:
            try:
                playsound("alert.mp3")
            except:
                break
    threading.Thread(target=_play, daemon=True).start()

# -------------------------------
# Logging CSV
# -------------------------------
os.makedirs("logs", exist_ok=True)
logfile = "logs/zone_counts.csv"
if not os.path.exists(logfile):
    with open(logfile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "zone", "people_count"])

# -------------------------------
# Alert Flags
# -------------------------------
alert_triggered = {zone: False for zone in zones}

# -------------------------------
# Main Loop
# -------------------------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model.predict(frame, conf=0.5, classes=0, verbose=False)
    detections = []

    # Convert YOLO detections for DeepSORT
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            detections.append(([x1, y1, x2 - x1, y2 - y1], conf, "person"))

    tracks = tracker.update_tracks(detections, frame=frame)

    zone_counts = {zone: 0 for zone in zones}

    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = int(track.track_id)
        custom_id = f"kumbhmela_{track_id:02d}"
        l, t, w, h = track.to_ltrb()
        l, t, w, h = int(l), int(t), int(w), int(h)

        cx, cy = int((l + w) / 2), int((t + h) / 2)

        # check each zone
        for zone_name, polygon in zones.items():
            if point_in_zone((cx, cy), polygon):
                zone_counts[zone_name] += 1

        # Draw bbox + ID
        cv2.rectangle(frame, (l, t), (w, h), (0, 255, 0), 2)
        cv2.putText(frame, custom_id, (l, t - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

    # Draw zones + display counts
    for zone_name, polygon in zones.items():
        pts = np.array(polygon, np.int32)
        cv2.polylines(frame, [pts], isClosed=True, color=(255,0,0), thickness=2)

        count = zone_counts[zone_name]
        status = get_status(count)

        # show text
        cv2.putText(frame, f"{zone_name}: {count} - {status}",
                    (polygon[0][0], polygon[0][1]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

        # Save to CSV
        with open(logfile, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), zone_name, count])

        # Alerts (only when count >= 13 and not already triggered)
        if count >= 13:
            if not alert_triggered[zone_name]:
                play_alert_sound(duration=5)
                send_email_alert(zone_name, count)
                alert_triggered[zone_name] = True
        else:
            # reset flag when crowd reduces again
            alert_triggered[zone_name] = False

    cv2.imshow("Zone-wise Crowd Detection + Tracking", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
