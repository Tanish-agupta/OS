import cv2
import numpy as np
import mediapipe as mp
import math
import platform
import subprocess
import os

class GestureVolumeController:
    def __init__(self):
        # Initialize MediaPipe hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Volume control parameters
        self.min_vol = 0
        self.max_vol = 100
        self.vol = 0
        self.vol_bar = 400
        self.vol_per = 0
        
        # Gesture parameters
        self.min_hand_distance = 30
        self.max_hand_distance = 200
        
        # Smoothing parameters
        self.volume_history = []
        self.history_size = 5
        
        # OS detection for volume control
        self.os_type = platform.system()
        
    def set_volume(self, volume):
        """Set system volume based on OS"""
        try:
            if self.os_type == "Windows":
                # Windows volume control using nircmd (requires nircmd.exe)
                # Alternative: using pycaw library
                os.system(f"nircmd setsysvolume {int(volume * 655.35)}")
            elif self.os_type == "Darwin":  # macOS
                os.system(f"osascript -e 'set volume output volume {volume}'")
            elif self.os_type == "Linux":
                # Linux using amixer
                os.system(f"amixer -D pulse sset Master {volume}%")
        except Exception as e:
            print(f"Error setting volume: {e}")
    
    def get_distance(self, point1, point2):
        """Calculate distance between two points"""
        return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)
    
    def smooth_volume(self, current_vol):
        """Apply smoothing to volume changes"""
        self.volume_history.append(current_vol)
        if len(self.volume_history) > self.history_size:
            self.volume_history.pop(0)
        return int(sum(self.volume_history) / len(self.volume_history))
    
    def draw_volume_bar(self, img, vol_per):
        """Draw volume bar on the image"""
        # Volume bar
        cv2.rectangle(img, (50, 150), (85, 400), (255, 0, 0), 3)
        cv2.rectangle(img, (50, int(400 - (vol_per * 2.5))), (85, 400), (255, 0, 0), cv2.FILLED)
        
        # Volume percentage text
        cv2.putText(img, f'{int(vol_per)}%', (40, 450), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 3)
        
        # Instructions
        cv2.putText(img, 'Pinch to Control Volume', (200, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, 'Press Q to Quit', (200, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    def run(self):
        """Main execution loop"""
        cap = cv2.VideoCapture(0)
        
        # Check if camera opened successfully
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("Gesture Volume Controller Started!")
        print("Instructions:")
        print("- Show your hand to the camera")
        print("- Pinch thumb and index finger together to control volume")
        print("- Closer pinch = lower volume, farther apart = higher volume")
        print("- Press 'q' to quit")
        
        while True:
            success, img = cap.read()
            if not success:
                print("Failed to read from camera")
                break
            
            # Flip image horizontally for mirror effect
            img = cv2.flip(img, 1)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Process hand detection
            results = self.hands.process(img_rgb)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw hand landmarks
                    self.mp_drawing.draw_landmarks(img, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    # Get landmark positions
                    landmarks = []
                    for lm in hand_landmarks.landmark:
                        h, w, c = img.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        landmarks.append([cx, cy])
                    
                    # Get thumb tip (4) and index finger tip (8) positions
                    if len(landmarks) >= 9:
                        thumb_tip = landmarks[4]
                        index_tip = landmarks[8]
                        
                        # Draw circles on fingertips
                        cv2.circle(img, tuple(thumb_tip), 15, (255, 0, 255), cv2.FILLED)
                        cv2.circle(img, tuple(index_tip), 15, (255, 0, 255), cv2.FILLED)
                        
                        # Draw line between fingertips
                        cv2.line(img, tuple(thumb_tip), tuple(index_tip), (255, 0, 255), 3)
                        
                        # Calculate distance between fingertips
                        distance = self.get_distance(thumb_tip, index_tip)
                        
                        # Map distance to volume (inverted for intuitive control)
                        vol = np.interp(distance, [self.min_hand_distance, self.max_hand_distance], [self.max_vol, self.min_vol])
                        vol_per = np.interp(distance, [self.min_hand_distance, self.max_hand_distance], [100, 0])
                        
                        # Apply smoothing
                        vol_smooth = self.smooth_volume(vol)
                        vol_per_smooth = self.smooth_volume(vol_per)
                        
                        # Set system volume
                        self.set_volume(vol_smooth)
                        
                        # Visual feedback
                        if distance < 50:
                            cv2.circle(img, ((thumb_tip[0] + index_tip[0]) // 2, (thumb_tip[1] + index_tip[1]) // 2), 15, (0, 255, 0), cv2.FILLED)
                        
                        # Display distance
                        cv2.putText(img, f'Distance: {int(distance)}', (200, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Draw volume bar
            self.draw_volume_bar(img, vol_per_smooth if 'vol_per_smooth' in locals() else 0)
            
            # Display the image
            cv2.imshow('Gesture Volume Controller', img)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        print("Gesture Volume Controller stopped!")

# Additional utility functions for different volume control methods
def install_requirements():
    """Install required packages"""
    packages = ['opencv-python', 'mediapipe', 'numpy']
    for package in packages:
        try:
            subprocess.check_call(['pip', 'install', package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")

def setup_windows_volume():
    """Setup instructions for Windows volume control"""
    print("\nFor Windows users:")
    print("1. Download nircmd.exe from https://www.nirsoft.net/utils/nircmd.html")
    print("2. Place nircmd.exe in your system PATH or in the same directory as this script")
    print("3. Alternatively, install pycaw: pip install pycaw")

if __name__ == "__main__":
    # Check if running directly
    print("Gesture Volume Controller")
    print("=" * 50)
    
    # Install requirements if needed
    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError:
        print("Installing required packages...")
        install_requirements()
    
    # Setup instructions
    if platform.system() == "Windows":
        setup_windows_volume()
    
    # Run the controller
    controller = GestureVolumeController()
    controller.run()
