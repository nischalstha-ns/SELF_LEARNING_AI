import cv2
import face_recognition
import numpy as np
import os
import json
import pickle
from datetime import datetime

class VisionModule:
    def __init__(self):
        self.camera = None
        self.known_faces = {}
        self.faces_file = 'known_faces.pkl'
        self.load_known_faces()
        
    def load_known_faces(self):
        if os.path.exists(self.faces_file):
            with open(self.faces_file, 'rb') as f:
                self.known_faces = pickle.load(f)
    
    def save_known_faces(self):
        with open(self.faces_file, 'wb') as f:
            pickle.dump(self.known_faces, f)
    
    def start_camera(self):
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
        return self.camera.isOpened()
    
    def stop_camera(self):
        if self.camera:
            self.camera.release()
            cv2.destroyAllWindows()
            self.camera = None
    
    def capture_frame(self):
        if not self.start_camera():
            return None
        ret, frame = self.camera.read()
        return frame if ret else None
    
    def detect_faces(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        return face_locations, face_encodings
    
    def recognize_face(self, face_encoding):
        if not self.known_faces:
            return "Unknown"
        
        for name, known_encoding in self.known_faces.items():
            matches = face_recognition.compare_faces([known_encoding], face_encoding, tolerance=0.6)
            if matches[0]:
                return name
        return "Unknown"
    
    def learn_face(self, name):
        frame = self.capture_frame()
        if frame is None:
            return False
        
        face_locations, face_encodings = self.detect_faces(frame)
        
        if len(face_encodings) == 0:
            return False
        
        self.known_faces[name] = face_encodings[0]
        self.save_known_faces()
        
        # Save image
        cv2.imwrite(f"face_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg", frame)
        return True
    
    def who_am_i_seeing(self):
        frame = self.capture_frame()
        if frame is None:
            return "Camera not available"
        
        face_locations, face_encodings = self.detect_faces(frame)
        
        if len(face_encodings) == 0:
            return "No faces detected"
        
        names = []
        for face_encoding in face_encodings:
            name = self.recognize_face(face_encoding)
            names.append(name)
        
        if len(names) == 1:
            return f"I see {names[0]}"
        else:
            return f"I see {len(names)} people: {', '.join(names)}"
    
    def show_camera_feed(self, duration=5):
        if not self.start_camera():
            return False
        
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < duration:
            frame = self.capture_frame()
            if frame is None:
                break
            
            face_locations, face_encodings = self.detect_faces(frame)
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                name = self.recognize_face(face_encoding)
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            cv2.imshow('JARVIS Vision', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()
        return True
    
    def take_photo(self):
        frame = self.capture_frame()
        if frame is None:
            return None
        
        filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, frame)
        return filename
    
    def describe_scene(self):
        frame = self.capture_frame()
        if frame is None:
            return "Camera not available"
        
        face_locations, _ = self.detect_faces(frame)
        
        # Basic scene description
        height, width = frame.shape[:2]
        brightness = np.mean(frame)
        
        description = []
        
        if brightness < 50:
            description.append("The scene is dark")
        elif brightness > 200:
            description.append("The scene is very bright")
        else:
            description.append("The scene has normal lighting")
        
        if len(face_locations) > 0:
            description.append(f"I detect {len(face_locations)} face(s)")
        else:
            description.append("No faces detected")
        
        return ". ".join(description)
